import os
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Any
from PIL import Image

# Path to images
IMAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs", "images"))

def load_image(image_name: str):
    """Load image from docs/images directory"""
    img_path = os.path.join(IMAGE_DIR, image_name)
    if os.path.exists(img_path):
        pil_img = Image.open(img_path).convert('RGBA')
        return np.array(pil_img) / 255.0
    return None

def draw_physical_scenario(trial_info: Dict[str, Any], ax: plt.Axes):
    """
    Draws the visual scenario for a physical trial.
    Ported from archive plotting_utils.py.
    """
    ax.clear()
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 2)
    ax.axis('off')

    img_size = 0.8
    y_pos = 1.0

    # Load images
    rock_img = load_image('rock.png')
    farmer_img = load_image('farmer.png')
    wizard_img = load_image('wizard.png')
    
    # Determine Goal (Apple/Banana) from direction or explicit field
    # In trial_data, we often have 'farmer_initial_direction'. 
    # Mapped: Right -> Apple, Left -> Banana (Standard Map)
    direction = trial_info.get('farmer_initial_direction', 'right')
    initial_goal = 'apple' if direction == 'right' else 'banana'
    
    initial_goal_img = load_image(f'{initial_goal}.png')
    
    # Final Outcome
    final_outcome = trial_info.get('final_outcome', 'apple')
    outcome_img = load_image(f'{final_outcome}.png')

    # Initial state
    is_rock_present = trial_info.get('rock_initial', False)
    farmer_x = 1.7 if is_rock_present else 1.0

    # Draw Rock (Initial)
    if is_rock_present and rock_img is not None:
        ax.imshow(rock_img, extent=[0.5-img_size/2, 0.5+img_size/2, y_pos-img_size/2, y_pos+img_size/2])

    # Draw Farmer (Initial)
    if farmer_img is not None:
        ax.imshow(farmer_img, extent=[farmer_x-img_size/2, farmer_x+img_size/2, y_pos-img_size/2, y_pos+img_size/2])

    # Arrow to Goal
    arrow_x = farmer_x + 1.2
    ax.text(arrow_x, y_pos, '→', fontsize=14, ha='center', va='center', fontfamily='DejaVu Sans', fontweight='bold')

    # Goal Icon
    goal_x = arrow_x + 1.2
    if initial_goal_img is not None:
        ax.imshow(initial_goal_img, extent=[goal_x-img_size/2, goal_x+img_size/2, y_pos-img_size/2, y_pos+img_size/2])
    
    # Separator
    ax.text(goal_x + 0.7, y_pos, ',', fontsize=12, ha='center', va='center')

    # Wizard Action
    wizard_x = 5.5
    if wizard_img is not None:
        ax.imshow(wizard_img, extent=[wizard_x-img_size/2, wizard_x+img_size/2, y_pos-img_size/2, y_pos+img_size/2])

    wizard_action = trial_info.get('wizard_action', 'nothing')
    
    action_item_x = wizard_x + 1.0
    
    if wizard_action == 'place_rock' and rock_img is not None:
        ax.imshow(rock_img, extent=[action_item_x-img_size/2, action_item_x+img_size/2, y_pos-img_size/2, y_pos+img_size/2])
    elif wizard_action == 'remove_rock' and rock_img is not None:
        # Show Faded Rock with X
        ax.imshow(rock_img, extent=[action_item_x-img_size/2, action_item_x+img_size/2, y_pos-img_size/2, y_pos+img_size/2], alpha=0.5)
        ax.text(action_item_x, y_pos, 'X', fontsize=14, ha='center', va='center', color='red', fontweight='bold')
    
    # Separator
    ax.text(action_item_x + 0.7, y_pos, ',', fontsize=12, ha='center', va='center')

    # Final Outcome Section
    outcome_farmer_x = 8.0
    if farmer_img is not None:
        ax.imshow(farmer_img, extent=[outcome_farmer_x-img_size/2, outcome_farmer_x+img_size/2, y_pos-img_size/2, y_pos+img_size/2])

    outcome_arrow_x = outcome_farmer_x + 1.2
    ax.text(outcome_arrow_x, y_pos, '→', fontsize=14, ha='center', va='center', fontfamily='DejaVu Sans', fontweight='bold')

    # Final Fruit Icon
    outcome_fruit_x = outcome_arrow_x + 1.2
    if outcome_img is not None:
        ax.imshow(outcome_img, extent=[outcome_fruit_x-img_size/2, outcome_fruit_x+img_size/2, y_pos-img_size/2, y_pos+img_size/2])
