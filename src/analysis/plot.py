import os
import csv
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Any
import pandas as pd
import matplotlib.colors as mcolors
import json

from matplotlib.patches import Patch
from matplotlib.legend_handler import HandlerBase
from matplotlib.text import Text
from matplotlib.lines import Line2D
from scipy.stats import pearsonr
from src.utils import load_human_data, get_trial_response_counts
from src.analysis.human import normalize_response_counts, bootstrap_human_data, get_error_bars
from src.utils.plotting import COLORS as VERB_COLORS


class HeaderItem:
    def __init__(self, text):
        self.text = text

class HandlerHeader(HandlerBase):
    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize,
                       trans):
        t = Text(0, height/2, orig_handle.text, 
                 fontsize=fontsize, verticalalignment='center', fontweight='bold')
        return [t]


def load_predictions(csv_path: str) -> Dict[str, List[Dict[str, Any]]]:
    data_by_domain = {'physical': [], 'preference': [], 'belief': []}
    VERBS = ['caused', 'enabled', 'allowed', 'made_no_difference']
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = row['domain']
            tid = row['trial_id']
            
            def get_dist(suffix):
                return {v: float(row.get(f'pred_{v}_{suffix}', 0.0)) for v in VERBS}
                
            entry = {
                'trial_id': tid,
                'human_n': int(row.get('human_n', 0)),
                'human': {v: float(row.get(f'human_{v}', 0.0)) for v in VERBS},
                'full': get_dist('full'),
                'nopref': get_dist('nopref'),
                'nocausal': get_dist('nocausal'),
                'sem': get_dist('sem'),
            }
            
            entry['trial_data'] = None
                
            if domain in data_by_domain:
                data_by_domain[domain].append(entry)
    return data_by_domain

OUTPUT_DIR = "outputs/plots/"
PREDICTIONS_CSV = 'outputs/model_predictions_full.csv'
VERBS = ['caused', 'enabled', 'allowed', 'made_no_difference']
VERB_LABELS = ['Caused', 'Enabled', 'Allowed', 'Made no difference']


def load_and_bootstrap_all_domains(base_dir="data"):
    """Load raw data and bootstrap CIs for all domains."""
    domains = {
        'physical': 'physical_speaker',
        'belief': 'belief_speaker',
        'preference': 'preference_speaker'
    }
    
    domain_errors = {}
    print("Bootstrapping error bars for all domains...")
    
    for name, subdir in domains.items():
        path = os.path.join(base_dir, subdir)
        if os.path.exists(path):
            print(f"  Processing {name}...")
            df = load_human_data(path)

            domain_errors[name] = bootstrap_human_data(df, n_bootstrap=1000, seed=42)
        else:
            print(f"Warning: Data path not found: {path}")
            domain_errors[name] = None
            
    return domain_errors

def get_trial(domain_data, trial_id_suffix):
    """Find a trial by its ID suffix (e.g. 'trial_c' or 'c')."""
    target = trial_id_suffix.lower()
    if not target.startswith('trial_'):
        target = f"trial_{target}"
        
    for t in domain_data:
        if t['trial_id'] == target:
            return t
    return None

def compute_nll(human_dist, model_dist):
    nll = 0.0
    epsilon = 1e-10
    for v in VERBS:
        p_h = human_dist.get(v, 0.0)
        p_m = model_dist.get(v, 0.0)
        p_m = max(p_m, epsilon)
        if p_h > 0:
            nll -= p_h * np.log(p_m)
    return nll

