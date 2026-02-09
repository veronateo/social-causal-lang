import numpy as np
import pandas as pd
import csv
import os
import concurrent.futures
import random
import json

from typing import List, Dict, Any, Tuple
from scipy.optimize import minimize, minimize_scalar
from scipy import stats
from scipy.stats import pearsonr
from sklearn.model_selection import KFold
from src.model.domains.physical import PhysicalDomain
from src.model.domains.belief import BeliefDomain
from src.model.domains.preference import PreferenceDomain
from src.model.semantics import Semantics
from src.model.rsa import RSACausalVerbModel
from src.model.config import ModelConfig
from src.utils.data_loader import load_physical_data, load_belief_data, load_preference_data


# Constants
VERBS = ['caused', 'enabled', 'allowed', 'made_no_difference']
EPS = 1e-10
SEED = 42


class TrialObj:
    """Helper to store trial data uniformly"""
    def __init__(self, domain_name, trial_data, human_dist, domain_model):
        self.domain_name = domain_name
        self.trial_data = trial_data
        self.human_dist = human_dist
        self.domain_model = domain_model
        self.state = domain_model.get_domain_state(trial_data)
        self.theta = None
        if domain_name == 'physical' and hasattr(domain_model, 'inference'):
            self.theta = domain_model.inference.infer_most_likely_theta(trial_data)

def loss_wrapper(params, trials, ablation):
    step_cost, temperature, alpha = params
    config = ModelConfig(
        step_cost=step_cost,
        temperature=temperature,
        alpha=alpha,
        alignment_mode='soft',
    )
    return evaluate_with_config(trials, config, ablation=ablation)

def run_optimization_worker(seed_offset, bounds, trials, ablation):
    np.random.seed(SEED + seed_offset) # Ensure different seeds per process
    x0 = [np.random.uniform(b[0], b[1]) for b in bounds]
    res = minimize(loss_wrapper, x0=x0, args=(trials, ablation), 
                   bounds=bounds, method='L-BFGS-B', 
                   options={'maxiter': 200, 'ftol': 1e-6})
    return res

