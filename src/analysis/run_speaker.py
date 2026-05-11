import os
import json
import numpy as np
from typing import List
from scipy.stats import pearsonr
from sklearn.model_selection import KFold

from src.analysis.fit import VERBS, EPS, SEED, TrialObj, compute_nll, evaluate_metrics, fit_full_model, fit_model_semantics_only, save_detailed_results
from src.model.domains.physical import PhysicalDomain
from src.model.domains.belief import BeliefDomain
from src.model.domains.preference import PreferenceDomain
from src.model.config import ModelConfig
from src.utils.data_loader import load_physical_data, load_belief_data, load_preference_data
from src.utils.metrics import mean_kl_divergence, jsd, tvd


def evaluate_uniform(trials):
    """Evaluate a uniform baseline (prop=0.25 per verb) on a set of trials."""
    uniform_pred = {v: 0.25 for v in VERBS}
    nlls = []
    jsds = []
    tvds = []
    all_human = []
    all_model = []

    for t in trials:
        nlls.append(compute_nll(t.human_dist, uniform_pred))
        jsds.append(jsd(t.human_dist, uniform_pred))
        tvds.append(tvd(t.human_dist, uniform_pred))
        for v in VERBS:
            all_human.append(t.human_dist.get(v, 0.0))
            all_model.append(0.25)

    nlls_arr = np.array(nlls)
    r_val, _ = pearsonr(all_human, all_model) if np.std(all_human) > 0 and np.std(all_model) > 0 else (0.0, 1.0)
    rmse = float(np.sqrt(np.mean((np.array(all_human) - np.array(all_model)) ** 2)))

    n_trials = len(all_human) // 4
    h_groups = [all_human[i * 4:(i + 1) * 4] for i in range(n_trials)]
    m_groups = [all_model[i * 4:(i + 1) * 4] for i in range(n_trials)]
    kl = mean_kl_divergence(h_groups, m_groups)

    return {
        'nll': float(np.mean(nlls_arr)), 'r': r_val, 'rmse': rmse, 'kl': kl,
        'jsd': float(np.mean(jsds)), 'tvd': float(np.mean(tvds)),
        'nlls': list(nlls_arr), 'jsds': jsds, 'tvds': tvds,
        'all_human': all_human, 'all_model': all_model,
    }


def config_from_result(res_dict, model_type='rsa'):
    """Build a ModelConfig from an optimization result dict."""
    return ModelConfig(
        step_cost=res_dict.get('step_cost', 0.05),
        temperature=res_dict.get('temperature', 0.1),
        alpha=res_dict.get('alpha', 1.0),
        alignment_mode='soft',
        cost_caused=res_dict.get('cost_caused', 0.0),
        cost_enabled=res_dict.get('cost_enabled', 0.0),
        cost_allowed=res_dict.get('cost_allowed', 0.0),
        cost_mnd=res_dict.get('cost_made_no_difference', 0.0),
    )


def bootstrap_metrics(human_vals, model_vals, nll_per_trial, jsd_per_trial=None,
                      tvd_per_trial=None, n_boot=1000):
    """Bootstrap SE for NLL, r, RMSE, KL, JSD, TVD by resampling trial groups."""
    n = len(human_vals)
    n_groups = n // 4    # Each trial is a group of 4 verbs
    nll_boots = []
    r_boots = []
    rmse_boots = []
    kl_boots = []
    jsd_boots = []
    tvd_boots = []

    h_arr = np.array(human_vals)
    m_arr = np.array(model_vals)
    nll_arr = np.array(nll_per_trial)
    jsd_arr = np.array(jsd_per_trial) if jsd_per_trial is not None else None
    tvd_arr = np.array(tvd_per_trial) if tvd_per_trial is not None else None
    group_indices = np.arange(n_groups)

    for _ in range(n_boot):
        resamp_groups = np.random.choice(group_indices, size=n_groups, replace=True)
        resamp_idx = np.concatenate([np.arange(g * 4, g * 4 + 4) for g in resamp_groups])
        h_sample = h_arr[resamp_idx]
        m_sample = m_arr[resamp_idx]

        nll_boots.append(float(np.mean(nll_arr[resamp_groups])))

        if np.std(h_sample) > 0 and np.std(m_sample) > 0:
            r_val, _ = pearsonr(h_sample, m_sample)
        else:
            r_val = 0.0
        r_boots.append(r_val)

        rmse_boots.append(np.sqrt(np.mean((h_sample - m_sample) ** 2)))

        h_groups = [h_sample[i * 4:(i + 1) * 4] for i in range(n_groups)]
        m_groups = [m_sample[i * 4:(i + 1) * 4] for i in range(n_groups)]
        kl_boots.append(mean_kl_divergence(h_groups, m_groups))

        if jsd_arr is not None:
            jsd_boots.append(float(np.mean(jsd_arr[resamp_groups])))
        if tvd_arr is not None:
            tvd_boots.append(float(np.mean(tvd_arr[resamp_groups])))

    def _ci95(boots):
        return (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5)))

    result = {
        'nll_se': np.std(nll_boots, ddof=1),
        'r_se': np.std(r_boots, ddof=1),
        'rmse_se': np.std(rmse_boots, ddof=1),
        'kl_se': np.std(kl_boots, ddof=1),
        'nll_ci95': _ci95(nll_boots),
        'r_ci95': _ci95(r_boots),
        'rmse_ci95': _ci95(rmse_boots),
        'kl_ci95': _ci95(kl_boots),
    }
    if jsd_boots:
        result['jsd_se'] = np.std(jsd_boots, ddof=1)
        result['jsd_ci95'] = _ci95(jsd_boots)
    if tvd_boots:
        result['tvd_se'] = np.std(tvd_boots, ddof=1)
        result['tvd_ci95'] = _ci95(tvd_boots)
    return result


