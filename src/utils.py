import json
import numpy as np
import math
import hashlib
import pandas as pd
import glob
import os
import random
import csv
from scipy.special import softmax, expit
from src.model.config import TRIAL_DATA_FILE, DEFAULT_DATA_DIR_SPEAKER, SEED, EPS
from typing import Dict, Any, List
from pathlib import Path


def compute_aic_bic(nll: float, n_params: int, n_samples: int):
    """Compute AIC and BIC from negative log-likelihood"""
    aic = 2 * n_params + 2 * nll * n_samples
    bic = n_params * np.log(n_samples) + 2 * nll * n_samples
    return aic, bic

def compute_nll_loss(human_dist: pd.Series, model_dist: Dict[str, float]) -> float:
        """Compute negative log-likelihood between human and model distributions"""
        verbs = ['caused', 'enabled', 'allowed', 'made_no_difference']
        loss = 0.0
        for verb in verbs:
            human_prob = human_dist.get(verb, 0.0)
            model_prob = max(model_dist.get(verb, EPS), EPS)
            if human_prob > 0:
                loss -= human_prob * np.log(model_prob)
        return loss

def set_seed(seed: int = None):
    """Set random seed for reproducibility across numpy and random modules."""
    if seed is None:
        seed = SEED
    random.seed(seed)
    np.random.seed(seed)

def load_trial_data(filename: str = DEFAULT_DATA_DIR_SPEAKER + TRIAL_DATA_FILE) -> List[Dict[str, Any]]:
    """Load trial data from JSON."""
    with open(filename, 'r') as f:
        return json.load(f)

def sigmoid(x):
    """Numerically stable sigmoid function."""
    # Clamp input to prevent overflow
    x = max(min(x, 700), -700)
    if x >= 0:
        exp_neg_x = math.exp(-x)
        return 1 / (1 + exp_neg_x)
    else:
        exp_x = math.exp(x)
        return exp_x / (1 + exp_x)

def sigmoid_vec(x):
    if isinstance(x, (list, np.ndarray)):
        return expit(np.array(x))
    else:
        return sigmoid(x)

def softmax_vec(x, axis=-1):
    return softmax(np.array(x), axis=axis)

def exp(x, max_exp=700):
    """Exponential with overflow protection."""
    return math.exp(max(min(x, max_exp), -max_exp))

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
    exclude_keys = exclude_keys or ['scipy_result']
    
    json_result = {}
    for key, value in result.items():
        if key in exclude_keys:
            continue
        json_result[key] = convert_for_json(value)
    
    return json_result

def hash_trial_data(trial_data: Dict[str, Any]) -> str:
    """Create a hash key for trial data for caching"""
    key_data = {
        'trial_id': trial_data.get('trial_id'),
        'farmer_action': trial_data.get('farmer_action'),
        'wizard_action': trial_data.get('wizard_action'),
        'rock_present': trial_data.get('rock_present'),
        'outcome': trial_data.get('outcome')
    }
    # Sort keys for consistent hashing
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()

