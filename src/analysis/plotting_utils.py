import os
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, Tuple, List, Dict, Any
from PIL import Image


# Font configuration
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica']

# Color mappings
COLORS = {
    'caused': '#e74c3c',
    'enabled': '#f39c12',
    'allowed': '#3498db',
    'made_no_difference': '#95a5a6'
}

MODEL_COLORS = {
    'full': '#73B5FF',
    'no_causal': '#FFBE73',
    'no_preference': '#65BA8F',
    'no_pragmatics': '#DB7493',
}

VERB_LABELS = {
    'caused': 'Caused',
    'enabled': 'Enabled',
    'allowed': 'Allowed',
    'made_no_difference': 'Made No Difference'
}

ABLATION_LABELS = {
    'full_model': 'Full',
    'no_step_cost': 'No Step Cost',
    'no_impact_sensitivity': 'No Sigmoid Temp',
    'no_soft_and': 'No Soft And',
    'no_rationality_alpha': 'No Pragmatics',
    'no_preference': 'No Preference'
}


def load_image(image_name: str):
    """Load image from docs/images directory"""
    base_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "images")
    img_path = os.path.abspath(os.path.join(base_path, image_name))
    if os.path.exists(img_path):
        pil_img = Image.open(img_path).convert('RGBA')
        return np.array(pil_img) / 255.0
    return None


def draw_scenario(trial_info: Dict[str, Any], ax: plt.Axes):
    """Draw compact trial scenario visualization"""
    ax.clear()
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 2)
    ax.axis('off')

    img_size = 1.0
    y_pos = 1.0

    # Load images
    rock_img = load_image('rock.png')
    farmer_img = load_image('farmer.png')
    wizard_img = load_image('wizard.png')
    initial_goal = trial_info.get('farmer_initial_direction_goal', 'apple')
    initial_goal_img = load_image(f'{initial_goal}.png')
    final_outcome = trial_info.get('final_outcome', 'apple')
    outcome_img = load_image(f'{final_outcome}.png')

    # Initial state
    is_rock_present = trial_info.get('rock_initial', False)
    farmer_x = 1.7 if is_rock_present else 1.0

    if is_rock_present and rock_img is not None:
        ax.imshow(rock_img, extent=[0.5-img_size/2, 0.5+img_size/2, y_pos-img_size/2, y_pos+img_size/2])

    if farmer_img is not None:
        ax.imshow(farmer_img, extent=[farmer_x-img_size/2, farmer_x+img_size/2, y_pos-img_size/2, y_pos+img_size/2])

    arrow_x = farmer_x + 1.2
    ax.text(arrow_x, y_pos, '→', fontsize=14, ha='center', va='center', fontfamily='DejaVu Sans')

    goal_x = arrow_x + 1.2
    if initial_goal_img is not None:
        ax.imshow(initial_goal_img, extent=[goal_x-img_size/2, goal_x+img_size/2, y_pos-img_size/2, y_pos+img_size/2])
    ax.text(goal_x + 0.7, y_pos, ',', fontsize=12, ha='center', va='center')

    # Wizard action
    wizard_x = 5.5
    if wizard_img is not None:
        ax.imshow(wizard_img, extent=[wizard_x-img_size/2, wizard_x+img_size/2, y_pos-img_size/2, y_pos+img_size/2])

    wizard_action = trial_info.get('wizard_action', '')
    if wizard_action == 'place_rock' and rock_img is not None:
        ax.imshow(rock_img, extent=[wizard_x+1.0-img_size/2, wizard_x+1.0+img_size/2, y_pos-img_size/2, y_pos+img_size/2])
        ax.text(wizard_x + 1.7, y_pos, ',', fontsize=12, ha='center', va='center')
    elif wizard_action == 'remove_rock' and rock_img is not None:
        ax.imshow(rock_img, extent=[wizard_x+1.0-img_size/2, wizard_x+1.0+img_size/2, y_pos-img_size/2, y_pos+img_size/2], alpha=0.5)
        ax.text(wizard_x + 1.0, y_pos, 'X', fontsize=12, ha='center', va='center', color='red')
        ax.text(wizard_x + 1.7, y_pos, ',', fontsize=12, ha='center', va='center')
    else:
        ax.text(wizard_x + 1.3, y_pos, ',', fontsize=12, ha='center', va='center')

    # Final outcome
    outcome_farmer_x = 8.0
    if farmer_img is not None:
        ax.imshow(farmer_img, extent=[outcome_farmer_x-img_size/2, outcome_farmer_x+img_size/2, y_pos-img_size/2, y_pos+img_size/2])

    outcome_arrow_x = outcome_farmer_x + 1.2
    ax.text(outcome_arrow_x, y_pos, '→', fontsize=14, ha='center', va='center', fontfamily='DejaVu Sans')

    outcome_fruit_x = outcome_arrow_x + 1.2

