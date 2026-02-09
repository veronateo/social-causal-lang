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
from src.model.classifier import InertialVerbClassifier
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

def loss_wrapper(params, trials, necessity_mode, ablation):
    step_cost, temperature, alpha, l_act, l_align = params
    config = ModelConfig(
        step_cost=step_cost,
        temperature=temperature,
        alpha=alpha,
        alignment_mode='soft',
        lambda_act=l_act,
        lambda_align=l_align,
        necessity_mode=necessity_mode,
        reward_scale=1.0
    )
    return evaluate_with_config(trials, config, ablation=ablation)

def run_optimization_worker(seed_offset, bounds, trials, necessity_mode, ablation):
    np.random.seed(SEED + seed_offset) # Ensure different seeds per process
    x0 = [np.random.uniform(b[0], b[1]) for b in bounds]
    res = minimize(loss_wrapper, x0=x0, args=(trials, necessity_mode, ablation), 
                   bounds=bounds, method='L-BFGS-B', 
                   options={'maxiter': 200, 'ftol': 1e-6})
    return res

def save_detailed_results(trials: List[TrialObj], config: ModelConfig,
                          output_csv: str = 'outputs/model_predictions_full.csv', 
                          output_json: str = 'outputs/model_states.json'):
    """Save detailed trial states and model predictions to CSV and JSON."""
    print(f"Saving detailed results to {output_csv}...")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    # Models
    # 1. Full Model
    rsa_full = RSACausalVerbModel(
        rationality_alpha=config.alpha, 
        lambda_act=config.lambda_act,
        lambda_align=config.lambda_align,
        necessity_mode=config.necessity_mode
    )
    
    # 2. No Preference (No Aligned)
    rsa_no_pref = RSACausalVerbModel(
        rationality_alpha=config.alpha, 
        ablation='no_aligned',
        lambda_act=config.lambda_act,
        lambda_align=config.lambda_align,
        necessity_mode=config.necessity_mode
    )
    
    # 3. No Causal (No Necessity)
    rsa_no_causal = RSACausalVerbModel(
        rationality_alpha=config.alpha, 
        ablation='no_causal',
        lambda_act=config.lambda_act,
        lambda_align=config.lambda_align,
        necessity_mode=config.necessity_mode
    )
    
    # 4. Semantics Only (classifier only, using fitted semantics)
    classifier = InertialVerbClassifier(
        lambda_act=config.lambda_act,
        lambda_align=config.lambda_align,
        necessity_mode=config.necessity_mode
    )
    
    headers = [
        'domain', 'trial_id', 'human_n',
        'changed', 'aligned', 'wizard_acted', 'necessity', 'theta',
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
            # Get model predictions
            probs_full = rsa_full.pragmatic_speaker_s1(t.state)
            probs_nopref = rsa_no_pref.pragmatic_speaker_s1(t.state)
            probs_nocausal = rsa_no_causal.pragmatic_speaker_s1(t.state)
            
            # Semantics Only (Normalize truth values)
            sem_vals = classifier.get_verb_probabilities(t.state)
            # Already normalized by get_verb_probabilities
            probs_sem = sem_vals
            
            # Identify unique semantic state key 
            nec_val = getattr(t.state, f'necessity_{config.necessity_mode}', 0.0)
            state_key = (t.state.changed, t.state.aligned, t.state.wizard_acted, nec_val)
            state_str = str(state_key)
            
            if state_str not in unique_distributions:
                unique_distributions[state_str] = {
                    "state": {
                        "changed": t.state.changed,
                        "aligned": t.state.aligned,
                        "wizard_acted": t.state.wizard_acted,
                        "necessity": nec_val
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
                'changed': t.state.changed,
                'aligned': t.state.aligned,
                'wizard_acted': t.state.wizard_acted,
                'necessity': nec_val,
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

def evaluate_with_config(trials: List[TrialObj], config: ModelConfig, valence_cost: float = 2.0, 
                        use_valence_cost: bool = True, strict_valence: bool = False,
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
        lambda_act=config.lambda_act,
        lambda_align=config.lambda_align,
        necessity_mode=config.necessity_mode,
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

def evaluate_dataset(trials: List[TrialObj], alpha: float, valence_cost: float = 2.0, use_valence_cost: bool = True, strict_valence: bool = False) -> float:
    """Compute total NLL for a dataset (using precomputed states)."""
    total_nll = 0.0
    rsa_model = RSACausalVerbModel(
        rationality_alpha=alpha, 
        use_valence_cost=use_valence_cost, 
        strict_valence_semantics=strict_valence,
        valence_cost=valence_cost
    )
    
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
    
    classifier = InertialVerbClassifier(
        lambda_act=config.lambda_act if config else 0.5,
        lambda_align=config.lambda_align if config else 0.5,
        necessity_mode=config.necessity_mode if config else 'avg'
    )
    
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
            
        sem_probs = classifier.get_verb_probabilities(state)
        total = sum(sem_probs.values())
        if total > 0:
            sem_norm = {k: v/total for k, v in sem_probs.items()}
        else:
            sem_norm = {k: 0.25 for k in VERBS}
        
        total_nll += compute_nll(t.human_dist, sem_norm)
        
    return total_nll

def fit_model_semantics_only(trials: List[TrialObj], necessity_mode: str = 'avg') -> Dict[str, float]:
    """
    Perform fit for Semantics Only (S0) model.
    Optimizes step_cost, temperature, lambda_act, lambda_align.
    """
    def loss(params):
        step_cost, temperature, l_act, l_align = params
        
        config = ModelConfig(
            step_cost=step_cost,
            temperature=temperature,
            alpha=1.0, 
            alignment_mode='soft',
            lambda_act=l_act,
            lambda_align=l_align,
            necessity_mode=necessity_mode,
            reward_scale=1.0
        )
        return evaluate_dataset_semantics(trials, config)
    
    # step, temp, l_act, l_align
    x0 = [0.05, 0.1, 0.5, 0.5]
    bounds = [(0.001, 2.0), (0.01, 2.0), (1.0, 1.0), (1.0, 1.0)]
    
    result = minimize(loss, x0=x0, bounds=bounds, method='L-BFGS-B',
                     options={'maxiter': 200, 'ftol': 1e-4})
    
    step_cost, temperature, l_act, l_align = result.x
    return {
        'step_cost': step_cost,
        'temperature': temperature,
        'lambda_act': l_act,
        'lambda_align': l_align,
        'necessity_mode': necessity_mode,
        'nll': result.fun
    }


def fit_full_model(trials: List[TrialObj], necessity_mode: str = 'avg',
                            ablation: str = None) -> Dict[str, float]:
    """
    Perform full model fit (5 parameters): step_cost, temperature, alpha, lambda_act, lambda_align.
    Uses Multi-Restart optimization with ProcessPoolExecutor.
    """
    # 5 parameters: step, temp, alpha, l_act, l_align
    bounds = [(0.001, 2.0), (0.01, 2.0), (0.01, 5.0), (1.0, 1.0), (1.0, 1.0)]
    
    # Parallel multi-restart
    n_restarts = 20
    best_res = None
    best_fun = float('inf')
    
    # Use ProcessPool for parallelism
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # Submit tasks
        futures = [executor.submit(run_optimization_worker, i, bounds, trials, necessity_mode, ablation) 
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
    step_cost, temperature, alpha, l_act, l_align = fit_params
    
    res_dict = {
        'step_cost': step_cost,
        'temperature': temperature,
        'alpha': alpha,
        'lambda_act': l_act,
        'lambda_align': l_align,
        'necessity_mode': necessity_mode,
        'nll': best_res.fun
    }
    
    return res_dict
