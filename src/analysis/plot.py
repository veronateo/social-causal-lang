import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
import seaborn as sns
import argparse
import json

from scipy.stats import pearsonr
from matplotlib.gridspec import GridSpec
from typing import Union, List, Dict, Any, Optional
from src.model.config import TRIAL_DATA_FILE, SEED, DEFAULT_DATA_DIR_SPEAKER
# Note: create_rsa_model import removed - not needed for human-only plotting
# from src.model.rsa import create_rsa_model
from src.utils import load_trial_data, load_human_data, get_trial_response_counts, load_fitted_params, compute_nll_loss
from src.analysis.speaker import normalize_response_counts, bootstrap_human_data, prepare_model_dataframe, get_error_bars
from src.analysis.plotting_utils import *


def plot_responses_by_scenario(data: Union[pd.DataFrame, List[Dict[str, Any]]],
                               trial_definitions: Dict[str, Any],
                               title: str,
                               save_path: Optional[str] = None,
                               normalize_human_data: bool = True,
                               ylabel: Optional[str] = None,
                               error_bars: Optional[pd.DataFrame] = None):
    """Create grid visualization of trial responses."""
    is_model_data = isinstance(data, list)

    if is_model_data:
        df = pd.DataFrame([r['verb_distribution'] for r in data], index=[r['trial_id'] for r in data])
    else:
        df = data.copy()
        if normalize_human_data and df.max().max() > 1:
            df = normalize_response_counts(df)

    trial_ids = sorted([tid for tid in df.index if tid.startswith('trial_')])
    verbs = ['caused', 'enabled', 'allowed', 'made_no_difference']
    
    n_trials = len(trial_ids)
    
    # Determine grid layout
    if n_trials == 14:
        n_cols = 7
        n_rows = 2
    elif n_trials <= 5:
        n_cols = n_trials
        n_rows = 1
    elif n_trials <= 10:
        n_cols = 5
        n_rows = 2
    else:
        n_cols = 5
        n_rows = (n_trials + 4) // 5

    # Calculate figure size width based on columns
    fig_width = 14 * (n_cols / 4)
    fig_height = 7.5 if n_rows > 1 else 4.0
    
    fig = plt.figure(figsize=(fig_width, fig_height))
    
    # Grid spec with space for scenarios and bars
    
    if n_rows == 2 and n_cols == 7:
        # Special 2x7 layout
        height_ratios = [0.5, 1.0, 0.5, 0.5, 1.0, 0.01]
        row_map = [0, 1, 3, 4] # logical rows 0,1 map to grid rows 0 (scen), 1 (bar); logical rows 2,3 map to 3 (scen), 4 (bar)
        gs = GridSpec(6, n_cols, figure=fig, height_ratios=height_ratios, wspace=0.3, hspace=0.0)
    elif n_rows == 2:
        height_ratios = [1.3, 2.0, 0.35, 1.3, 2.0, 0.01]
        row_map = [0, 1, 3, 4]
        gs = GridSpec(6, n_cols, figure=fig, height_ratios=height_ratios, wspace=0.3, hspace=0.0)
    else:
        # Generic fallback
        gs = GridSpec(n_rows * 3, n_cols, figure=fig)
        row_map = []
        for r in range(n_rows):
            row_map.extend([r*3, r*3+1])

    plt.subplots_adjust(bottom=0.1) 
    
    axes = np.full((n_rows * 2, n_cols), None, dtype=object)
    
    # Initialize axes
    current_grid_row_idx = 0
    for r in range(n_rows):
        # Scenario row
        grid_r_scen = row_map[r*2]
        # Bar row
        grid_r_bar = row_map[r*2 + 1]
        
        for c in range(n_cols):
            axes[r*2, c] = fig.add_subplot(gs[grid_r_scen, c])
            axes[r*2 + 1, c] = fig.add_subplot(gs[grid_r_bar, c])

    fig.suptitle(title, fontsize=16, y=0.98)

    for idx, trial_id in enumerate(trial_ids):
        col = idx % n_cols
        row = idx // n_cols
        
        # Base row index in our axes array (2 indices per logical row)
        base_row = row * 2

        # Scenario visualization
        scenario_ax = axes[base_row, col]
        trial_info = trial_definitions.get(trial_id, {})
        
        if trial_info:
            if 'rock_initial' in trial_info or 'farmer_initial_direction_goal' in trial_info:
                draw_scenario(trial_info, scenario_ax)
            elif 'label' in trial_info:
                draw_text_scenario(scenario_ax, trial_info['label'])
        else:
            scenario_ax.axis('off')
            
        scenario_ax.set_title(trial_id.replace('trial_', '').upper(), fontsize=12, fontweight='normal')

        # Bar chart directly below scenario
        bar_ax = axes[base_row + 1, col]
        trial_data = df.loc[trial_id].reindex(verbs, fill_value=0)
        colors = [COLORS[verb] for verb in verbs]

        # Get error bars
        yerr_lower, yerr_upper = get_error_bars(trial_id, verbs, trial_data.values, error_bars)

        # Plot bars with optional error bars
        if yerr_lower is not None and yerr_upper is not None:
            bar_ax.bar(range(len(verbs)), trial_data.values, color=colors, edgecolor=colors, linewidth=0,
                      yerr=[yerr_lower, yerr_upper], error_kw={'linewidth': 1, 'ecolor': 'black', 'capsize': 2})
        else:
            bar_ax.bar(range(len(verbs)), trial_data.values, color=colors, edgecolor=colors, linewidth=0)

        bar_ax.set_xticks([])
        bar_ax.grid(False)

        is_normalized = is_model_data or (normalize_human_data and df.max().max() <= 1)
        if is_normalized:
            bar_ax.set_ylim(0, 1.0)
            bar_ax.set_yticks([0, 0.5, 1.0])
        else:
            bar_ax.set_ylim(0, 20)

        # Only show y-label on leftmost plots
        if col == 0:
            if ylabel:
                bar_ax.set_ylabel(ylabel, fontsize=12)
            else:
                bar_ax.set_ylabel('Probability' if is_model_data else 'Proportion', fontsize=12)
        else:
            bar_ax.set_yticklabels([])

        # Clip spines at data limits
        bar_ax.spines['left'].set_bounds(0, 1.0 if is_normalized else 20)
        bar_ax.spines['right'].set_visible(False)
        bar_ax.spines['top'].set_visible(False)

    legend_elements = [plt.Rectangle((0,0),1,1, color=COLORS[verb],
                                    label=VERB_LABELS[verb]) for verb in verbs]
    fig.legend(handles=legend_elements, loc='lower center', ncol=4,
              bbox_to_anchor=(0.5, -0.02), frameon=False, columnspacing=4.0,
              fontsize=14, handlelength=1.0, handleheight=1.0)

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

