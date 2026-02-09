from src.analysis.fit import *


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
        
        # Merge input parameters
        output_dict = res_dict.copy()
        output_dict['optimizer_nll'] = output_dict.pop('nll', None) 
        if 'avg_nll' in output_dict:
            del output_dict['avg_nll'] 
        
        output_dict.update({
            'name': name,
            'nll': mean_nll,
            'nll_se': se_nll,
            'r': r,
            'r_se': r_se,
            'rmse': rmse,
            'rmse_se': rmse_se
        })
        
        return output_dict

    
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
                res = fit_full_model(all_trials, necessity_mode=m, ablation=ablation)
            
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
    
    # Save outputs
    other_configs = {
        'sem': res_sem,
        'nopref': res_nopref,
        'nocausal': res_nocausal
    }
    save_detailed_results(all_trials, best_config, other_configs=other_configs)
    if not os.path.exists('outputs'):
        os.makedirs('outputs')


    # 2. Cross Validation
    K = 5
    kf = KFold(n_splits=K, shuffle=True, random_state=SEED)
    
    print(f"\nRunning {K}-Fold Comprehensive Cross-Validation...")
    print(f"Fold   | Params (Full)                  | Sem      | Full     | NoPref   | NoCausal     (avg NLL)")
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
                res = fit_full_model(train_set, necessity_mode=m, ablation=ablation)
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
        
        print(f"{fold_idx:<6} | {params_str:<30} | {nll_sem:<8.4f} | {nll_full:<8.4f} | {nll_nopref:<8.4f} | {nll_no_causal:<8.4f}")
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