def save_detailed_results(trials: List[TrialObj], config: ModelConfig,
                          output_csv: str = 'outputs/model_predictions_full.csv', 
                          output_json: str = 'outputs/model_states.json',
                          other_configs: Dict[str, Any] = None):
    """Save detailed trial states and model predictions to CSV and JSON."""
    print(f"Saving detailed results to {output_csv}...")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    if other_configs is None:
        other_configs = {}

    # Setup models and domains
    
    # Helper config reconstruction
    def make_config(res_dict, fallback_config):
        if res_dict is None: return fallback_config
        return ModelConfig(
            step_cost=res_dict.get('step_cost', fallback_config.step_cost),
            temperature=res_dict.get('temperature', fallback_config.temperature),
            alpha=res_dict.get('alpha', fallback_config.alpha),
            alignment_mode='soft',
            cost_caused=res_dict.get('cost_caused', fallback_config.cost_caused),
            cost_enabled=res_dict.get('cost_enabled', fallback_config.cost_enabled),
            cost_allowed=res_dict.get('cost_allowed', fallback_config.cost_allowed),
            cost_mnd=res_dict.get('cost_made_no_difference', fallback_config.cost_mnd)
        )

    # 1. Full Model (Base)
    rsa_full = RSACausalVerbModel(
        rationality_alpha=config.alpha, 
        costs={k: getattr(config, f"cost_{k}", 0.0) for k in ['caused', 'enabled', 'allowed']}
    )
    # print(f"rsa_full config: {config}")

    # 2. No Preference
    conf_nopref = make_config(other_configs.get('nopref'), config)
    rsa_no_pref = RSACausalVerbModel(
        rationality_alpha=conf_nopref.alpha, 
        ablation='no_aligned',
        costs={k: getattr(conf_nopref, f"cost_{k}", 0.0) for k in ['caused', 'enabled', 'allowed']}
    )
    # print(f"rsa_no_pref config: {conf_nopref}")
    domains_nopref = {
        'physical': PhysicalDomain(config=conf_nopref),
        'preference': PreferenceDomain(config=conf_nopref),
        'belief': BeliefDomain(config=conf_nopref)
    }

    # 3. No Causal
    conf_nocausal = make_config(other_configs.get('nocausal'), config)
    rsa_no_causal = RSACausalVerbModel(
        rationality_alpha=conf_nocausal.alpha, 
        ablation='no_causal',
        costs={k: getattr(conf_nocausal, f"cost_{k}", 0.0) for k in ['caused', 'enabled', 'allowed']}
    )
    # print(f"rsa_no_causal config: {conf_nocausal}")
    domains_nocausal = {
        'physical': PhysicalDomain(config=conf_nocausal),
        'preference': PreferenceDomain(config=conf_nocausal),
        'belief': BeliefDomain(config=conf_nocausal)
    }

    # 4. Semantics Only
    # Alpha is unused for semantics, setting to default 1.0 for config validity
    conf_sem = make_config(other_configs.get('sem'), config)
    conf_sem.alpha = 1.0
    
    semantics = Semantics()
    # print(f"rsa_sem config: {conf_sem}")
    domains_sem = {
        'physical': PhysicalDomain(config=conf_sem),
        'preference': PreferenceDomain(config=conf_sem),
        'belief': BeliefDomain(config=conf_sem)
    }
    
    headers = [
        'domain', 'trial_id', 'human_n',
        'necessity', 'acted', 'aligned', 'theta',
        'actual_outcome', 'expected_outcome',
        'pred_caused_full', 'pred_enabled_full', 'pred_allowed_full', 'pred_made_no_difference_full',
        'pred_caused_nopref', 'pred_enabled_nopref', 'pred_allowed_nopref', 'pred_made_no_difference_nopref',
        'pred_caused_nocausal', 'pred_enabled_nocausal', 'pred_allowed_nocausal', 'pred_made_no_difference_nocausal',
        'pred_caused_sem', 'pred_enabled_sem', 'pred_allowed_sem', 'pred_made_no_difference_sem',
        'human_caused', 'human_enabled', 'human_allowed', 'human_made_no_difference',
        'debug_necessity', 'debug_posterior'
    ]
    
    unique_distributions = {}
    
    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        
        for t in trials:
            # 1. Full Model (Uses t.state which is based on 'config')
            state_full = t.state
            probs_full = rsa_full.pragmatic_speaker_s1(state_full)
            
            # 2. No Pref
            state_nopref = domains_nopref[t.domain_name].get_domain_state(t.trial_data)
            probs_nopref = rsa_no_pref.pragmatic_speaker_s1(state_nopref)
            
            # 3. No Causal
            state_nocausal = domains_nocausal[t.domain_name].get_domain_state(t.trial_data)
            probs_nocausal = rsa_no_causal.pragmatic_speaker_s1(state_nocausal)
            
            # 4. Semantics
            state_sem = domains_sem[t.domain_name].get_domain_state(t.trial_data)
            probs_sem = semantics.get_verb_probabilities(state_sem)
            
            # Identify unique semantic state key (C, A, V)
            state_key = (t.state.necessity, t.state.acted, t.state.aligned)
            state_str = str(state_key)
            
            if state_str not in unique_distributions:
                unique_distributions[state_str] = {
                    "state": {
                        "necessity": t.state.necessity,
                        "acted": t.state.acted,
                        "aligned": t.state.aligned,
                    },
                    "full": probs_full,
                    "nopref": probs_nopref,
                    "nocausal": probs_nocausal,
                    "sem": probs_sem,
                    "trials": []
                }
            unique_distributions[state_str]["trials"].append({
                "domain": t.domain_name,
                "trial_id": t.trial_data.get('trial_id', 'unknown'),
                "theta": t.theta
            })
            
            row = {
                'domain': t.domain_name,
                'trial_id': t.trial_data.get('trial_id', 'unknown'),
                'human_n': t.trial_data.get('human_N', 0),
                'necessity': t.state.necessity,
                'acted': t.state.acted,
                'aligned': t.state.aligned,
                'theta': t.theta,
                'actual_outcome': t.state.actual_outcome,
                'expected_outcome': t.state.expected_outcome,
                
                # Full
                'pred_caused_full': probs_full.get('caused', 0.0),
                'pred_enabled_full': probs_full.get('enabled', 0.0),
                'pred_allowed_full': probs_full.get('allowed', 0.0),
                'pred_made_no_difference_full': probs_full.get('made_no_difference', 0.0),

                # No Pref
                'pred_caused_nopref': probs_nopref.get('caused', 0.0),
                'pred_enabled_nopref': probs_nopref.get('enabled', 0.0),
                'pred_allowed_nopref': probs_nopref.get('allowed', 0.0),
                'pred_made_no_difference_nopref': probs_nopref.get('made_no_difference', 0.0),
                
                # No Causal
                'pred_caused_nocausal': probs_nocausal.get('caused', 0.0),
                'pred_enabled_nocausal': probs_nocausal.get('enabled', 0.0),
                'pred_allowed_nocausal': probs_nocausal.get('allowed', 0.0),
                'pred_made_no_difference_nocausal': probs_nocausal.get('made_no_difference', 0.0),
                
                # Sem Only
                'pred_caused_sem': probs_sem.get('caused', 0.0),
                'pred_enabled_sem': probs_sem.get('enabled', 0.0),
                'pred_allowed_sem': probs_sem.get('allowed', 0.0),
                'pred_made_no_difference_sem': probs_sem.get('made_no_difference', 0.0),
                
                # Human P(u)
                'human_caused': t.human_dist.get('caused', 0.0),
                'human_enabled': t.human_dist.get('enabled', 0.0),
                'human_allowed': t.human_dist.get('allowed', 0.0),
                'human_made_no_difference': t.human_dist.get('made_no_difference', 0.0),
                
                'debug_necessity': json.dumps(t.state.debug_necessity_info) if t.state.debug_necessity_info else "",
                'debug_posterior': json.dumps(t.state.debug_posterior) if t.state.debug_posterior else ""
            }
            writer.writerow(row)
            
    # Save unique distributions to JSON
    print(f"Saving unique distributions to {output_json}...")
    with open(output_json, 'w') as f:
        json.dump(unique_distributions, f, indent=2)
            
    print("Done.")