def plot_human_vs_model_comparison(human_data: pd.DataFrame,
                                   model_predictions: List[Dict[str, Any]],
                                   title: str,
                                   save_path: Optional[str] = None,
                                   error_bars: Optional[pd.DataFrame] = None,
                                   s0_predictions: Optional[List[Dict[str, Any]]] = None,
                                   third_model_label: str = 'No Pragmatics model'):
    """Create 2x5 comparison plot of human vs model predictions with grouped bars."""

    # Prepare data
    model_df = prepare_model_dataframe(model_predictions)
    s0_df = prepare_model_dataframe(s0_predictions) if s0_predictions else None
    human_df = normalize_response_counts(human_data)

    # Get trial IDs in order
    trial_ids = sorted([tid for tid in human_df.index if tid.startswith('trial_')])

    # Create 2x5 subplot grid
    fig, axes = plt.subplots(2, 5, figsize=(14, 5),
                            gridspec_kw={'wspace': 0.3, 'hspace': 0.4})
    # fig.suptitle(title, fontsize=16, y=0.98)

    verbs = ['caused', 'enabled', 'allowed', 'made_no_difference']

    for idx, trial_id in enumerate(trial_ids):
        row = idx // 5
        col = idx % 5
        ax = axes[row, col]

        # Get data for this trial
        human_vals = human_df.loc[trial_id].reindex(verbs, fill_value=0).values
        model_vals = model_df.loc[trial_id].reindex(verbs, fill_value=0).values
        s0_vals = s0_df.loc[trial_id].reindex(verbs, fill_value=0).values if s0_df is not None else None

        # Get error bars
        yerr_lower, yerr_upper = get_error_bars(trial_id, verbs, human_vals, error_bars)

        # Create grouped bar positions
        x = np.arange(len(verbs))
        num_bars = 3 if s0_vals is not None else 2
        width = 0.25 if num_bars == 3 else 0.32
        gap = 0.01

        # Plot human bars (solid)
        colors = [COLORS[verb] for verb in verbs]
        x_offset = -width - gap if num_bars == 3 else -width/2 - gap/2
        if yerr_lower is not None and yerr_upper is not None:
            ax.bar(x + x_offset, human_vals, width, color=colors,
                  yerr=[yerr_lower, yerr_upper],
                  error_kw={'linewidth': 1, 'ecolor': 'black', 'capsize': 2},
                  label='Human',
                  edgecolor=colors, linewidth=1.5)
        else:
            ax.bar(x + x_offset, human_vals, width, color=colors, label='Human')

        # Plot S1 bars individually (outlined with hatching and light transparent fill)
        x_offset = 0 if num_bars == 3 else width/2 + gap/2
        for i, (verb, val) in enumerate(zip(verbs, model_vals)):
            color = COLORS[verb]
            color_alpha = mcolors.to_rgba(color, alpha=0.2)
            label = 'Full model' if i == 0 else None
            ax.bar(x[i] + x_offset, val, width, facecolor=color_alpha, edgecolor=color,
                   hatch='///', linewidth=1.5, label=label)

        # Plot S0 bars individually (outlined only, no fill, no hatching)
        if s0_vals is not None:
            for i, (verb, val) in enumerate(zip(verbs, s0_vals)):
                color = COLORS[verb]
                label = 'No Pragmatics model' if i == 0 else None
                ax.bar(x[i] + width + gap, val, width, facecolor='none', edgecolor=color,
                       linewidth=1.5, label=label)

        # Formatting
        ax.set_ylim(0, 1.0)
        ax.set_yticks([0, 0.5, 1.0])
        ax.set_xticks([])
        ax.set_title(trial_id.replace('trial_', '').upper(), fontsize=12, fontweight='normal')

        # Only show y-label on leftmost plots
        if col == 0:
            ax.set_ylabel('Probability', fontsize=12)
        else:
            ax.set_yticklabels([])

        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_bounds(0, 1.0)
        ax.grid(False)

    # Create two-part legend
    # Part 1: Verb colors
    verb_legend_elements = [plt.Rectangle((0,0),1,1, color=COLORS[verb],
                                         label=VERB_LABELS[verb]) for verb in verbs]
    # Part 2: Human vs Model
    if s0_predictions is not None:
        condition_legend_elements = [
            plt.Rectangle((0,0),1,1, facecolor='lightgray', edgecolor='lightgray', linewidth=1.5, label='Human'),
            plt.Rectangle((0,0),1,1, facecolor=mcolors.to_rgba('lightgray', alpha=0.2),
                         edgecolor='lightgray', hatch='///', linewidth=1.5, label='Full model'),
            plt.Rectangle((0,0),1,1, facecolor='none', edgecolor='lightgray', linewidth=1.5, label=third_model_label)
        ]
    else:
        condition_legend_elements = [
            plt.Rectangle((0,0),1,1, facecolor='lightgray', edgecolor='lightgray', linewidth=1.5, label='Human'),
            plt.Rectangle((0,0),1,1, facecolor=mcolors.to_rgba('lightgray', alpha=0.2),
                         edgecolor='lightgray', hatch='///', linewidth=1.5, label='Full model')
        ]

    # Place legends vertically aligned on the right
    legend1 = fig.legend(handles=verb_legend_elements, loc='upper left', ncol=1,
                        bbox_to_anchor=(0.93, 0.78), frameon=False,
                        fontsize=11, title='Verb (color)', title_fontsize=11, alignment='left', handlelength=1.0, handleheight=1.0)
    legend2 = fig.legend(handles=condition_legend_elements, loc='upper left', ncol=1,
                        bbox_to_anchor=(0.93, 0.42), frameon=False,
                        fontsize=11, title='Data (marker)', title_fontsize=11, alignment='left', handlelength=1.0, handleheight=1.0)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    return fig