def compute_and_print_fit_stats(trials, res_dict, name, model_type='rsa', ablation=None):
    """Evaluate a fitted model on trials with bootstrap SEs, print and return results."""
    config = config_from_result(res_dict, model_type)
    metrics = evaluate_metrics(trials, config, model_type=model_type, ablation=ablation)

    ses = bootstrap_metrics(metrics['all_human'], metrics['all_model'], metrics['nlls'],
                            jsd_per_trial=metrics.get('jsds'),
                            tvd_per_trial=metrics.get('tvds'))

    jsd_ci = ses.get('jsd_ci95', (0, 0))
    tvd_ci = ses.get('tvd_ci95', (0, 0))
    print(f"{name:<20} | NLL: {metrics['nll']:.4f}+/-{ses['nll_se']:.4f} | "
          f"r: {metrics['r']:.3f}+/-{ses['r_se']:.3f} | "
          f"RMSE: {metrics['rmse']:.3f}+/-{ses['rmse_se']:.3f} | "
          f"KL: {metrics['kl']:.4f}+/-{ses['kl_se']:.4f} | "
          f"JSD: {metrics['jsd']:.4f} [{jsd_ci[0]:.4f}, {jsd_ci[1]:.4f}] | "
          f"TVD: {metrics['tvd']:.4f} [{tvd_ci[0]:.4f}, {tvd_ci[1]:.4f}] | ")

    output_dict = res_dict.copy()
    output_dict['optimizer_nll'] = output_dict.pop('nll', None)
    if 'avg_nll' in output_dict:
        del output_dict['avg_nll']

    output_dict.update({
        'name': name,
        'nll': metrics['nll'],
        'nll_se': ses['nll_se'],
        'r': metrics['r'],
        'r_se': ses['r_se'],
        'rmse': metrics['rmse'],
        'rmse_se': ses['rmse_se'],
        'rmse_ci95': list(ses.get('rmse_ci95', (0, 0))),
        'kl': metrics['kl'],
        'kl_se': ses['kl_se'],
        'jsd': metrics['jsd'],
        'jsd_se': ses.get('jsd_se', 0),
        'jsd_ci95': list(ses.get('jsd_ci95', (0, 0))),
        'tvd': metrics['tvd'],
        'tvd_se': ses.get('tvd_se', 0),
        'tvd_ci95': list(ses.get('tvd_ci95', (0, 0)))
    })
    return output_dict