def plot_human_model_trial_comparison(all_results, domain_errors):
    """
    Specific Trial Comparison
    2x3 Grid
    Physical: C, E
    Belief: D, E
    Preference: G, D
    """
    fig, axes = plt.subplots(2, 3, figsize=(6.5, 3), layout='constrained')
    fig.set_constrained_layout_pads(wspace=0.2, hspace=0.15)
    
    # Define grid targets
    targets = [
        ('physical', 'a', axes[0, 0], "Physical Trial C"),
        ('physical', 'i', axes[1, 0], "Physical Trial E"),
        ('belief', 'd', axes[0, 1], "Belief Trial D"),
        ('belief', 'e', axes[1, 1], "Belief Trial E"),
        ('preference', 'g', axes[0, 2], "Preference Trial G"),
        ('preference', 'd', axes[1, 2], "Preference Trial D"),
    ]
    
    x = np.arange(len(VERBS))
    width = 0.35

    for domain, tid, ax, title in targets:
        trial = get_trial(all_results[domain], tid)
        if not trial:
            ax.text(0.5, 0.5, f"Missing {domain} {tid}", ha='center')
            continue
            
        human_vals = [trial['human'].get(v, 0.0) for v in VERBS]
        model_vals = [trial['full'].get(v, 0.0) for v in VERBS]
        
        # Get bootstrapped error bars
        full_tid = tid if tid.startswith('trial_') else f"trial_{tid}"
        
        yerr_lower, yerr_upper = get_error_bars(full_tid, VERBS, np.array(human_vals), domain_errors.get(domain))

        # Plot bars per verb
        for i, v in enumerate(VERBS):
            c = VERB_COLORS.get(v, 'gray')
            # Human
            err = [[yerr_lower[i]], [yerr_upper[i]]] if yerr_lower is not None else None
            
            ax.bar(x[i] - width/2, human_vals[i], width, color=c, 
                   yerr=err, ecolor='#5C5C5C', capsize=2, error_kw={'elinewidth': 1.0},
                   label='Human' if i==0 else "")
            
            # Model 
            c_rgba = mcolors.to_rgba(c, alpha=0.3)
            ax.bar(x[i] + width/2, model_vals[i], width, facecolor=c_rgba, edgecolor='none', label='Model' if i==0 else "")

            ax.bar(x[i] + width/2, model_vals[i], width, facecolor='none', edgecolor=c, hatch='///', linewidth=0)

        # ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(['C', 'E', 'A', 'N'])
        ax.set_ylim(0, 1.0)
        ax.set_yticks([0.0, 0.5, 1.0])
        
        if domain == 'physical':
            ax.set_ylabel("Proportion")
            
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        ax.spines['bottom'].set_color('#808080')
        ax.spines['left'].set_color('#808080')
        ax.tick_params(axis='x', colors='#808080')
        ax.tick_params(axis='y', colors='#808080')
        
    # Legend
    gray_rgba = mcolors.to_rgba('gray', alpha=0.3)
    legend_elements = [
        Patch(facecolor='gray', label='Human', edgecolor='gray', linewidth=1.0),
        Patch(facecolor='none', hatch='///', edgecolor='gray', label='Full Model', linewidth=1.0)
    ]

    fig.legend(handles=legend_elements, loc='upper center', fontsize=10,
               bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    save_path = os.path.join(OUTPUT_DIR, "human_model.png")
    plt.savefig(save_path, dpi=1200, bbox_inches='tight')
    print(f"Saved {save_path}")


def plot_scatter_comparison(all_results, domain_errors):
    """
    Scatter plots of Human vs Model predictions
    1x4 Row: Full, No Causal, No Preference, Semantics
    Each point is a (Trial, Verb) pair.
    """
    models = ['full', 'nocausal', 'nopref', 'sem']
    model_labels = ['Full Model', 'No Causal Inference', 'No Mental State Inference', 'No Pragmatics']
    
    fig, axes = plt.subplots(1, 4, figsize=(10, 2.8), layout='constrained')
    axes = axes.flatten()
    
    # Collect data for all domains
    data_per_model = {m: {'x': [], 'y': [], 'y_err_lower': [], 'y_err_upper': [], 'c': [], 'domain': []} for m in models}
    
    MARKERS = {'physical': 'o', 'belief': 's', 'preference': '^'}
    DOMAIN_LABELS = {'physical': 'Physical', 'belief': 'Belief', 'preference': 'Preference'}
    
    for domain, domain_trials in all_results.items():
        # Get errors for this domain
        d_errors = domain_errors.get(domain)
        
        for trial in domain_trials:
            N = max(trial.get('human_n', 0), 1) 
            # Construct full tid
            tid = trial['trial_id']
            full_tid = tid if tid.startswith('trial_') else f"trial_{tid}"
        
            trial_human_vals = np.array([trial['human'].get(v, 0.0) for v in VERBS])
            l_errs, u_errs = get_error_bars(full_tid, VERBS, trial_human_vals, d_errors)
            
            # Map verb -> (l, u)
            verb_err_map = {}
            if l_errs is not None:
                for i, v in enumerate(VERBS):
                    verb_err_map[v] = (l_errs[i], u_errs[i])
            else: # regular CIs
                print(f"Using regular (not bootstrapped) CIs for {domain} {tid}")
                for i, v in enumerate(VERBS):
                    p = trial_human_vals[i]
                    se = np.sqrt(p * (1 - p) / N)
                    verb_err_map[v] = (1.96 * se, 1.96 * se)

            for v in VERBS:
                h_val = trial['human'].get(v, 0.0)
                l_err, u_err = verb_err_map.get(v, (0, 0))
                
                for m in models:
                    m_val = trial[m].get(v, 0.0)
                    
                    # Flip axes: X = Model, Y = Human
                    data_per_model[m]['x'].append(m_val)
                    data_per_model[m]['y'].append(h_val)
                    data_per_model[m]['y_err_lower'].append(l_err)
                    data_per_model[m]['y_err_upper'].append(u_err)
                    data_per_model[m]['c'].append(VERB_COLORS[v])
                    data_per_model[m]['domain'].append(domain)


    # Load global metrics
    metrics_path = 'outputs/model_results.json'
    global_metrics = {}
    if os.path.exists(metrics_path):
        with open(metrics_path, 'r') as f:
            global_metrics = json.load(f)
            
    # Plot
    for i, m in enumerate(models):
        ax = axes[i]
        
        x = np.array(data_per_model[m]['x'])
        y = np.array(data_per_model[m]['y'])
        lower = np.array(data_per_model[m]['y_err_lower'])
        upper = np.array(data_per_model[m]['y_err_upper'])
        y_err = [lower, upper]
        
        colors = np.array(data_per_model[m]['c'])
        domains = np.array(data_per_model[m]['domain'])
        
        # Plot points per domain
        for dom, marker in MARKERS.items():
            mask = domains == dom
            if np.any(mask):
                # Error bars
                y_err_masked = [lower[mask], upper[mask]]
                
                ax.errorbar(x[mask], y[mask], yerr=y_err_masked, fmt='none', 
                            ecolor=colors[mask], alpha=0.3, elinewidth=0.8, capsize=0, zorder=1)
                
                # Points
                ax.scatter(x[mask], y[mask], c=colors[mask], marker=marker, 
                           alpha=0.7, s=40, edgecolors='w', linewidth=0.5, zorder=2)
        
        # Diagonal line
        ax.plot([0, 1], [0, 1], color='black', linestyle=(0, (4, 4)), alpha=0.2, zorder=0)
        
        # Stats
        if 'global_fits' in global_metrics and m in global_metrics['global_fits']:
            # Use pre-computed global metrics with SE
            gm = global_metrics['global_fits'][m]
            r, r_se = gm['r'], gm['r_se']
            rmse, rmse_se = gm['rmse'], gm['rmse_se']
            stats_text = f"$r={r:.2f}$\nRMSE$={rmse:.2f}$"
        else:
            # Otherwise compute
            r, p = pearsonr(x, y)
            rmse = np.sqrt(np.mean((x - y)**2))
            stats_text = f"$r={r:.2f}$\nRMSE$={rmse:.2f}$"
            
        # ax.set_title(model_labels[i])
        
        # Add stats text in bottom-right
        ax.text(0.95, 0.05, stats_text, transform=ax.transAxes, 
                verticalalignment='bottom', horizontalalignment='right',
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='lightgray'))

        ax.set_xlim(0, 1.05)
        ax.set_ylim(0, 1.05)
        ax.set_aspect('equal')
        
        ticks = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        
        ax.set_xlabel(model_labels[i])
        if i == 0: 
            ax.set_ylabel("Human Proportion")
            
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        ax.spines['bottom'].set_color('#808080')
        ax.spines['left'].set_color('#808080')
        ax.tick_params(axis='x', colors='#808080')
        ax.tick_params(axis='y', colors='#808080')

    expression_header = HeaderItem('Expression (color)')
    experiment_header = HeaderItem('Experiment (marker)')
    
    verb_elements = [Line2D([0], [0], marker='o', color='w', label=l,
                          markerfacecolor=VERB_COLORS[v], markersize=9) 
                          for v, l in zip(VERBS, VERB_LABELS)]
                          
    domain_elements = [Line2D([0], [0], marker=MARKERS[d], color='w', label=DOMAIN_LABELS[d],
                            markerfacecolor='gray', markersize=9)
                            for d in ['physical', 'belief', 'preference']]
                            

    handles = [expression_header] + verb_elements + [Line2D([0], [0], color='w', label='')] + [experiment_header] + domain_elements
    labels = [''] + VERB_LABELS + [''] + [''] + [DOMAIN_LABELS[d] for d in ['physical', 'belief', 'preference']]
    
    # Legend to the right 
    fig.legend(handles=handles, labels=labels, loc='center left', bbox_to_anchor=(1.0, 0.5), 
               ncol=1, frameon=False, 
               handletextpad=0.4, handlelength=1.0, borderaxespad=0.1,
               handler_map={HeaderItem: HandlerHeader()})
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    save_path = os.path.join(OUTPUT_DIR, "model_scatter.png")
    plt.savefig(save_path, dpi=1200, bbox_inches='tight')
    print(f"Saved {save_path}")


def main():
    print("Loading predictions...")
    if not os.path.exists(PREDICTIONS_CSV):
        print(f"Error: {PREDICTIONS_CSV} not found. Please run model_results.py first.")
        # return
        
    all_results = None
    if not os.path.exists('outputs/plots/'):
        os.makedirs('outputs/plots/')
    
    if os.path.exists(PREDICTIONS_CSV):
        all_results = load_predictions(PREDICTIONS_CSV)
        
        # Load and bootstrap human data for all domains 
        domain_errors = load_and_bootstrap_all_domains()
        
        print("Generating human-model trial comparison figure...")
        plot_human_model_trial_comparison(all_results, domain_errors)
        
        print("Generating scatter comparison figure...")
        plot_scatter_comparison(all_results, domain_errors)
    

if __name__ == "__main__":
    main()