def hash_trial_set(possible_trials: List[Dict[str, Any]]) -> str:
    """Create a hash key for a set of possible trials"""
    trial_ids = sorted([trial.get('trial_id') for trial in possible_trials])
    key_str = json.dumps(trial_ids, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()

def hash_parameters(params: Dict[str, Any]) -> str:
    """Create a hash key for parameter dictionary"""
    key_str = json.dumps(params, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()

class SimpleCache:
    """A simple cache with optional size limit"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = {}
        self.access_order = []  # For LRU eviction

    def get(self, key: str, default=None):
        """Get item from cache"""
        if key in self.cache:
            # Update access order for LRU
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return default

    def put(self, key: str, value: Any):
        """Put item in cache"""
        if key in self.cache:
            # Update existing item
            self.access_order.remove(key)
        elif len(self.cache) >= self.max_size:
            # Evict least recently used item
            lru_key = self.access_order.pop(0)
            del self.cache[lru_key]

        self.cache[key] = value
        self.access_order.append(key)

    def clear(self):
        """Clear all cached items"""
        self.cache.clear()
        self.access_order.clear()

    def __contains__(self, key: str) -> bool:
        return key in self.cache

    def size(self) -> int:
        return len(self.cache)

def load_trial_definitions(filepath: str) -> Dict[str, Any]:
    """Load trial scenario definitions from a CSV file into a dictionary."""
    df = pd.read_csv(filepath)
    return df.set_index('trial_id').to_dict('index')

def load_human_data(data_dir: str, task_filter: str = None) -> pd.DataFrame:
    """Load and combine all human trial CSV files."""
    """Load and combine all human trial CSV files."""
    # Try specific subdirectories first
    csv_files = []
    for subdir in ["humans/", "humans_v1/", ""]:
        human_data_dir = os.path.join(data_dir, subdir)
        csv_files = glob.glob(os.path.join(human_data_dir, "*_trials.csv"))
        if csv_files:
            break

    all_data = []
    for file in csv_files:
        df = pd.read_csv(file)
        participant_id = os.path.basename(file).replace('_trials.csv', '')
        df['participant_id'] = participant_id
        all_data.append(df)

    combined_df = pd.concat(all_data, ignore_index=True)

    # Filter by task type if specified
    if task_filter and 'task' in combined_df.columns:
        combined_df = combined_df[combined_df['task'] == task_filter]
        print(f"Loaded data from {len(csv_files)} participants, totaling {len(combined_df)} {task_filter} trials.")
    else:
        print(f"Loaded data from {len(csv_files)} participants, totaling {len(combined_df)} trials.")

    # Normalize response names
    if 'response' in combined_df.columns:
        combined_df['response'] = combined_df['response'].replace({
            'no_difference': 'made_no_difference'
        })

    return combined_df


def get_trial_response_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Create a pivot table of response counts by trial."""
    expected_trials = sorted(df['trial_id'].unique(), key=lambda x: x.split('_')[1])
    expected_responses = ['caused', 'enabled', 'allowed', 'made_no_difference']

    response_counts = df.groupby(['trial_id', 'response']).size().unstack(fill_value=0)

    # Check all expected responses and trials exist
    for response in expected_responses:
        if response not in response_counts.columns:
            response_counts[response] = 0

    for trial in expected_trials:
        if trial not in response_counts.index:
            response_counts.loc[trial] = 0

    return response_counts.reindex(index=expected_trials, columns=expected_responses)

def find_latest_fit_results(results_dir: str, model_level: str = None):
    """Recursively search for RSA fitting results JSON file in directory."""
    # Search patterns in order of preference
    if model_level == 'S1':
        patterns = ['**/s1_fit*.json']
    elif model_level == 'S0':
        patterns = ['**/s0_fit*.json']
    else:
        patterns = [
            '**/s1_fit*.json',
            '**/s0_fit*.json',
            '**/rsa_generalization_assessment*.json',
            '**/rsa_cv*.json',
            '**/rsa_multistart_fitting*.json',
            '**/rsa*fitting*.json',
            '**/rsa_fit*.json',
            '**/*fitting*.json'
        ]

    candidates = []
    for pattern in patterns:
        full_pattern = os.path.join(results_dir, pattern)
        matches = glob.glob(full_pattern, recursive=True)
        candidates.extend(matches)

    if not candidates:
        return None

    # Return the most recently modified file
    return max(candidates, key=os.path.getmtime)

def load_fitted_params(results_dir: str, model_level: str = None) -> Dict:
    """Load fitted RSA parameters from results directory.
    Recursively searches for fitting results JSON file and extracts parameters.
    """
    results_path = find_latest_fit_results(results_dir, model_level=model_level)

    if results_path is None:
        raise FileNotFoundError(
            f"No RSA fitting results found in {results_dir}. "
            f"Run fitting first or provide a directory with fitting results."
        )

    print(f"Loading fitted parameters from: {results_path}")

    with open(results_path, 'r') as f:
        results = json.load(f)

    # Try different JSON structures (different fitting scripts save differently)
    if 'train_fit_result' in results:
        # Cross-validation results format
        params = results['train_fit_result']['best_params']
    elif 'best_params' in results:
        # Direct fitting results format
        params = results['best_params']
    else:
        raise KeyError(
            f"Could not find 'best_params' in {results_path}. "
            f"Expected 'best_params' or 'train_fit_result.best_params' key."
        )

    # Validate expected parameters based on model level
    if model_level == 'S0':
        expected_params = [
            'classifier_impact_sensitivity',
            'classifier_effect_threshold',
            'classifier_soft_and_mismatch_weight',
            'farmer_step_cost'
        ]
    else:
        expected_params = [
            'rationality_alpha',
            'classifier_impact_sensitivity',
            'classifier_effect_threshold',
            'classifier_soft_and_mismatch_weight',
            'farmer_step_cost'
        ]
        # Also allow new parameter names
        new_params = [
            'alpha',
            'lambda_action_yes', 
            'lambda_action_no', 
            'lambda_align_bad', 
            'lambda_align_good',
            'step_cost',
            'temperature'
        ]
        
        # Check if we have either set of parameters
        has_old = all(p in params for p in expected_params)
        has_new = all(p in params for p in new_params)
        
        if not (has_old or has_new):
            missing_old = [p for p in expected_params if p not in params]
            missing_new = [p for p in new_params if p not in params]
            raise KeyError(f"Missing expected parameters. \nMissing old format: {missing_old}\nMissing new format: {missing_new}")

        return params

    missing = [p for p in expected_params if p not in params]
    if missing:
        raise KeyError(f"Missing expected parameters: {missing}")

    return params

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

    # Append to CSV
    with open(csv_path, 'a', newline='') as f:
        fieldnames = [
            # Trial and preference info
            'trial_id', 'theta', 'P_theta_given_obs',
            # Actual outcome info
            'actual_outcome', 'actual_wizard_action', 'R_actual', 'path_cost_actual',
            'U_actual',
            # Counterfactual info
            'counterfactual_outcome', 'counterfactual_wizard_action', 'R_counterfactual', 'path_cost_cf',
            'U_counterfactual',
            # Impact score
            'impact_score',
            # Classifier intermediate values (masses)
            'w_zero', 'w_pos', 'w_neg',
            # Classifier truth values
            'truth_caused', 'truth_enabled', 'truth_allowed', 'Z_pos',
            # Literal verb probabilities (per theta, from world model)
            'p_caused', 'p_enabled', 'p_allowed', 'p_made_no_difference',
            # Final model predictions (S0 marginalized or S1 pragmatic)
            'model_final_caused', 'model_final_enabled', 'model_final_allowed', 'model_final_made_no_difference'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if write_header:
            writer.writeheader()

        writer.writerows(debug_rows)