def create_listener_heatmap(df: pd.DataFrame, model_level: str, output_path: str):
    """Create heatmap showing P(trial|verb) for listener"""
    heatmap_data = df.pivot(index='verb', columns='trial', values='probability')
    trial_order = sorted(heatmap_data.columns, key=lambda x: x.replace('trial_', ''))
    heatmap_data = heatmap_data[trial_order]

    verb_order = ['caused', 'allowed', 'enabled', 'made_no_difference']
    heatmap_data = heatmap_data.reindex(verb_order)

    fig, ax = plt.subplots(figsize=(8, 3))
    cbar_ax = sns.heatmap(heatmap_data, annot=True, fmt='.3f', cmap='Greens',
                cbar_kws={'label': 'Probability', 'ticks': []}, ax=ax, linewidths=2.0, square=False,
                annot_kws={'fontsize': 8})

    # Rotate colorbar label 180 degrees
    cbar = cbar_ax.collections[0].colorbar
    # cbar.set_label('Probability', rotation=270, labelpad=15)

    listener_type = "Pragmatic Listener" if model_level == "L1" else "Literal Listener"
    ax.set_title(f'RSA {model_level} ({listener_type}) Inference', fontsize=12, pad=20)
    ax.set_xlabel('Trial', fontsize=10)
    ax.set_ylabel('Observed Verb', fontsize=10)
    ax.set_xticklabels([t.replace('trial_', '').upper() for t in trial_order], rotation=0, fontsize=9)
    ax.set_yticklabels([VERB_LABELS[v] for v in heatmap_data.index], rotation=0, fontsize=9)
    ax.tick_params(left=False, bottom=False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    return fig

def create_rsa_speaker_plots(output_dir: str, model_level: str = 'S1', fitted_params: dict = None,
                            human_summary: pd.DataFrame = None, human_bootstrap: pd.DataFrame = None, save_debug: bool = False):
    """Create plots for RSA speaker model results"""
    print(f"Creating RSA {model_level} speaker plots...")

    trials_data = load_trial_data(f'{DEFAULT_DATA_DIR_SPEAKER}/{TRIAL_DATA_FILE}')
    trial_definitions = {trial['trial_id']: trial for trial in trials_data}

    # Load human data if not provided
    if human_summary is None:
        human_data = load_human_data(DEFAULT_DATA_DIR_SPEAKER)
        human_summary = get_trial_response_counts(human_data)
        if human_bootstrap is None:
            print(f"  Bootstrapping human data (n=1000)...")
            human_bootstrap = bootstrap_human_data(human_data, n_bootstrap=1000, seed=42)

    if fitted_params is None:
        print("Warning: No fitted parameters provided!")
        fitted_params = {}

    rsa_model = create_rsa_model(fitted_params, model_level=model_level)

    predictions = []
    for trial in trials_data:
        if model_level == 'S1':
            result = rsa_model.predict_verb_distribution(trial, trials_data, save_debug=save_debug, debug_model_label=model_level.lower())
        else:
            result = rsa_model.predict_verb_distribution(trial, save_debug=save_debug, debug_model_label=model_level.lower())
        predictions.append({'trial_id': trial['trial_id'], 'verb_distribution': result['verb_distribution']})

    os.makedirs(output_dir, exist_ok=True)

    plot_responses_by_scenario(human_summary, trial_definitions, 'Human Responses',
                              save_path=f'{output_dir}/speaker_humans.png', normalize_human_data=True,
                              error_bars=human_bootstrap)

    speaker_type = "Pragmatic Speaker" if model_level == "S1" else "Literal Speaker"
    plot_responses_by_scenario(predictions, trial_definitions,
                              f'RSA {model_level} ({speaker_type}) Predictions',
                              save_path=f'{output_dir}/speaker_model_{model_level.lower()}.png')
    return predictions

def create_rsa_listener_plots(output_dir: str, s0_params: dict = None, s1_params: dict = None):
    """Create plots for RSA listener inference"""
    print(f"Creating RSA listener inference plots...")

    trials_data = load_trial_data(f'{DEFAULT_DATA_DIR_SPEAKER}/{TRIAL_DATA_FILE}')
    os.makedirs(output_dir, exist_ok=True)

    def get_listener_data(listener, level_name):
        verbs = ['caused', 'enabled', 'allowed', 'made_no_difference']
        trial_ids = [t['trial_id'] for t in trials_data]
        inference_data = []

        for verb in verbs:
            result = listener.infer_trial_distribution(verb, trials_data)
            trial_probs = result['trial_probabilities']
            for i, trial_id in enumerate(trial_ids):
                inference_data.append({
                    'verb': verb,
                    'trial': trial_id,
                    'probability': trial_probs.get(i, 0.0)
                })
        return pd.DataFrame(inference_data)

    # L0 reasons about S0 (use s0_params)
    s0_model = create_rsa_model(s0_params or {}, model_level='S0')
    l0_data = get_listener_data(s0_model.L0, 'L0')

    # L1 reasons about S1 (use s1_params)
    s1_model = create_rsa_model(s1_params or {}, model_level='S1')
    l1_data = get_listener_data(s1_model.L1, 'L1')

    create_listener_heatmap(l0_data, 'L0', f'{output_dir}/listener_model_l0.png')
    create_listener_heatmap(l1_data, 'L1', f'{output_dir}/listener_model_l1.png')

    return l0_data, l1_data

def _get_listener_data(listener, trials_data):
    """Helper to get listener inference data"""
    verbs = ['caused', 'enabled', 'allowed', 'made_no_difference']
    trial_ids = [t['trial_id'] for t in trials_data]
    inference_data = []

    for verb in verbs:
        result = listener.infer_trial_distribution(verb, trials_data)
        trial_probs = result['trial_probabilities']
        for i, trial_id in enumerate(trial_ids):
            inference_data.append({
                'verb': verb,
                'trial': trial_id,
                'probability': trial_probs.get(i, 0.0)
            })
    return pd.DataFrame(inference_data)


def create_all_plots(s0_params: Dict[str, float], s1_params: Dict[str, float],
                     output_dir: str, data_dir: str, model_variants: Dict[str, Dict] = None, save_debug: bool = False):
    """Create all RSA plots with fitted models."""
    speaker_dir = os.path.join(output_dir, "speaker")
    listener_dir = os.path.join(output_dir, "listener")
    os.makedirs(speaker_dir, exist_ok=True)
    os.makedirs(listener_dir, exist_ok=True)

    print("\nGenerating plots...")

    human_data = load_human_data(data_dir)
    human_summary = get_trial_response_counts(human_data)
    human_bootstrap = bootstrap_human_data(human_data, n_bootstrap=1000, seed=SEED)
    trials_data = load_trial_data(f'{data_dir}/{TRIAL_DATA_FILE}')
    trial_definitions = {trial['trial_id']: trial for trial in trials_data}

    s0_predictions = create_rsa_speaker_plots(speaker_dir, model_level='S0', fitted_params=s0_params,
                            human_summary=human_summary, human_bootstrap=human_bootstrap, save_debug=save_debug)
    s1_predictions = create_rsa_speaker_plots(speaker_dir, model_level='S1', fitted_params=s1_params,
                            human_summary=human_summary, human_bootstrap=human_bootstrap, save_debug=save_debug)

    plot_human_vs_model_comparison(human_summary, s1_predictions, 'Human vs Model Comparison',
        save_path=f'{speaker_dir}/speaker_comparison.png',
        error_bars=human_bootstrap,
        s0_predictions=s0_predictions)

    create_rsa_listener_plots(listener_dir, s0_params=s0_params, s1_params=s1_params)

    # Create plots for any model variants
    if model_variants:
        for variant_name, variant_config in model_variants.items():
            # Speaker plots go in speaker_dir
            variant_model = create_rsa_model(variant_config['params'], model_level='S1',
                                            uniform_preference=variant_config.get('uniform_preference', False))
            variant_predictions = []
            for trial in trials_data:
                # Pass save_debug and model label for variants
                result = variant_model.predict_verb_distribution(trial, trials_data,
                                                                save_debug=save_debug,
                                                                debug_model_label=variant_name)
                variant_predictions.append({'trial_id': trial['trial_id'], 'verb_distribution': result['verb_distribution']})

            plot_responses_by_scenario(variant_predictions, trial_definitions,
                                      f'RSA S1 ({variant_config["label"]}) Predictions',
                                      save_path=f'{speaker_dir}/speaker_model_s1_{variant_name}.png')

            plot_human_vs_model_comparison(human_summary, s1_predictions,
                                          f'Human vs Full vs {variant_config["label"]} Comparison',
                                          save_path=f'{speaker_dir}/speaker_comparison_{variant_name}.png',
                                          error_bars=human_bootstrap,
                                          s0_predictions=variant_predictions,
                                          third_model_label=f'{variant_config["label"]} model')

            # Listener plots go in listener_dir
            l1_data = _get_listener_data(variant_model.L1, trials_data)
            create_listener_heatmap(l1_data, 'L1', f'{listener_dir}/listener_model_l1_{variant_name}.png')


def plot_ablation_comparison(results: List[Dict[str, Any]], save_path: str,
                            models_to_plot: Optional[List[str]] = None,
                            bar_color: str = '#f8b6ba',
                            show_title: bool = True):
    """Create bar plot comparing ablation models by validation NLL."""
    # Filter results if specific models requested
    if models_to_plot is not None:
        results = [r for r in results if r['ablation_name'] in models_to_plot]

    fig, ax = plt.subplots(figsize=(6, 4))

    names = [r['ablation_name'] for r in results]
    mean_nlls = [r['mean_val_nll'] for r in results]
    std_nlls = [r['std_val_nll'] for r in results]

    display_names = [ABLATION_LABELS.get(name, name) for name in names]

    x = np.arange(len(names))
    ax.bar(x, mean_nlls, yerr=std_nlls, color=bar_color,
           error_kw={'linewidth': 1, 'ecolor': 'black', 'capsize': 2})

    if show_title:
        ax.set_title('Validation Loss Across Models', fontsize=14, pad=15)
    ax.set_ylabel('Average Validation Loss', fontsize=12, color='black')
    ax.set_xlabel('Model', fontsize=12, color='black', labelpad=10)
    ax.set_xticks(x)
    if len(results) > 3:
        ax.set_xticklabels(display_names, rotation=45, ha='center', fontsize=11)
    else: ax.set_xticklabels(display_names, rotation=0, ha='center', fontsize=11)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.grid(False)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved ablation comparison plot to {save_path}")


# TODO: move to utils?
def _compute_model_trial_nlls(result: Dict[str, Any], trials_data: List[Dict[str, Any]],
                              human_summary: pd.DataFrame) -> List[float]:
    """Compute per-trial NLL for a single model"""
    ablation_name = result['ablation_name']
    model_level = result.get('model_level', 'S1')
    fitted_params = result['fold_results'][0]['fitted_params']
    uniform_preference = 'no_preference' in ablation_name

    rsa_model = create_rsa_model(fitted_params, model_level=model_level,
                                 uniform_preference=uniform_preference)

    trial_nlls = []
    for trial in trials_data:
        trial_id = trial['trial_id']
        if not trial_id.startswith('trial_'):
            continue

        if model_level == 'S1':
            pred = rsa_model.predict_verb_distribution(trial, trials_data)
        else:
            pred = rsa_model.predict_verb_distribution(trial)

        if trial_id in human_summary.index:
            h_dist = human_summary.loc[trial_id] / human_summary.loc[trial_id].sum()
            nll = compute_nll_loss(h_dist, pred['verb_distribution'])
            trial_nlls.append(nll)
        else:
            trial_nlls.append(np.nan)

    return trial_nlls


def plot_ablation_heatmap(results: List[Dict[str, Any]],
                          trials_data: List[Dict[str, Any]],
                          human_data: pd.DataFrame,
                          save_path: str):
    """Create heatmap showing per-trial NLL for each ablation model"""
    human_summary = get_trial_response_counts(human_data)
    trial_ids = sorted([t['trial_id'] for t in trials_data if t['trial_id'].startswith('trial_')])

    heatmap_data = [_compute_model_trial_nlls(r, trials_data, human_summary) for r in results]
    model_names = [ABLATION_LABELS.get(r['ablation_name'], r['ablation_name']) for r in results]

    df = pd.DataFrame(heatmap_data, columns=trial_ids, index=model_names)

    fig, ax = plt.subplots(figsize=(10, 5))
    cbar_ax = sns.heatmap(df, annot=True, fmt='.3f', cmap='Reds',
                cbar_kws={'label': 'NLL (lower is better)', 'ticks': []},
                ax=ax, linewidths=2.0, linecolor='white', square=False,
                annot_kws={'fontsize': 8})

    # Rotate colorbar label 180 degrees
    cbar = cbar_ax.collections[0].colorbar
    # cbar.set_label('NLL (lower is better)', rotation=270, labelpad=15)

    ax.set_title('Per-Trial Validation NLL by Model', fontsize=14, pad=15)
    ax.set_xlabel('Trial', fontsize=12)
    ax.set_ylabel('Model', fontsize=12)
    ax.set_xticklabels([t.replace('trial_', '').upper() for t in trial_ids],
                       rotation=0, fontsize=10)
    ax.set_yticklabels(model_names, rotation=0, fontsize=10)
    ax.tick_params(left=False, bottom=False)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved ablation heatmap to {save_path}")


def plot_listener_scatter_comparison(detailed_df: pd.DataFrame, save_path: str):
    """Scatter plot comparing human vs model predictions for listener experiment"""
    fitted_df = detailed_df[detailed_df['model_variant'].str.contains('fitted')]

    model_names = ['full', 'no_pragmatics', 'empirical', 'no_preference']
    model_labels = {'full': 'Full', 'no_pragmatics': 'No Pragmatics', 'empirical': 'Empirical', 'no_preference': 'No Preference'}
    verbs = ['caused', 'enabled', 'allowed', 'made_no_difference']

    fig, axes = plt.subplots(1, 4, figsize=(12, 3))

    for idx, model_name in enumerate(model_names):
        ax = axes[idx]
        model_data = fitted_df[fitted_df['model_variant'] == f'{model_name}_fitted'].sort_values('trial_id')

        # Plot vertical CI bars for human data 
        yerr_lower = model_data['ci_lower'].values * 100
        yerr_upper = model_data['ci_upper'].values * 100
        for i in range(len(model_data)):
            ax.plot([model_data['model_prediction'].iloc[i], model_data['model_prediction'].iloc[i]],
                   [yerr_lower[i], yerr_upper[i]],
                   color='gray', alpha=0.3, linewidth=1.5, zorder=1)

        # Plot points colored by verb
        for verb in verbs:
            verb_data = model_data[model_data['verb'] == verb]
            ax.scatter(verb_data['model_prediction'], verb_data['human_mean'],
                      c=COLORS[verb], alpha=0.7, s=50, edgecolors='black',
                      linewidth=0.5, zorder=2, label=VERB_LABELS[verb])

        ax.plot([0, 100], [0, 100], 'k--', alpha=0.3, linewidth=1)

        # Compute and display statistics
        r, _ = pearsonr(model_data['human_mean'], model_data['model_prediction'])
        rmse = np.sqrt(np.mean((model_data['model_prediction'] - model_data['human_mean'])**2))
        ax.text(0.05, 0.95, f'RMSE = {rmse:.2f}\nr = {r:.2f}',
               transform=ax.transAxes, fontsize=9, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.7, edgecolor='none'))

        ax.set_xlim(-5, 105)
        ax.set_ylim(-5, 105)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_xlabel('Model Prediction', fontsize=11) 
        if idx == 0:
            ax.set_ylabel('Human Mean', fontsize=11) 
        ax.set_title(model_labels[model_name], fontsize=12)
        ax.set_aspect('equal')
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)

    # Add legend to right of plots
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='center left', bbox_to_anchor=(1, 0.5),
              frameon=False, fontsize=10, handlelength=1.0, handleheight=1.0)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def plot_listener_error_heatmap(detailed_df: pd.DataFrame, save_path: str):
    """Heatmap showing per-trial errors for each model"""
    fitted_df = detailed_df[detailed_df['model_variant'].str.contains('fitted')]

    model_names = ['full_fitted', 'no_pragmatics_fitted', 'empirical_fitted', 'no_preference_fitted']
    model_labels = {'full_fitted': 'Full', 'no_pragmatics_fitted': 'No Pragmatics',
                   'empirical_fitted': 'Empirical', 'no_preference_fitted': 'No Preference'}

    heatmap_data = []
    for model_name in model_names:
        model_data = fitted_df[fitted_df['model_variant'] == model_name].sort_values('trial_id')
        heatmap_data.append(model_data['abs_error'].values)

    trial_ids = sorted(fitted_df['trial_id'].unique())
    df = pd.DataFrame(heatmap_data, columns=trial_ids,
                     index=[model_labels[m] for m in model_names])

    fig, ax = plt.subplots(figsize=(10, 3.5))
    cbar_ax = sns.heatmap(df, annot=True, fmt='.1f', cmap='Reds',
               cbar_kws={'label': 'Absolute Error'},
               ax=ax, linewidths=2.0, linecolor='white')

    cbar = cbar_ax.collections[0].colorbar
    cbar.set_label('Absolute Error', rotation=270, labelpad=15)

    ax.set_title('Per-Trial Absolute Error by Model', fontsize=12, pad=10)
    ax.set_xlabel('Trial', fontsize=11)
    ax.set_ylabel('Model', fontsize=11)
    ax.set_xticklabels([f'{i+1}' for i in range(len(trial_ids))], fontsize=9)
    ax.tick_params(left=False, bottom=False)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def plot_listener_trial_preds(detailed_df: pd.DataFrame, save_path: str):
    """Grouped bar chart showing human means with CIs and model predictions per trial"""
    fitted_df = detailed_df[detailed_df['model_variant'].str.contains('fitted')]

    trial_ids = sorted(fitted_df['trial_id'].unique())
    human_data = fitted_df[fitted_df['model_variant'] == 'full_fitted'][['trial_id', 'human_mean', 'ci_lower', 'ci_upper']].drop_duplicates()
    human_data = human_data.sort_values('trial_id')

    fig, ax = plt.subplots(figsize=(16, 4))

    model_names = ['full_fitted', 'no_pragmatics_fitted', 'empirical_fitted', 'no_preference_fitted']
    model_labels = {'full_fitted': 'Full', 'no_pragmatics_fitted': 'No Pragmatics',
                   'empirical_fitted': 'Empirical', 'no_preference_fitted': 'No Preference'}
    colors = {'human': '#f8b6ba', 'full_fitted': '#a84222',
              'no_pragmatics_fitted': '#f5ecc2', 'empirical_fitted': '#7ba3cc', 'no_preference_fitted': '#837e31'}

    x = np.arange(len(trial_ids))
    width = 0.13

    # Human bars with error bars
    yerr_lower = human_data['human_mean'] - human_data['ci_lower'] * 100
    yerr_upper = human_data['ci_upper'] * 100 - human_data['human_mean']
    ax.bar(x - 2*width, human_data['human_mean'], width,
           label='Human', color=colors['human'],
           yerr=[yerr_lower, yerr_upper],
           error_kw={'linewidth': 1, 'ecolor': 'black', 'capsize': 2})

    # Model bars
    for i, model_name in enumerate(model_names):
        model_data = fitted_df[fitted_df['model_variant'] == model_name].sort_values('trial_id')
        offset = (-1 + i) * width
        ax.bar(x + offset, model_data['model_prediction'], width,
               label=model_labels[model_name], color=colors[model_name])

    ax.set_xlabel('Trial', fontsize=11)
    ax.set_ylabel('Response', fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels([f'{i+1}' for i in range(len(trial_ids))], fontsize=9)
    ax.legend(fontsize=10, loc='center left', bbox_to_anchor=(1, 0.5), frameon=False, handlelength=1.0, handleheight=1.0)
    # ax.grid(True, alpha=0.2, axis='y')
    ax.set_xlim(-0.8, len(trial_ids) - 0.2)
    ax.set_ylim(0, 105)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def plot_human_data(data_dir: str, output_dir: str, experiment: str):
    """Plot human data only"""
    # ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading data from {data_dir}...")
    human_data = load_human_data(data_dir)
    print(f"Loaded {len(human_data)} trials from {human_data['participant_id'].nunique()} participants.")
    
    human_summary = get_trial_response_counts(human_data)
    print(f"Trial IDs found: {sorted(human_summary.index.tolist())}")
    
    print("Bootstrapping error bars...")
    human_bootstrap = bootstrap_human_data(human_data, n_bootstrap=1000, seed=42)
    
    if experiment == 'belief':
        # Trial definitions for belief experiment
        trial_definitions = {
            'trial_a': {'label': 'No belief, true sign, listens, gold'},
            'trial_b': {'label': 'No belief, false sign, listens, rocks'},
            'trial_c': {'label': 'True belief, false sign, listens, rocks'},
            'trial_d': {'label': 'False belief, true sign, listens, gold'},
            'trial_e': {'label': 'True belief, true sign, listens, gold'},
            'trial_f': {'label': 'False belief, false sign, listens, rocks'},
            'trial_g': {'label': 'True belief, nothing, gold'},
            'trial_h': {'label': 'False belief, nothing, rocks'},
            'trial_i': {'label': 'True belief, false sign, ignores, gold'},
            'trial_j': {'label': 'False belief, true sign, ignores, rocks'},
            'trial_k': {'label': 'No belief, nothing, true guess, gold'},
            'trial_l': {'label': 'No belief, nothing, false guess, rocks'},
            'trial_m': {'label': 'No belief, true sign, ignores, rocks'},
            'trial_n': {'label': 'No belief, false sign, ignores, gold'}
        }
        
        output_path = os.path.join(output_dir, 'humans.png')
        print(f"Generating plot to {output_path}...")
        
        plot_responses_by_scenario(
            human_summary, 
            trial_definitions, 
            title='Belief Experiment: Human Responses', 
            save_path=output_path, 
            normalize_human_data=True,
            error_bars=human_bootstrap
        )
        print("Done!")

    elif args.experiment == 'preference':
        output_path = os.path.join(output_dir, 'humans.png')
        print(f"Generating plot to {output_path}...")
        trial_definitions = {
            'trial_a': {'label': '1B v 2A --> 1B v 3A\nLeft, add right, right'},
            'trial_b': {'label': '1B v 2A --> 1B v 2A\nLeft, nothing, left'},
            'trial_c': {'label': '1B v 2A --> 1B+1A v 2A\nRight, add left, left'},
            'trial_d': {'label': '1B v 2A --> 1B v 3A\nRight, add right, right'},
            'trial_e': {'label': '2B v 1A --> 2B+1A v 1A\nLeft, add left, left'},
            'trial_f': {'label': '2B v 1A --> 2B v 2A\nLeft, add right, right'},
            'trial_g': {'label': '2B v 1A --> 2B+1A v 1A\nRight, add left, left'},
            'trial_h': {'label': '2B v 1A --> 2B+1A v 1A\nRight, add left, right'},
            'trial_i': {'label': '2B v 1A --> 2B v 1A\nRight, nothing, right'},
            'trial_j': {'label': '2B v 2A --> 2B+1A v 2A\n Left, add left, left'},
            'trial_k': {'label': '2B v 2A --> 2B v 3A\nLeft, add right, right'},
            'trial_l': {'label': '2B v 2A --> 2B v 2A\nLeft, nothing, left'},
            'trial_m': {'label': '2B v 2A --> 2B+1A v 2A\nRight, add left, left'},
            'trial_n': {'label': '2B v 2A --> 2B v 2A\nRight, nothing, right'}
        }
        plot_responses_by_scenario(
            human_summary, 
            trial_definitions, 
            title='Preference Experiment: Human Responses', 
            save_path=output_path, 
            normalize_human_data=True,
            error_bars=human_bootstrap
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate plots from fitted results')
    parser.add_argument('--dir', type=str, required=False, help='Path to results directory (e.g., results/physical_rsa)')
    parser.add_argument('--data-dir', type=str, default='../data/physical_speaker/', help='Path to human data directory')
    parser.add_argument('--human', action='store_true', help='Plot human data only (no models)')
    parser.add_argument('--output-dir', type=str, help='Output directory for plot')
    parser.add_argument('--experiment', type=str, default='physical', choices=['physical', 'belief', 'preference'], help='Experiment type')
    args = parser.parse_args()

    if args.human:
        plot_human_data(args.data_dir, args.output_dir, args.experiment)
        exit(0)

    # Load S0 and S1 parameters
    speaker_dir = os.path.join(args.dir, 'speaker')
    s0_params = load_fitted_params(speaker_dir, model_level='S0')
    s1_params = load_fitted_params(speaker_dir, model_level='S1')

    # Load model variants
    variant_config = {
        'no_preference': {'label': 'No Preference', 'uniform_preference': True},
        'no_impact_sensitivity': {'label': 'No Impact Sensitivity', 'uniform_preference': False}
    }

    model_variants = {}
    for variant_name, config in variant_config.items():
        variant_files = [f for f in os.listdir(args.dir) if f'{variant_name}_fit' in f and f.endswith('.json')]
        if variant_files:
            variant_path = os.path.join(speaker_dir, sorted(variant_files)[-1])
            print(f"Loading {variant_name} parameters from: {variant_path}")
            with open(variant_path, 'r') as f:
                variant_results = json.load(f)
                if 'train_fit_result' in variant_results:
                    params = variant_results['train_fit_result']['best_params']
                elif 'best_params' in variant_results:
                    params = variant_results['best_params']
                else:
                    continue

                model_variants[variant_name] = {
                    'params': params,
                    'label': config['label'],
                    'uniform_preference': config['uniform_preference']
                }

    # Generate all plots
    create_all_plots(s0_params, s1_params, args.dir, args.data_dir, model_variants=model_variants)