def main():
    np.random.seed(SEED)

    print("Loading data...")
    all_trials: List[TrialObj] = []

    phys_data = load_physical_data()
    phys_dom = PhysicalDomain()
    for td, hd in phys_data:
        all_trials.append(TrialObj('physical', td, hd, phys_dom))

    for td, hd in load_preference_data():
        all_trials.append(TrialObj('preference', td, hd, PreferenceDomain()))

    for td, hd in load_belief_data():
        all_trials.append(TrialObj('belief', td, hd, BeliefDomain()))

    print(f"Total Trials: {len(all_trials)}")

    # helper for global fits
    def fit_global_variant(name, ablation=None, model_type='rsa'):
        print(f"\nFitting Global {name}...")
        if model_type == 'sem':
            return fit_model_semantics_only(all_trials)
        return fit_full_model(all_trials, ablation=ablation)

    # 1. Global Fits (fit on all 38 trials, evaluate on same 38 trials)
    collected_metrics = {}
    print("\n" + "=" * 110)
    print("GLOBAL FITS (parameters fit on all 38 trials, metrics evaluated on same data)")
    print("=" * 110)

    # A. Full Model
    res_full = fit_global_variant("Full Model", ablation=None)
    best_res = res_full

    CI_NOTE = "(\u00b1 values: bootstrap SE, n=1000, resampling trial groups)"
    print(f"\nBest Parameters: step_cost={best_res['step_cost']:.3f}, "
          f"temperature={best_res['temperature']:.3f}, alpha={best_res['alpha']:.3f}")
    print(CI_NOTE)

    collected_metrics['full'] = compute_and_print_fit_stats(
        all_trials, best_res, "Full Model", ablation=None)

    # B. Semantics Only
    res_sem = fit_global_variant("Semantics Only", model_type='sem')
    collected_metrics['sem'] = compute_and_print_fit_stats(
        all_trials, res_sem, "Semantics Only", model_type='sem')

    # C. No Mental State
    res_nopref = fit_global_variant("No Mental State", ablation='no_aligned')
    collected_metrics['nopref'] = compute_and_print_fit_stats(
        all_trials, res_nopref, "No Mental State", ablation='no_aligned')

    # D. No Causal
    res_nocausal = fit_global_variant("No Causal", ablation='no_causal')
    collected_metrics['nocausal'] = compute_and_print_fit_stats(
        all_trials, res_nocausal, "No Causal", ablation='no_causal')

    # E. Uniform Baseline
    print("\nEvaluating Uniform Baseline...")
    uniform_metrics = evaluate_uniform(all_trials)
    uniform_ses = bootstrap_metrics(
        uniform_metrics['all_human'], uniform_metrics['all_model'],
        uniform_metrics['nlls'],
        jsd_per_trial=uniform_metrics.get('jsds'),
        tvd_per_trial=uniform_metrics.get('tvds'))

    jsd_ci = uniform_ses.get('jsd_ci95', (0, 0))
    tvd_ci = uniform_ses.get('tvd_ci95', (0, 0))
    print(f"{'Uniform':<20} | NLL: {uniform_metrics['nll']:.4f}+/-{uniform_ses['nll_se']:.4f} | "
          f"RMSE: {uniform_metrics['rmse']:.3f}+/-{uniform_ses['rmse_se']:.3f} | "
          f"KL: {uniform_metrics['kl']:.4f}+/-{uniform_ses['kl_se']:.4f} | "
          f"JSD: {uniform_metrics['jsd']:.4f} [{jsd_ci[0]:.4f}, {jsd_ci[1]:.4f}] | "
          f"TVD: {uniform_metrics['tvd']:.4f} [{tvd_ci[0]:.4f}, {tvd_ci[1]:.4f}] | ")
    collected_metrics['uniform'] = {
        'name': 'Uniform',
        'nll': uniform_metrics['nll'],
        'nll_se': uniform_ses['nll_se'],
        'r': uniform_metrics['r'],
        'r_se': uniform_ses['r_se'],
        'rmse': uniform_metrics['rmse'],
        'rmse_se': uniform_ses['rmse_se'],
        'rmse_ci95': list(uniform_ses.get('rmse_ci95', (0, 0))),
        'kl': uniform_metrics['kl'],
        'kl_se': uniform_ses['kl_se'],
        'jsd': uniform_metrics['jsd'],
        'jsd_se': uniform_ses.get('jsd_se', 0),
        'jsd_ci95': list(uniform_ses.get('jsd_ci95', (0, 0))),
        'tvd': uniform_metrics['tvd'],
        'tvd_se': uniform_ses.get('tvd_se', 0),
        'tvd_ci95': list(uniform_ses.get('tvd_ci95', (0, 0)))
    }

    # Set final best state with best config (Full Model)
    best_config = config_from_result(best_res)
    final_phys_dom = PhysicalDomain(config=best_config)
    final_pref_dom = PreferenceDomain(config=best_config)
    final_belief_dom = BeliefDomain(config=best_config)

    # Update states for saving detailed results
    for t in all_trials:
        if t.domain_name == 'physical':
            t.state = final_phys_dom.get_domain_state(t.trial_data)
            t.theta = final_phys_dom.inference.infer_most_likely_theta(t.trial_data)
        elif t.domain_name == 'preference':
            t.state = final_pref_dom.get_domain_state(t.trial_data)
        elif t.domain_name == 'belief':
            t.state = final_belief_dom.get_domain_state(t.trial_data)

    # Save outputs
    other_configs = {
        'sem': res_sem,
        'nopref': res_nopref,
        'nocausal': res_nocausal
    }
    save_detailed_results(all_trials, best_config, other_configs=other_configs)
    os.makedirs('outputs', exist_ok=True)

    # 2. Cross Validation
    K = 5
    kf = KFold(n_splits=K, shuffle=True, random_state=SEED)

    print("\n" + "=" * 110)
    print(f"{K}-FOLD CROSS-VALIDATION (parameters fit on training folds, "
          f"metrics evaluated on held-out test fold)")
    print("(" + "\u00b1" + " values: SE across folds)")
    print("=" * 110)
    print(f"\nFold   | Params (Full)                  | Sem      | Full     "
          f"| NoPref   | NoCausal     (avg NLL)")
    print("-" * 110)

    fold_idx = 1
    results_cv = {
        key: {m: [] for m in ['nll', 'r', 'rmse', 'kl', 'jsd', 'tvd']}
        for key in ['sem', 'full', 'nopref', 'nocausal', 'uniform']
    }

    for train_idx, test_idx in kf.split(all_trials):
        train_set = [all_trials[i] for i in train_idx]
        test_set = [all_trials[i] for i in test_idx]

        # Semantics Only
        best_sem_res = fit_model_semantics_only(train_set)
        sem_config = config_from_result(best_sem_res, model_type='sem')
        sem_metrics = evaluate_metrics(test_set, sem_config, model_type='sem')

        # Helper to fit and evaluate on test
        def fit_eval_model_cv(ablation=None):
            res = fit_full_model(train_set, ablation=ablation)
            config = config_from_result(res)
            metrics = evaluate_metrics(test_set, config, ablation=ablation)
            return metrics, res

        # Full, No Mental State Inference, No Causal Inference
        full_metrics, res_full_cv = fit_eval_model_cv(ablation=None)
        nopref_metrics, _ = fit_eval_model_cv(ablation='no_aligned')
        nocausal_metrics, _ = fit_eval_model_cv(ablation='no_causal')

        # Uniform baseline (no fitting)
        uniform_cv_metrics = evaluate_uniform(test_set)

        # Store
        for key, m in [('sem', sem_metrics), ('full', full_metrics),
                       ('nopref', nopref_metrics), ('nocausal', nocausal_metrics),
                       ('uniform', uniform_cv_metrics)]:
            for metric in ['nll', 'r', 'rmse', 'kl', 'jsd', 'tvd']:
                results_cv[key][metric].append(m[metric])

        params_str = (f"c={res_full_cv['step_cost']:.2f},"
                      f"T={res_full_cv['temperature']:.2f},"
                      f"\u03b1={res_full_cv['alpha']:.2f}")
        print(f"{fold_idx:<6} | {params_str:<30} | {sem_metrics['nll']:<8.4f} | "
              f"{full_metrics['nll']:<8.4f} | {nopref_metrics['nll']:<8.4f} | "
              f"{nocausal_metrics['nll']:<8.4f}")
        fold_idx += 1

    print("-" * 110)
    print("\nHeld-out test metrics (mean +/- SE across folds):")

    cv_summary = {}

    def print_stat(name, metrics_dict, key):
        for metric in ['nll', 'r', 'rmse', 'kl', 'jsd', 'tvd']:
            scores = metrics_dict[metric]
            mean = np.mean(scores)
            se = np.std(scores, ddof=1) / np.sqrt(K)
            print(f"{name:<15} {metric.upper():<8}: {mean:.4f} +/- {se:.4f}")
            if key not in cv_summary:
                cv_summary[key] = {}
            cv_summary[key][metric] = {
                'mean': mean,
                'se': se,
                'scores': scores
            }
        print("-" * 40)

    print_stat("Semantics Only", results_cv['sem'], 'sem')
    print_stat("Full Model", results_cv['full'], 'full')
    print_stat("No Mental State", results_cv['nopref'], 'nopref')
    print_stat("No Causal", results_cv['nocausal'], 'nocausal')
    print_stat("Uniform", results_cv['uniform'], 'uniform')

    # Save outputs
    final_output = {
        'global_fits': collected_metrics,
        'cv_summary': cv_summary
    }

    output_path = 'outputs/model_results.json'
    print(f"Saving analysis results to {output_path}...")
    with open(output_path, 'w') as f:
        def convert(o):
            if isinstance(o, np.int64): return int(o)
            if isinstance(o, np.float64): return float(o)
            if isinstance(o, np.ndarray): return o.tolist()
            return o

        json.dump(final_output, f, indent=2, default=convert)


if __name__ == "__main__":
    main()
