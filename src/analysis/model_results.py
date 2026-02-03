import numpy as np
import pandas as pd
import csv
import os
from typing import List, Dict, Any, Tuple
import json
from scipy.optimize import minimize, minimize_scalar
from scipy import stats
from scipy.stats import pearsonr
from sklearn.model_selection import KFold
import concurrent.futures
import random


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
        # Precompute domain state to speed up fitting
        self.state = domain_model.get_domain_state(trial_data)
        # Store inferred theta for physical domain
        self.theta = None
        if domain_name == 'physical' and hasattr(domain_model, 'inference'):
            self.theta = domain_model.inference.infer_most_likely_theta(trial_data)

# Top-level functions for pickling support
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

def save_fitted_params(step_cost: float, temperature: float, alpha: float, valence_cost: float, nll: float, 
                       output_path: str = 'outputs/fitted_params.json'):
    """Save fitted model parameters to JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    params = {
        'step_cost': step_cost,
        'temperature': temperature,
        'alpha': alpha,
        'valence_cost': valence_cost,
        'nll': nll
    }
    with open(output_path, 'w') as f:
        json.dump(params, f, indent=2)
    print(f"Saved fitted parameters to {output_path}")

def save_detailed_results(trials: List[TrialObj], config: ModelConfig,
                          output_csv: str = 'outputs/model_predictions_debug.csv', 
                          output_json: str = 'outputs/unique_model_states.json'):
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


def fit_model_5params(trials: List[TrialObj], necessity_mode: str = 'avg',
                            ablation: str = None) -> Dict[str, float]:
    """
    Perform fit for 5 parameters:
    step_cost, temperature, alpha, lambda_act, lambda_align.
    
    Uses Multi-Restart optimization with ProcessPoolExecutor.
    """
    
    # 5 parameters
    # step, temp, alpha, l_act, l_align
    bounds = [(0.001, 2.0), (0.01, 2.0), (0.01, 5.0), (1.0, 1.0), (1.0, 1.0)]
    
    # Parallel Multi-Restart
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

    if best_res is None:
        # Fallback if all failed
        return run_optimization_worker(0, bounds, trials, necessity_mode, ablation)

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


def main():
    # Set seed
    np.random.seed(SEED)

    print("Loading data...")
    all_trials: List[TrialObj] = []
    
    # Load all domains (Physical, Preference, Belief)
    phys_data = load_physical_data()
    phys_dom = PhysicalDomain()
    for td, hd in phys_data:
        all_trials.append(TrialObj('physical', td, hd, phys_dom))
        
    for td, hd in load_preference_data():
        all_trials.append(TrialObj('preference', td, hd, PreferenceDomain()))
        
    for td, hd in load_belief_data():
        all_trials.append(TrialObj('belief', td, hd, BeliefDomain()))
        
    print(f"Total Trials: {len(all_trials)}")

    def evaluate_performance(trials, config, model_type='rsa', ablation=None):
        # 1. Setup Domains
        phys_dom = PhysicalDomain(config=config)
        pref_dom = PreferenceDomain(config=config)
        belief_dom = BeliefDomain(config=config)
        
        # 2. Setup Model
        if model_type == 'sem':
            model = InertialVerbClassifier(
                lambda_act=config.lambda_act,
                lambda_align=config.lambda_align,
                necessity_mode=config.necessity_mode
            )
        else:
            model = RSACausalVerbModel(
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
            
        all_human = []
        all_model = []
        total_nll = 0.0
        
        for t in trials:
            # Recompute state
            if t.domain_name == 'physical':
                state = phys_dom.get_domain_state(t.trial_data)
            elif t.domain_name == 'preference':
                state = pref_dom.get_domain_state(t.trial_data)
            else: # belief
                state = belief_dom.get_domain_state(t.trial_data)
                
            if model_type == 'sem':
                probs = model.get_verb_probabilities(state)
                total = sum(probs.values())
                preds = {k: v/total if total>0 else 0.25 for k,v in probs.items()}
            else:
                preds = model.pragmatic_speaker_s1(state)
            
            # NLL
            total_nll += compute_nll(t.human_dist, preds)
            
            # Collect for r/RMSE
            for v in VERBS:
                all_human.append(t.human_dist.get(v, 0.0))
                all_model.append(preds.get(v, 0.0))
                
        avg_nll = total_nll / len(trials)
        r, _ = pearsonr(all_human, all_model)
        rmse = np.sqrt(np.mean((np.array(all_human) - np.array(all_model))**2))
        
        return avg_nll, r, rmse

    def bootstrap_metrics(human_vals, model_vals, n_boot=1000):
        """Bootstrap SE for r and RMSE."""
        n = len(human_vals)
        r_boots = []
        rmse_boots = []
        
        # Convert to numpy arrays for speed
        h_arr = np.array(human_vals)
        m_arr = np.array(model_vals)
        indices = np.arange(n)
        
        for _ in range(n_boot):
            # Resample indices with replacement
            resamp_idx = np.random.choice(indices, size=n, replace=True)
            h_sample = h_arr[resamp_idx]
            m_sample = m_arr[resamp_idx]
            
            # r
            if np.std(h_sample) > 0 and np.std(m_sample) > 0:
                r_val, _ = pearsonr(h_sample, m_sample)
            else:
                r_val = 0.0 # Should not happen with enough data
            r_boots.append(r_val)
            
            # rmse
            rmse_val = np.sqrt(np.mean((h_sample - m_sample)**2))
            rmse_boots.append(rmse_val)
            
        r_se = np.std(r_boots, ddof=1)
        rmse_se = np.std(rmse_boots, ddof=1)
        return r_se, rmse_se

    def compute_and_print_fit_stats(trials, res_dict, name, model_type='rsa', ablation=None):
        # 1. Reconstruct Config
        config = ModelConfig(
            step_cost=res_dict['step_cost'],
            temperature=res_dict['temperature'],
            alpha=res_dict.get('alpha', 1.0),
            alignment_mode='soft',
            lambda_act=res_dict['lambda_act'],
            lambda_align=res_dict['lambda_align'],
            necessity_mode=res_dict['necessity_mode'],
            reward_scale=1.0
        )
        
        # 2. Recreate Domain Models
        phys_dom = PhysicalDomain(config=config)
        pref_dom = PreferenceDomain(config=config)
        belief_dom = BeliefDomain(config=config)
        
        # 3. Setup Model
        if model_type == 'sem':
            model = InertialVerbClassifier(
                lambda_act=config.lambda_act,
                lambda_align=config.lambda_align,
                necessity_mode=config.necessity_mode
            )
        else:
            model = RSACausalVerbModel(
                rationality_alpha=config.alpha,
                ablation=ablation,
                lambda_act=config.lambda_act,
                lambda_align=config.lambda_align,
                necessity_mode=config.necessity_mode,
                costs={
                    'caused': res_dict.get('cost_caused', 0.0),
                    'enabled': res_dict.get('cost_enabled', 0.0),
                    'allowed': res_dict.get('cost_allowed', 0.0),
                    'made_no_difference': res_dict.get('cost_made_no_difference', 0.0)
                }
            )
            
        # 4. Compute Metrics
        nlls = []
        all_human = []
        all_model = []
        
        for t in trials:
            # Recompute state
            if t.domain_name == 'physical':
                state = phys_dom.get_domain_state(t.trial_data)
            elif t.domain_name == 'preference':
                state = pref_dom.get_domain_state(t.trial_data)
            else: # belief
                state = belief_dom.get_domain_state(t.trial_data)
                
            if model_type == 'sem':
                probs = model.get_verb_probabilities(state)
                total = sum(probs.values())
                preds = {k: v/total if total>0 else 0.25 for k,v in probs.items()}
            else:
                preds = model.pragmatic_speaker_s1(state)
                
            nll = compute_nll(t.human_dist, preds)
            nlls.append(nll)
            
            # Collect flat lists for r/RMSE
            for v in VERBS:
                all_human.append(t.human_dist.get(v, 0.0))
                all_model.append(preds.get(v, 0.0))
        
        nlls = np.array(nlls)
        mean_nll = np.mean(nlls)
        se_nll = np.std(nlls, ddof=1) / np.sqrt(len(nlls)) # Standard error of the mean NLL (across trials)
        
        # Point estimates
        r, _ = pearsonr(all_human, all_model)
        rmse = np.sqrt(np.mean((np.array(all_human) - np.array(all_model))**2))
        
        # Bootstrap SEs
        r_se, rmse_se = bootstrap_metrics(all_human, all_model)
        
        print(f"{name:<20} | NLL: {mean_nll:.4f}+/-{se_nll:.4f} | r: {r:.3f}+/-{r_se:.3f} | RMSE: {rmse:.3f}+/-{rmse_se:.3f}")
        
        return {
            'name': name,
            'nll': mean_nll,
            'nll_se': se_nll,
            'r': r,
            'r_se': r_se,
            'rmse': rmse,
            'rmse_se': rmse_se
        }

    
    # helper for global fits
    def fit_global_variant(name, ablation=None, model_type='rsa'):
        print(f"\nFitting Global {name}...")
        best_var_res = None
        # modes = ['control', 'max', 'avg']
        modes = ['avg']
        for m in modes:
            if model_type == 'sem':
                res = fit_model_semantics_only(all_trials, necessity_mode=m)
            else:
                res = fit_model_5params(all_trials, necessity_mode=m, ablation=ablation)
            
            if best_var_res is None or res['nll'] < best_var_res['nll']:
                best_var_res = res
        
        # Convert total NLL to average NLL
        best_var_res['avg_nll'] = best_var_res['nll'] / len(all_trials)
        print(f"Best {name}: {best_var_res['necessity_mode']}, Avg NLL={best_var_res['avg_nll']:.4f}")
        return best_var_res

    # 1. Global Fits
    
    collected_metrics = {}
    
    # A. Full Model
    res_full = fit_global_variant("Full Model", ablation=None)
    best_res = res_full # For saving
            
    print(f"\nBest Overall Fit:")
    print(f"Best Mode: {best_res['necessity_mode']}")
    print(f"Best Parameters: step_cost={best_res['step_cost']:.3f}, temperature={best_res['temperature']:.3f}, alpha={best_res['alpha']:.3f}")
    print(f"Semantics: λact={best_res['lambda_act']:.2f}, λalign={best_res['lambda_align']:.2f}")
    
    collected_metrics['full'] = compute_and_print_fit_stats(all_trials, best_res, "Full Model", ablation=None)
    
    # B. Semantics Only
    res_sem = fit_global_variant("Semantics Only", model_type='sem')
    collected_metrics['sem'] = compute_and_print_fit_stats(all_trials, res_sem, "Semantics Only", model_type='sem')
    
    # C. No Preference
    res_nopref = fit_global_variant("No Preference", ablation='no_aligned')
    collected_metrics['nopref'] = compute_and_print_fit_stats(all_trials, res_nopref, "No Preference", ablation='no_aligned')

    # D. No Causal
    res_nocausal = fit_global_variant("No Causal", ablation='no_causal')
    collected_metrics['nocausal'] = compute_and_print_fit_stats(all_trials, res_nocausal, "No Causal", ablation='no_causal')
    
    # Save Metrics
    metrics_path = 'outputs/global_fit_metrics.json'
    print(f"Saving global fit metrics to {metrics_path}...")
    with open(metrics_path, 'w') as f:
        json.dump(collected_metrics, f, indent=2)
    
    # Set final best state with best config (Full Model)
    best_config = ModelConfig(
        step_cost=best_res['step_cost'], 
        temperature=best_res['temperature'], 
        alpha=best_res['alpha'], 
        alignment_mode='soft',
        lambda_act=best_res['lambda_act'],
        lambda_align=best_res['lambda_align'],
        cost_enabled=best_res.get('cost_enabled', 0.0),
        cost_allowed=best_res.get('cost_allowed', 0.0),
        cost_mnd=best_res.get('cost_made_no_difference', 0.0),
        cost_caused=best_res.get('cost_caused', 0.0),
        necessity_mode=best_res['necessity_mode'],
        reward_scale=1.0
    )
    final_phys_dom = PhysicalDomain(config=best_config)
    final_pref_dom = PreferenceDomain(config=best_config)
    
    # Update states for saving detailed results
    for t in all_trials:
        if t.domain_name == 'physical':
            t.state = final_phys_dom.get_domain_state(t.trial_data)
            t.theta = final_phys_dom.inference.infer_most_likely_theta(t.trial_data)
        elif t.domain_name == 'preference':
            t.state = final_pref_dom.get_domain_state(t.trial_data)
    
    # Save detailed outputs
    save_detailed_results(all_trials, best_config)

    # Save best parameters to JSON for plotting
    best_params_path = 'outputs/s1_fit_best.json'
    print(f"Saving best parameters to {best_params_path}...")
    with open(best_params_path, 'w') as f:
        # Wrap in expected structure for utils.load_fitted_params
        json.dump({'best_params': best_res}, f, indent=2)

    # 2. Cross Validation
    K = 5
    kf = KFold(n_splits=K, shuffle=True, random_state=SEED)
    
    print(f"\nRunning {K}-Fold Comprehensive Cross-Validation...")
    print(f"Fold   | Params (Full)                  | Sem      | Full     | NoPref   (Avg NLL)")
    print("-" * 110)
    
    fold_idx = 1
    # Storage for (NLL, r, RMSE)
    results_cv = {
        'sem': {'nll': [], 'r': [], 'rmse': []},
        'full': {'nll': [], 'r': [], 'rmse': []},
        'nopref': {'nll': [], 'r': [], 'rmse': []},
        'nocausal': {'nll': [], 'r': [], 'rmse': []}
    }
    
    # print(f"len(all_trials): {len(all_trials)}")
    for train_idx, test_idx in kf.split(all_trials):
        train_set = [all_trials[i] for i in train_idx]
        test_set = [all_trials[i] for i in test_idx]
        
        # 1. Semantics Only (Fitted)
        best_sem_res = None
        # for m in ['control', 'max', 'avg']:
        for m in ['avg']:
            res = fit_model_semantics_only(train_set, necessity_mode=m)
            if best_sem_res is None or res['nll'] < best_sem_res['nll']:
                best_sem_res = res
        
        # Eval S0 on test set
        sem_config = ModelConfig(
            step_cost=best_sem_res['step_cost'],
            temperature=best_sem_res['temperature'],
            alpha=1.0, 
            alignment_mode='soft',
            lambda_act=best_sem_res['lambda_act'],
            lambda_align=best_sem_res['lambda_align'],
            necessity_mode=best_sem_res['necessity_mode']
        )
        nll_sem, r_sem, rmse_sem = evaluate_performance(test_set, sem_config, model_type='sem')
        
        # Helper to fit, update test states, and evaluate
        def fit_eval_model_cv(ablation=None):
            # Fit on Train: try all necessity modes
            # modes = ['control', 'max', 'avg']
            modes = ['avg']
            best_train_res = None
            
            for m in modes:
                res = fit_model_5params(train_set, necessity_mode=m, ablation=ablation)
                if best_train_res is None or res['nll'] < best_train_res['nll']:
                    best_train_res = res
            
            # Create config with best trained params
            config = ModelConfig(
                step_cost=best_train_res['step_cost'],
                temperature=best_train_res['temperature'],
                alpha=best_train_res['alpha'],
                alignment_mode='soft',
                lambda_act=best_train_res['lambda_act'],
                lambda_align=best_train_res['lambda_align'],
                cost_enabled=best_train_res.get('cost_enabled', 0.0),
                cost_allowed=best_train_res.get('cost_allowed', 0.0),
                cost_mnd=best_train_res.get('cost_made_no_difference', 0.0),
                cost_caused=best_train_res.get('cost_caused', 0.0),
                necessity_mode=best_train_res['necessity_mode'],
                reward_scale=1.0
            )
            
            # Evaluate on test set with config
            return evaluate_performance(test_set, config, ablation=ablation), best_train_res
            
        # 2. Full Model
        (nll_full, r_full, rmse_full), res_full_cv = fit_eval_model_cv(ablation=None)
        
        # 3. No Preference (No Aligned)
        (nll_nopref, r_nopref, rmse_nopref), res_no_pref = fit_eval_model_cv(ablation='no_aligned')
        
        # 4. No Causal (No Necessity)
        (nll_no_causal, r_no_causal, rmse_no_causal), res_no_causal = fit_eval_model_cv(ablation='no_causal')
        
        # Store
        results_cv['sem']['nll'].append(nll_sem)
        results_cv['sem']['r'].append(r_sem)
        results_cv['sem']['rmse'].append(rmse_sem)
        
        results_cv['full']['nll'].append(nll_full)
        results_cv['full']['r'].append(r_full)
        results_cv['full']['rmse'].append(rmse_full)
        
        results_cv['nopref']['nll'].append(nll_nopref)
        results_cv['nopref']['r'].append(r_nopref)
        results_cv['nopref']['rmse'].append(rmse_nopref)
        
        results_cv['nocausal']['nll'].append(nll_no_causal)
        results_cv['nocausal']['r'].append(r_no_causal)
        results_cv['nocausal']['rmse'].append(rmse_no_causal)
        
        # Print optimized params from Full Model
        params_str = (f"c={res_full_cv['step_cost']:.2f},T={res_full_cv['temperature']:.2f},"
                      f"Act={res_full_cv['lambda_act']:.2f},Ali={res_full_cv['lambda_align']:.2f}")
        
        print(f"{fold_idx:<6} | {params_str:<30} | {nll_sem:<8.4f} | {nll_full:<8.4f} | {nll_nopref:<8.4f}")
        fold_idx += 1
        
    print("-" * 110)
    print(f"Results (Mean Test Metrics +/- SE):")
    
    cv_summary = {}

    def print_stat(name, metrics_dict, key):
        # Metrics to print
        for metric in ['nll', 'r', 'rmse']:
            scores = metrics_dict[metric]
            mean = np.mean(scores)
            se = np.std(scores, ddof=1) / np.sqrt(K)
            
            print(f"{name:<15} {metric.upper():<4}: {mean:.4f} +/- {se:.4f}")
            
            if key not in cv_summary: cv_summary[key] = {}
            cv_summary[key][metric] = {
                'mean': mean,
                'se': se,
                'scores': scores
            }
        print("-" * 40)
        
    print_stat("Semantics Only", results_cv['sem'], 'sem')
    print_stat("Full Model", results_cv['full'], 'full')
    print_stat("No Preference", results_cv['nopref'], 'nopref')
    print_stat("No Causal", results_cv['nocausal'], 'nocausal')
    
    
    # Merge and Save
    final_output = {
        'global_fits': {
            'full': res_full,
            'sem': res_sem,
            'nopref': res_nopref,
            'nocausal': res_nocausal
        },
        'cv_summary': cv_summary
    }
    
    output_path = 'outputs/model_analysis_results.json'
    print(f"Saving analysis results to {output_path}...")
    with open(output_path, 'w') as f:
        # Convert numpy types to native python for JSON serialization
        def convert(o):
            if isinstance(o, np.int64): return int(o)
            if isinstance(o, np.float64): return float(o)
            if isinstance(o, np.ndarray): return o.tolist()
            return o
            
        json.dump(final_output, f, indent=2, default=convert)


if __name__ == "__main__":
    main()
