"""
Run ablation experiments to test which semantic variables matter.

Ablations:
1. no_aligned: Remove preference inference (A → 0.5)
2. no_causal: Remove causal reasoning (control → 1.0, necessity → 1.0)
3. no_aligned_no_causal: Remove both

Also compares to S0 (No Pragmatics, α=0) baseline.
Saves results to outputs/ablation_results.json and outputs/ablation_results.csv.
"""

import numpy as np
import importlib.util
import json
import os
from typing import List, Dict, Tuple, Any
from sklearn.model_selection import KFold
from scipy.optimize import minimize, minimize_scalar
from datetime import datetime

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load data_loader directly to bypass utils.py shadowing utils/
spec = importlib.util.spec_from_file_location("data_loader", PROJECT_ROOT / "src" / "utils" / "data_loader.py")
data_loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_loader)
load_physical_data = data_loader.load_physical_data
load_belief_data = data_loader.load_belief_data
load_preference_data = data_loader.load_preference_data

from src.model.domains.physical import PhysicalDomain
from src.model.domains.belief import BeliefDomain
from src.model.domains.preference import PreferenceDomain
from src.model.rsa import RSACausalVerbModel
from src.model.classifier import ABLATION_TYPES

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


def compute_nll(human_dist: Dict[str, float], model_dist: Dict[str, float]) -> float:
    """Compute NLL for a single trial."""
    nll = 0.0
    for v in VERBS:
        p_h = human_dist.get(v, 0.0)
        p_m = max(model_dist.get(v, 0.0), EPS)
        if p_h > 0:
            nll -= p_h * np.log(p_m)
    return nll


def evaluate_dataset(trials: List[TrialObj], alpha: float, ablation: str = None) -> float:
    """Compute total NLL for a dataset with specified ablation."""
    total_nll = 0.0
    rsa_model = RSACausalVerbModel(
        rationality_alpha=alpha,
        use_valence_cost=False,  # Keep simple for ablation comparison
        ablation=ablation
    )
    
    for t in trials:
        preds = rsa_model.pragmatic_speaker_s1(t.state)
        total_nll += compute_nll(t.human_dist, preds)
        
    return total_nll


def evaluate_dataset_s0(trials: List[TrialObj], ablation: str = None) -> float:
    """Compute total NLL using S0 (literal semantics, no pragmatics).
    
    This is equivalent to α=0, where the model just uses P(u|w) without
    the P(u) informativeness normalization.
    """
    from src.model.classifier import InertialVerbClassifier
    
    total_nll = 0.0
    classifier = InertialVerbClassifier(ablation=ablation)
    
    for t in trials:
        # S0 is just the normalized classifier output
        sem_probs = classifier.get_verb_probabilities(t.state)
        total_nll += compute_nll(t.human_dist, sem_probs)
        
    return total_nll


def fit_alpha(trials: List[TrialObj], ablation: str = None, fixed_alpha: float = None) -> Tuple[float, float]:
    """Fit alpha parameter for given ablation. Returns (alpha, nll).
    
    If fixed_alpha is provided, skip fitting and use that value.
    """
    if fixed_alpha is not None:
        nll = evaluate_dataset(trials, fixed_alpha, ablation=ablation)
        return fixed_alpha, nll
    
    def loss(a):
        return evaluate_dataset(trials, a, ablation=ablation)
    
    res = minimize_scalar(loss, bounds=(0, 20), method='bounded')
    return res.x, res.fun


def load_all_trials() -> List[TrialObj]:
    """Load all trial data from all domains."""
    all_trials = []
    
    # Physical
    try:
        phys_dom = PhysicalDomain()
        for td, hd in load_physical_data():
            all_trials.append(TrialObj('physical', td, hd, phys_dom))
        print(f"  Physical: {sum(1 for t in all_trials if t.domain_name == 'physical')} trials")
    except Exception as e:
        print(f"  Physical: skipped ({e})")
    
    # Preference
    try:
        pref_dom = PreferenceDomain()
        before = len(all_trials)
        for td, hd in load_preference_data():
            all_trials.append(TrialObj('preference', td, hd, pref_dom))
        print(f"  Preference: {len(all_trials) - before} trials")
    except Exception as e:
        print(f"  Preference: skipped ({e})")
    
    # Belief
    try:
        belief_dom = BeliefDomain()
        before = len(all_trials)
        for td, hd in load_belief_data():
            all_trials.append(TrialObj('belief', td, hd, belief_dom))
        print(f"  Belief: {len(all_trials) - before} trials")
    except Exception as e:
        print(f"  Belief: skipped ({e})")
    
    return all_trials


