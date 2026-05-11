import os
import csv
import json
import random
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from pathlib import Path

from src.model.config import SEED


def set_seed(seed: int = None):
    """Set random seed for reproducibility across numpy and random modules."""
    if seed is None:
        seed = SEED
    random.seed(seed)
    np.random.seed(seed)


def convert_for_json(obj):
    """Convert numpy types to JSON-serializable types and round floats to 4 decimal places."""
    if isinstance(obj, np.ndarray):
        return [convert_for_json(item) for item in obj.tolist()]
    elif isinstance(obj, np.floating):
        return round(float(obj), 4)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, float):
        return round(obj, 4)
    elif isinstance(obj, list):
        return [convert_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_for_json(value) for key, value in obj.items()}
    return obj


def clean_result_for_json(result: Dict[str, Any], exclude_keys: list = None) -> Dict[str, Any]:
    """Clean a result dictionary for JSON serialization."""
    exclude_keys = exclude_keys or ['scipy_result']

    json_result = {}
    for key, value in result.items():
        if key in exclude_keys:
            continue
        json_result[key] = convert_for_json(value)

    return json_result


def extract_factors_responses(data_dir: str, output_file: str = None) -> List[str]:
    """Extract all factors responses from feedback files."""
    data_path = Path(data_dir)
    feedback_files = sorted(data_path.glob('*_feedback.csv'))

    all_responses = []
    for file in feedback_files:
        df = pd.read_csv(file)
        if 'factors' in df.columns:
            response = df['factors'].iloc[0]
            if pd.notna(response) and str(response).strip():
                all_responses.append(str(response).strip())

    if output_file:
        with open(output_file, 'w') as f:
            for response in all_responses:
                f.write(f"{response}\n")

    return all_responses


def save_debug_info(debug_rows: List[Dict], trial_data: Dict, output_dir: str = 'results/debug', model_label: str = None):
    """Save debugging information to CSV."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f'debug_{model_label}.csv' if model_label else 'debug.csv'
    csv_path = os.path.join(output_dir, filename)
    write_header = not os.path.exists(csv_path)

    with open(csv_path, 'a', newline='') as f:
        fieldnames = [
            'trial_id', 'theta', 'P_theta_given_obs',
            'actual_outcome', 'actual_wizard_action', 'R_actual', 'path_cost_actual',
            'U_actual',
            'counterfactual_outcome', 'counterfactual_wizard_action', 'R_counterfactual', 'path_cost_cf',
            'U_counterfactual',
            'impact_score',
            'w_zero', 'w_pos', 'w_neg',
            'truth_caused', 'truth_enabled', 'truth_allowed', 'Z_pos',
            'p_caused', 'p_enabled', 'p_allowed', 'p_made_no_difference',
            'model_final_caused', 'model_final_enabled', 'model_final_allowed', 'model_final_made_no_difference'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if write_header:
            writer.writeheader()

        writer.writerows(debug_rows)
