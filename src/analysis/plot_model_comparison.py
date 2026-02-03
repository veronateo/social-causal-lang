import os
import csv
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Callable
from textwrap import fill

from src.utils.plotting import colors
from src.utils.visualize import draw_physical_scenario
from src.utils.data_loader import load_physical_data, load_preference_data, load_belief_data

OUTPUT_DIR = "plots"
PREDICTIONS_CSV = 'outputs/model_predictions_debug.csv'
VERBS = ['caused', 'enabled', 'allowed', 'made_no_difference']

# Trial definitions (keep existing)
TRIAL_DEFINITIONS = {
    # Preference
    'preference_trial_a': {'title': 'A', 'desc': '1B v 2A -> 1B v 3A\nLeft, add right, right'},
    'preference_trial_b': {'title': 'B', 'desc': '1B v 2A -> 1B v 2A\nLeft, nothing, left'},
    'preference_trial_c': {'title': 'C', 'desc': '1B v 2A -> 1B+1A v 2A\nRight, add left, left'},
    'preference_trial_d': {'title': 'D', 'desc': '1B v 2A -> 1B v 3A\nRight, add right, right'},
    'preference_trial_e': {'title': 'E', 'desc': '2B v 1A -> 2B+1A v 1A\nLeft, add left, left'},
    'preference_trial_f': {'title': 'F', 'desc': '2B v 1A -> 2B v 2A\nLeft, add right, right'},
    'preference_trial_g': {'title': 'G', 'desc': '2B v 1A -> 2B+1A v 1A\nRight, add left, left'},
    'preference_trial_h': {'title': 'H', 'desc': '2B v 1A -> 2B+1A v 1A\nRight, add left, right'},
    'preference_trial_i': {'title': 'I', 'desc': '2B v 1A -> 2B v 1A\nRight, nothing, right'},
    'preference_trial_j': {'title': 'J', 'desc': '2B v 2A -> 2B+1A v 2A\nLeft, add left, left'},
    'preference_trial_k': {'title': 'K', 'desc': '2B v 2A -> 2B v 3A\nLeft, add right, right'},
    'preference_trial_l': {'title': 'L', 'desc': '2B v 2A -> 2B v 2A\nLeft, nothing, left'},
    'preference_trial_m': {'title': 'M', 'desc': '2B v 2A -> 2B+1A v 2A\nRight, add left, left'},
    'preference_trial_n': {'title': 'N', 'desc': '2B v 2A -> 2B v 2A\nRight, nothing, right'},

    # Belief
    'belief_trial_a': {'title': 'A', 'desc': 'No Belief, True Sign, Listens, Gold'},
    'belief_trial_b': {'title': 'B', 'desc': 'No Belief, False Sign, Listens, Rocks'},
    'belief_trial_c': {'title': 'C', 'desc': 'True Belief, False Sign, Listens, Rocks'},
    'belief_trial_d': {'title': 'D', 'desc': 'False Belief, True Sign, Listens, Gold'},
    'belief_trial_e': {'title': 'E', 'desc': 'True Belief, True Sign, Listens, Gold'},
    'belief_trial_f': {'title': 'F', 'desc': 'False Belief, False Sign, Listens, Rocks'},
    'belief_trial_g': {'title': 'G', 'desc': 'True Belief, Nothing, Gold'},
    'belief_trial_h': {'title': 'H', 'desc': 'False Belief, Nothing, Rocks'},
    'belief_trial_i': {'title': 'I', 'desc': 'True Belief, False Sign, Ignores, Gold'},
    'belief_trial_j': {'title': 'J', 'desc': 'False Belief, True Sign, Ignores, Rocks'},
    'belief_trial_k': {'title': 'K', 'desc': 'Guess Correct, Nothing, Gold'},
    'belief_trial_l': {'title': 'L', 'desc': 'Guess Incorrect, Nothing, Rocks'},
    'belief_trial_m': {'title': 'M', 'desc': 'No Belief, True Sign, Ignores, Rocks'},
    'belief_trial_n': {'title': 'N', 'desc': 'No Belief, False Sign, Ignores, Gold'},
}