def compute_nll(human_dist: Dict[str, float], model_dist: Dict[str, float]) -> float:
    """Compute NLL for a single trial."""
    nll = 0.0
    for v in VERBS:
        p_h = human_dist.get(v, 0.0)
        p_m = model_dist.get(v, 0.0)
        p_m = max(p_m, EPS)
        if p_h > 0:
            nll -= p_h * np.log(p_m)
    return nll

def evaluate_with_config(trials: List[TrialObj], config: ModelConfig,
                        ablation: str = None) -> float:
    """
    Evaluate NLL for a dataset with given ModelConfig.
    Recreates domain models with the config and recomputes states.
    """
    # Create domain models with config
    phys_dom = PhysicalDomain(config=config)
    pref_dom = PreferenceDomain(config=config)
    belief_dom = BeliefDomain()
    
    # RSA model
    rsa_model = RSACausalVerbModel(
        rationality_alpha=config.alpha, 
        ablation=ablation,
        costs={
            'caused': config.cost_caused,
            'enabled': config.cost_enabled,
            'allowed': config.cost_allowed,
            'made_no_difference': config.cost_mnd
        }
    )
    
    total_nll = 0.0
    for t in trials:
        # Recompute state with new config
        if t.domain_name == 'physical':
            state = phys_dom.get_domain_state(t.trial_data)
        elif t.domain_name == 'preference':
            state = pref_dom.get_domain_state(t.trial_data)
        else:  # belief
            state = belief_dom.get_domain_state(t.trial_data)
        
        preds = rsa_model.pragmatic_speaker_s1(state)
        total_nll += compute_nll(t.human_dist, preds)
        
    return total_nll

