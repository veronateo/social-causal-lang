import json
import matplotlib.pyplot as plt
import numpy as np
import os
from collections import defaultdict

def plot_unique_distributions(json_path: str, output_path: str):
    """
    Groups states by their fitted model distribution and plots distinct distributions.
    """
    
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    # 1. Cluster by Distribution
    # Key: Tuple of rounded probabilities (caused, enabled, allowed, mnd)
    # Value: List of state descriptions
    clusters = defaultdict(list)
    cluster_probs = {}
    
    verbs = ['caused', 'enabled', 'allowed', 'made_no_difference']
    
    for state_key, entry in data.items():
        probs = entry['model_distribution_fitted']
        # Create a hashable key based on values
        prob_vals = tuple(probs.get(v, 0.0) for v in verbs)
        # Round to avoid float noise
        prob_key = tuple(round(p, 4) for p in prob_vals)
        
        control_val = entry['state'].get('control', 1.0)
        
        # Determine Domain for trials
        # entry['trials'] is a list of dicts {domain, trial_id}
        trials_formatted = []
        for t in entry['trials']:
            d_code = t['domain'][0:4] # phys, pref, beli
            trials_formatted.append(f"{d_code}:{t['trial_id']}")
        
        state_desc = (f"C={int(entry['state']['changed'])}, "
                      f"A={entry['state']['aligned']:.2f}, "
                      f"V={int(entry['state']['wizard_acted'])}, "
                      f"K={control_val}")
        
        clusters[prob_key].append({'state': state_desc, 'trials': trials_formatted})
        cluster_probs[prob_key] = prob_vals

    # 2. Sort Clusters by Dominant Verb
    # We want to group Caused, Enabled, Allowed, MND
    def get_sort_key(key):
        # key is (caused, enabled, allowed, mnd)
        # Find max index
        max_idx = np.argmax(key)
        # Return (Primary Verb Index, -Probability)
        return (max_idx, -key[max_idx])
        
    sorted_keys = sorted(clusters.keys(), key=get_sort_key)
    
    n_clusters = len(sorted_keys)
    
    # 3. Plot
    fig, axes = plt.subplots(n_clusters, 1, figsize=(12, 4 * n_clusters), constrained_layout=True)
    if n_clusters == 1:
        axes = [axes]
        
    x = np.arange(len(verbs))
    width = 0.6
    
    for i, key in enumerate(sorted_keys):
        ax = axes[i]
        probs = cluster_probs[key]
        entries = clusters[key]
        
        # Color based on dominant verb?
        dom_idx = np.argmax(probs)
        colors = ['salmon', 'lightgreen', 'skyblue', 'lightgray']
        bar_color = colors[dom_idx]
        
        # Bar Chart
        ax.bar(x, probs, width, color=bar_color, alpha=0.9, edgecolor='black')
        
        # Text Construction
        mapping_text = []
        all_trials_count = 0
        
        for e in entries:
            t_count = len(e['trials'])
            all_trials_count += t_count
            # Wrap trials if too many
            t_ids = ", ".join(e['trials'])
            if len(t_ids) > 60:
                 t_ids = t_ids[:57] + "..."
            mapping_text.append(f"• {e['state']}\n   [{t_ids}]")
            
        mapping_str = "\n".join(mapping_text)
        
        ax.set_title(f"Pattern {i+1}: Dominant = {verbs[dom_idx].upper()} (n={all_trials_count})", fontsize=12, fontweight='bold')
        
        # Text Box
        props = dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray')
        ax.text(1.02, 1.0, f"State Mappings:\n{mapping_str}", transform=ax.transAxes, fontsize=9,
                verticalalignment='top', bbox=props)
        
        ax.set_ylim(0, 1.05)
        ax.set_xticks(x)
        ax.set_xticklabels(verbs)
        ax.set_ylabel('Probability')
        ax.grid(axis='y', linestyle='--', alpha=0.5)

    plt.suptitle(f"Clustered Model Distributions ({n_clusters} Distinct Patterns)", fontsize=16, y=1.01)
    
    # Adjust layout to make room for the right-side text
    # constrained_layout handles typical stuff, but right text might be clipped.
    # We might need manual subplot adjustment if constrained_layout fails on right text.
    # But let's try.
    
    plt.savefig(output_path, bbox_inches='tight')
    print(f"Plot saved to {output_path}")

if __name__ == "__main__":
    plot_unique_distributions('data/unique_model_states.json', 'data/clustered_distributions_plot.png')