def run_global_fit(trials: List[TrialObj]) -> Dict[str, Any]:
    """Run global fit for all model variants including S0 baseline.
    
    Returns structured dict with all results.
    """
    print("\n" + "=" * 70)
    print("GLOBAL FIT (All Data)")
    print("=" * 70)
    
    ablations = [None, 'no_aligned', 'no_causal', 'no_aligned_no_causal']
    ablation_names = {
        None: 'Full Model (S1)',
        'no_aligned': 'No Preference Inference',
        'no_causal': 'No Causal Reasoning',
        'no_aligned_no_causal': 'No Aligned + No Causal'
    }
    
    results = []
    
    # S0 Baseline (No Pragmatics) - uses classifier directly
    s0_nll = evaluate_dataset_s0(trials, ablation=None)
    results.append({
        'model': 'S0 (No Pragmatics)',
        'ablation': 'S0',
        'alpha': 0.0,
        'nll': s0_nll
    })
    
    # S1 models with different ablations
    for abl in ablations:
        alpha, nll = fit_alpha(trials, ablation=abl)
        results.append({
            'model': ablation_names[abl],
            'ablation': abl if abl else 'none',
            'alpha': alpha,
            'nll': nll
        })
    
    # Sort by NLL (best first)
    results.sort(key=lambda x: x['nll'])
    best_nll = results[0]['nll']
    
    # Add delta
    for r in results:
        r['delta_nll'] = r['nll'] - best_nll
    
    print(f"\n{'Model':<35} | {'α':>8} | {'NLL':>10} | {'ΔNLL':>10}")
    print("-" * 72)
    
    for r in results:
        marker = "★" if r['delta_nll'] == 0 else ""
        print(f"{r['model']:<35} | {r['alpha']:>8.3f} | {r['nll']:>10.2f} | {r['delta_nll']:>+10.2f} {marker}")
    
    return {'global_fit': results}


def run_cross_validation(trials: List[TrialObj], k: int = 5) -> Dict[str, Any]:
    """Run k-fold cross-validation for all model variants including S0 baseline.
    
    Returns structured dict with fold results and summaries.
    """
    print("\n" + "=" * 70)
    print(f"{k}-FOLD CROSS-VALIDATION")
    print("=" * 70)
    
    np.random.seed(SEED)
    kf = KFold(n_splits=k, shuffle=True, random_state=SEED)
    
    # Model configs: (name, ablation, use_s0)
    models = [
        ('S0 (No Pragmatics)', None, True),
        ('Full Model (S1)', None, False),
        ('No Aligned', 'no_aligned', False),
        ('No Causal', 'no_causal', False),
        ('No Both', 'no_aligned_no_causal', False),
    ]
    
    all_scores = {m[0]: [] for m in models}
    all_alphas = {m[0]: [] for m in models}
    
    print(f"\n{'Fold':<6}", end="")
    for name, _, _ in models:
        print(f" | {name:<18}", end="")
    print()
    print("-" * 110)
    
    for fold_idx, (train_idx, test_idx) in enumerate(kf.split(trials)):
        train_set = [trials[i] for i in train_idx]
        test_set = [trials[i] for i in test_idx]
        
        print(f"{fold_idx+1:<6}", end="")
        
        for name, abl, use_s0 in models:
            if use_s0:
                # S0: no fitting, just evaluate
                nll = evaluate_dataset_s0(test_set, ablation=abl)
                all_scores[name].append(nll)
                all_alphas[name].append(0.0)
            else:
                # S1: fit on train, evaluate on test
                alpha, _ = fit_alpha(train_set, ablation=abl)
                nll = evaluate_dataset(test_set, alpha, ablation=abl)
                all_scores[name].append(nll)
                all_alphas[name].append(alpha)
            
            print(f" | {nll:<18.2f}", end="")
        
        print()
    
    # Summary statistics
    print("-" * 110)
    print("\nSummary (Mean NLL ± SE):")
    print(f"{'Model':<30} | {'Mean NLL':>12} | {'SE':>8} | {'Mean α':>8}")
    print("-" * 70)
    
    summary_results = []
    for name, abl, use_s0 in models:
        scores = all_scores[name]
        alphas = all_alphas[name]
        mean_nll = np.mean(scores)
        se_nll = np.std(scores, ddof=1) / np.sqrt(k)
        mean_alpha = np.mean(alphas)
        summary_results.append({
            'model': name,
            'ablation': 'S0' if use_s0 else (abl if abl else 'none'),
            'mean_nll': mean_nll,
            'se_nll': se_nll,
            'mean_alpha': mean_alpha,
            'fold_scores': scores,
            'fold_alphas': alphas
        })
    
    # Sort by mean NLL
    summary_results.sort(key=lambda x: x['mean_nll'])
    best_mean = summary_results[0]['mean_nll']
    
    for r in summary_results:
        r['delta_nll'] = r['mean_nll'] - best_mean
        marker = "★" if r['delta_nll'] == 0 else ""
        print(f"{r['model']:<30} | {r['mean_nll']:>12.2f} | {r['se_nll']:>8.2f} | {r['mean_alpha']:>8.3f} {marker}")
    
    # Statistical significance tests (paired t-test)
    from scipy.stats import ttest_rel
    
    print("\n" + "-" * 70)
    print("Statistical Significance (paired t-test vs best model):")
    print(f"{'Comparison':<40} | {'t-stat':>8} | {'p-value':>10}")
    print("-" * 70)
    
    best_model = summary_results[0]
    best_scores = best_model['fold_scores']
    
    for r in summary_results[1:]:  # Skip best model
        t_stat, p_value = ttest_rel(best_scores, r['fold_scores'])
        sig = "**" if p_value < 0.05 else ""
        r['p_value'] = p_value
        r['t_stat'] = t_stat
        print(f"{best_model['model']} vs {r['model']:<15} | {t_stat:>8.3f} | {p_value:>10.4f} {sig}")
    
    best_model['p_value'] = None
    best_model['t_stat'] = None
    
    return {'cross_validation': summary_results}