def evaluate_dataset(trials: List[TrialObj], alpha: float) -> float:
    """Compute total NLL for a dataset (using precomputed states)."""
    total_nll = 0.0
    rsa_model = RSACausalVerbModel(rationality_alpha=alpha)
    
    for t in trials:
        preds = rsa_model.pragmatic_speaker_s1(t.state)
        total_nll += compute_nll(t.human_dist, preds)
        
    return total_nll

def evaluate_dataset_semantics(trials: List[TrialObj], config: ModelConfig = None) -> float:
    """Compute total NLL for semantics (S0) model."""
    total_nll = 0.0
    
    # If config provided, remake domains to ensure state parameters (temp, cost) are correct
    phys_dom = PhysicalDomain(config=config) if config else PhysicalDomain()
    pref_dom = PreferenceDomain(config=config) if config else PreferenceDomain()
    belief_dom = BeliefDomain(config=config) if config else BeliefDomain()
    
    semantics = Semantics()
    
    for t in trials:
        # Recompute state if config provided
        if config:
            if t.domain_name == 'physical':
                state = phys_dom.get_domain_state(t.trial_data)
            elif t.domain_name == 'preference':
                state = pref_dom.get_domain_state(t.trial_data)
            else:  # belief
                state = belief_dom.get_domain_state(t.trial_data)
        else:
            state = t.state
            
        sem_probs = semantics.get_verb_probabilities(state)
        total = sum(sem_probs.values())
        if total > 0:
            sem_norm = {k: v/total for k, v in sem_probs.items()}
        else:
            sem_norm = {k: 0.25 for k in VERBS}
        
        total_nll += compute_nll(t.human_dist, sem_norm)
        
    return total_nll

def fit_model_semantics_only(trials: List[TrialObj]) -> Dict[str, float]:
    """
    Perform fit for Semantics Only (S0) model.
    Optimizes step_cost and temperature.
    """
    def loss(params):
        step_cost, temperature = params
        
        config = ModelConfig(
            step_cost=step_cost,
            temperature=temperature,
            alpha=1.0, 
            alignment_mode='soft',
        )
        return evaluate_dataset_semantics(trials, config)
    
    x0 = [0.05, 0.1]
    bounds = [(0.001, 2.0), (0.01, 2.0)]
    
    result = minimize(loss, x0=x0, bounds=bounds, method='L-BFGS-B',
                     options={'maxiter': 200, 'ftol': 1e-4})
    
    step_cost, temperature = result.x
    return {
        'step_cost': step_cost,
        'temperature': temperature,
        'nll': result.fun
    }


def fit_full_model(trials: List[TrialObj],
                            ablation: str = None) -> Dict[str, float]:
    """
    Perform full model fit (3 parameters): step_cost, temperature, alpha.
    Uses Multi-Restart optimization with ProcessPoolExecutor.
    """
    bounds = [(0.001, 2.0), (0.01, 2.0), (0.01, 5.0)]
    
    # Parallel multi-restart
    n_restarts = 20
    best_res = None
    best_fun = float('inf')
    
    # Use ProcessPool for parallelism
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [executor.submit(run_optimization_worker, i, bounds, trials, ablation) 
                   for i in range(n_restarts)]
        for future in concurrent.futures.as_completed(futures):
            try:
                res = future.result()
                if res.fun < best_fun:
                    best_fun = res.fun
                    best_res = res
            except Exception as e:
                print(f"Optimization run failed: {e}")

    fit_params = best_res.x
    step_cost, temperature, alpha = fit_params
    
    return {
        'step_cost': step_cost,
        'temperature': temperature,
        'alpha': alpha,
        'nll': best_res.fun
    }