def load_physical_descriptions():
    try:
        # Assuming original path still valid for metadata
        df = pd.read_csv('data/physical_speaker/trials.csv')
        for _, row in df.iterrows():
            tid = row['trial_id']
            letter = row['trial_letter'] if 'trial_letter' in df.columns else tid.replace('trial_', '').upper()
            TRIAL_DEFINITIONS[f"physical_{tid}"] = {'title': letter, 'desc': ''}
    except: pass

def load_predictions(csv_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """Load predictions grouped by domain."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Predictions file not found: {csv_path}. Run model_results.py first.")
        
    data_by_domain = {'physical': [], 'preference': [], 'belief': []}
    
    # Reload original datasets to attach 'trial_data' for visualization
    # This is inefficient but necessary since CSV loses nested structure
    phys_data = {t.get('trial_id'): t for t, _ in load_physical_data()}
    pref_data = {t.get('trial_id'): t for t, _ in load_preference_data()}
    bel_data = {t.get('trial_id'): t for t, _ in load_belief_data()}
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = row['domain']
            tid = row['trial_id']
            
            # Reconstruct distributions
            def get_dist(suffix):
                return {v: float(row.get(f'pred_{v}_{suffix}', 0.0)) for v in VERBS}
                
            entry = {
                'trial_id': tid,
                'human': {v: float(row.get(f'human_{v}', 0.0)) for v in VERBS},
                'full': get_dist('full'),
                'nopref': get_dist('nopref'),
                'nocausal': get_dist('nocausal'),
                'sem': get_dist('sem'),
            }
            
            # Attach trial data
            if domain == 'physical':
                entry['trial_data'] = phys_data.get(tid)
            elif domain == 'preference':
                entry['trial_data'] = pref_data.get(tid)
            elif domain == 'belief':
                entry['trial_data'] = bel_data.get(tid)
                
            if domain in data_by_domain:
                data_by_domain[domain].append(entry)
                
    return data_by_domain

# Model Styling Configuration
MODEL_STYLES = {
    'human': {'label': 'Human', 'color': colors.ORANGE},
    'full': {'label': 'Full Model', 'color': colors.BLUE},
    'nopref': {'label': 'No Preference', 'color': colors.PINK},
    'nocausal': {'label': 'No Causal', 'color': colors.RED},
    'sem': {'label': 'Semantics Only', 'color': colors.SKY_BLUE}
}

def plot_domain(domain_name: str, results: List[Dict[str, Any]], 
                model_keys: List[str] = None,
                visualize_func: Optional[Callable] = None,
                suffix: str = "comparison"):
    """Generates a grid plot with bars for specified models."""
    if not results:
        print(f"No results for {domain_name}")
        return

    # Default to all models if not specified
    if model_keys is None:
        model_keys = ['human', 'full', 'nopref', 'nocausal', 'sem']

    n_trials = len(results)
    cols = 5
    
    # Calculate rows
    if visualize_func:
        chunk_rows = (n_trials + cols - 1) // cols
        rows = chunk_rows * 2 
    else:
        rows = (n_trials + cols - 1) // cols
    
    unit_height = 6.0 if visualize_func else 3.5
    fig_height = unit_height * (rows // 2 if visualize_func else rows)
    
    fig, axes = plt.subplots(rows, cols, figsize=(3.5 * cols, fig_height), layout='constrained')
    
    if rows == 1: axes = np.array(axes).flatten()
    axes_flat = axes.flatten()
    
    # Bar settings
    n_models = len(model_keys)
    width = 0.8 / n_models
    x = np.arange(len(VERBS))
    offsets = np.linspace(-width * (n_models - 1) / 2, width * (n_models - 1) / 2, n_models)
    
    for i in range(n_trials):
        res = results[i]
        tid = res['trial_id']
        def_key = f"{domain_name}_{tid}"
        trial_def = TRIAL_DEFINITIONS.get(def_key, {'title': tid.upper().replace('TRIAL_', ''), 'desc': ''})
        
        # Prepare Title
        title_str = trial_def['title']
        if trial_def['desc']:
            wrapped_desc = fill(trial_def['desc'], width=50)
            title_str += f"\n\n{wrapped_desc}"

        # Axes logic
        col_idx = i % cols
        chunk_idx = i // cols
        
        if visualize_func:
            ax_vis = axes[chunk_idx * 2, col_idx]
            ax_bar = axes[chunk_idx * 2 + 1, col_idx]
            
            # Visual
            if res['trial_data']:
                visualize_func(res['trial_data'], ax_vis)
            ax_vis.set_title(title_str, fontsize=11, loc='center')
            target_ax = ax_bar
        else:
            ax_idx = i 
            target_ax = axes_flat[ax_idx]
            target_ax.set_title(title_str, fontsize=11, loc='center')

        # Plot Bars
        for m_idx, m_key in enumerate(model_keys):
            style = MODEL_STYLES[m_key]
            vals = [res[m_key].get(v, 0.0) for v in VERBS]
            target_ax.bar(x + offsets[m_idx], vals, width, 
                         label=style['label'] if i == 0 else "", 
                         color=style['color'])
        
        target_ax.set_ylim(0, 1.0)
        target_ax.set_xticks(x)
        # Only show x labels on bottommost plots if dense? For now show all.
        target_ax.set_xticklabels(['C', 'E', 'A', 'M'], rotation=0, fontsize=8)
        target_ax.tick_params(axis='y', labelsize=8)
        target_ax.spines['top'].set_visible(False)
        target_ax.spines['right'].set_visible(False)
                
    # Hide unused axes
    total_slots = rows * cols 
    for j in range(total_slots):
        r = j // cols
        c = j % cols
        if visualize_func:
            trial_idx = (r // 2) * cols + c
        else:
            trial_idx = j
            
        if trial_idx >= n_trials:
             if rows > 1: axes[r, c].axis('off')
             else: axes[j].axis('off')

    # Legend
    leg_ax = axes[1, 0] if visualize_func else axes_flat[0]
    
    # Custom legend elements
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=MODEL_STYLES[k]['color'], label=MODEL_STYLES[k]['label']) for k in model_keys]
    
    fig.get_layout_engine().set(rect=(0, 0, 1, 0.88)) # Reserve top space
    fig.legend(handles=legend_elements, loc='lower center', 
               bbox_to_anchor=(0.5, 0.89), ncol=len(model_keys), frameon=False, fontsize=10)

    fig.suptitle(f"{domain_name.capitalize()} Experiment", fontsize=16, fontweight='bold', y=0.98)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    save_path = os.path.join(OUTPUT_DIR, f"{domain_name}_{suffix}.png")
    plt.savefig(save_path, dpi=150)
    print(f"Saved {save_path}")

def main():
    load_physical_descriptions()
    
    print("Loading predictions...")
    all_results = load_predictions(PREDICTIONS_CSV)
    
    domains = [
        ('physical', draw_physical_scenario),
        ('preference', None),
        ('belief', None)
    ]
    
    for dom, vis_func in domains:
        print(f"Plotting {dom}...")
        
        # 1. Full Comparison (5 bars)
        plot_domain(dom, all_results[dom], 
                    model_keys=['human', 'full', 'nopref', 'nocausal', 'sem'],
                    visualize_func=vis_func,
                    suffix="comparison")
                    
        # 2. Simple Comparison (Human vs Full)
        plot_domain(dom, all_results[dom], 
                    model_keys=['human', 'full'],
                    visualize_func=vis_func,
                    suffix="simple")
    
    print("Done.")

if __name__ == "__main__":
    main()