def draw_text_scenario(ax: plt.Axes, text: str):
    """Draw text-based scenario description with formatting"""
    ax.clear()
    ax.axis('off')
    
    ax.text(0.5, 0.5, text, 
           ha='center', va='center', 
           fontsize=9, 
           fontfamily='DejaVu Sans',
           wrap=True)


def setup_standard_axis(ax: plt.Axes, xlim: Tuple[float, float] = (-5, 105),
                        ylim: Tuple[float, float] = (-5, 105),
                        xticks: Optional[List[float]] = None,
                        yticks: Optional[List[float]] = None,
                        xlabel: str = 'Human Mean',
                        ylabel: str = 'Model Prediction',
                        show_ylabel: bool = True,
                        equal_aspect: bool = True):
    """Set up standard axis formatting for scatter plots"""
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    if xticks is None:
        xticks = [0, 25, 50, 75, 100]
    if yticks is None:
        yticks = [0, 25, 50, 75, 100]

    ax.set_xticks(xticks)
    ax.set_yticks(yticks)
    ax.set_xlabel(xlabel, fontsize=11)

    if show_ylabel:
        ax.set_ylabel(ylabel, fontsize=11)

    if equal_aspect:
        ax.set_aspect('equal')

    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)


def plot_horizontal_ci_bars(ax: plt.Axes, x_lower: np.ndarray, x_upper: np.ndarray,
                            y: np.ndarray, color: str = 'gray', alpha: float = 0.3,
                            linewidth: float = 1.5, zorder: int = 1):
    """Plot horizontal confidence interval bars"""
    for i in range(len(x_lower)):
        ax.plot([x_lower[i], x_upper[i]], [y[i], y[i]],
               color=color, alpha=alpha, linewidth=linewidth, zorder=zorder)


def plot_vertical_ci_bars(ax: plt.Axes, x: np.ndarray, y_lower: np.ndarray,
                         y_upper: np.ndarray, color: str = 'gray', alpha: float = 0.3,
                         linewidth: float = 1.5, zorder: int = 1):
    """Plot vertical confidence interval bars"""
    for i in range(len(y_lower)):
        ax.plot([x[i], x[i]], [y_lower[i], y_upper[i]],
               color=color, alpha=alpha, linewidth=linewidth, zorder=zorder)


def add_stats_textbox(ax: plt.Axes, r: float, rmse: float,
                     position: Tuple[float, float] = (0.05, 0.95),
                     fontsize: int = 9, valign: str = 'top'):
    """Add correlation and RMSE statistics to plot"""
    ax.text(position[0], position[1], f'RMSE = {rmse:.2f}\nr = {r:.2f}',
           transform=ax.transAxes, fontsize=fontsize, verticalalignment=valign,
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.7, edgecolor='none'))


def add_identity_line(ax: plt.Axes, xlim: Tuple[float, float] = (0, 100),
                     color: str = 'k', linestyle: str = '--',
                     alpha: float = 0.3, linewidth: float = 1):
    """Add identity line (y=x) to plot"""
    ax.plot([xlim[0], xlim[1]], [xlim[0], xlim[1]],
           color=color, linestyle=linestyle, alpha=alpha, linewidth=linewidth)


def create_verb_legend_elements(colors: dict, labels: dict, verbs: List[str]):
    """Create legend elements for verb colors"""
    return [plt.Rectangle((0, 0), 1, 1, color=colors[verb], label=labels[verb])
            for verb in verbs]