def analyze_marginals():
    """Compare P(u) marginals across ablation conditions."""
    print("\n" + "=" * 70)
    print("P(u) MARGINALS BY ABLATION")
    print("=" * 70)
    
    ablations = [None, 'no_aligned', 'no_causal', 'no_aligned_no_causal']
    ablation_names = {
        None: 'Full',
        'no_aligned': 'No Aligned',
        'no_causal': 'No Causal',
        'no_aligned_no_causal': 'No Both'
    }
    
    print(f"\n{'Verb':<20}", end="")
    for abl in ablations:
        print(f" | {ablation_names[abl]:<12}", end="")
    print()
    print("-" * 75)
    
    for verb in VERBS:
        print(f"{verb:<20}", end="")
        for abl in ablations:
            rsa = RSACausalVerbModel(ablation=abl)
            marginal = rsa.verb_marginals[verb]
            print(f" | {marginal:<12.4f}", end="")
        print()


def save_results(results: Dict[str, Any], output_dir: str = 'outputs'):
    """Save ablation experiment results to JSON and CSV."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Add metadata
    results['metadata'] = {
        'timestamp': datetime.now().isoformat(),
        'seed': SEED,
        'n_trials': results.get('n_trials', 0)
    }
    
    # Save JSON
    json_path = os.path.join(output_dir, 'ablation_results.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved results to {json_path}")
    
    # Save CSV (summary table)
    csv_path = os.path.join(output_dir, 'ablation_results.csv')
    with open(csv_path, 'w') as f:
        # Header
        f.write("source,model,ablation,alpha,nll,delta_nll,se_nll\n")
        
        # Global fit
        for r in results.get('global_fit', []):
            f.write(f"global,{r['model']},{r['ablation']},{r['alpha']:.4f},{r['nll']:.4f},{r['delta_nll']:.4f},\n")
        
        # Cross-validation
        for r in results.get('cross_validation', []):
            f.write(f"cv,{r['model']},{r['ablation']},{r['mean_alpha']:.4f},{r['mean_nll']:.4f},{r['delta_nll']:.4f},{r['se_nll']:.4f}\n")
    
    print(f"Saved CSV to {csv_path}")


def main():
    print("=" * 70)
    print("RUNNING ABLATION EXPERIMENTS")
    print("=" * 70)
    
    print(f"\nLoading data...")
    trials = load_all_trials()
    print(f"Loaded {len(trials)} trials")
    
    # Collect all results
    all_results = {
        'n_trials': len(trials),
        'necessity_mode': 'derived (C*V)'
    }
    
    # 1. Analyze how ablations affect P(u) marginals
    analyze_marginals()
    
    # 2. Global fit
    global_results = run_global_fit(trials)
    all_results.update(global_results)
    
    # 3. Cross-validation
    cv_results = run_cross_validation(trials, k=5)
    all_results.update(cv_results)
    
    # 4. Save results
    save_results(all_results, output_dir='outputs/ablation_results')
    
    print("\n" + "=" * 70)
    print("EXPERIMENT COMPLETE")
    print("=" * 70)
    print("""
Results saved to outputs/ablation_results/
""")


if __name__ == "__main__":
    main()

