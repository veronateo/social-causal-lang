import os
import csv
import json
import glob
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from collections import defaultdict
from src.model.config import TRIAL_DATA_FILE, DEFAULT_DATA_DIR_SPEAKER


# Constants
PHYSICAL_HUMAN_DIR = 'data/physical_speaker/humans'
PHYSICAL_TRIALS_PATH = 'data/physical_speaker/trials.csv'
PREFERENCE_HUMAN_DIR = 'data/preference_speaker/humans'
BELIEF_HUMAN_DIR = 'data/belief_speaker/humans'
BELIEF_TRIALS_PATH = 'data/belief_speaker/trials.csv'


# Preference definitions derived from docs/js/preference-trial-definitions.js
PREFERENCE_TRIALS = {
    # Config 1: 1B v 2A
    'trial_a': {'initialConfig': {'left': {'bananas': 1, 'apples': 0}, 'right': {'bananas': 0, 'apples': 2}}, 'initial_direction': 'left', 'final_outcome': 'right', 'wizardAction': {'type': 'add_apple', 'side': 'right'}},
    'trial_b': {'initialConfig': {'left': {'bananas': 1, 'apples': 0}, 'right': {'bananas': 0, 'apples': 2}}, 'initial_direction': 'left', 'final_outcome': 'left', 'wizardAction': {'type': 'nothing', 'side': 'middle'}},
    'trial_c': {'initialConfig': {'left': {'bananas': 1, 'apples': 0}, 'right': {'bananas': 0, 'apples': 2}}, 'initial_direction': 'right', 'final_outcome': 'left', 'wizardAction': {'type': 'add_apple', 'side': 'left'}},
    'trial_d': {'initialConfig': {'left': {'bananas': 1, 'apples': 0}, 'right': {'bananas': 0, 'apples': 2}}, 'initial_direction': 'right', 'final_outcome': 'right', 'wizardAction': {'type': 'add_apple', 'side': 'right'}},
    
    # Config 2: 2B v 1A
    'trial_e': {'initialConfig': {'left': {'bananas': 2, 'apples': 0}, 'right': {'bananas': 0, 'apples': 1}}, 'initial_direction': 'left', 'final_outcome': 'left', 'wizardAction': {'type': 'add_apple', 'side': 'left'}},
    'trial_f': {'initialConfig': {'left': {'bananas': 2, 'apples': 0}, 'right': {'bananas': 0, 'apples': 1}}, 'initial_direction': 'left', 'final_outcome': 'right', 'wizardAction': {'type': 'add_apple', 'side': 'right'}},
    'trial_g': {'initialConfig': {'left': {'bananas': 2, 'apples': 0}, 'right': {'bananas': 0, 'apples': 1}}, 'initial_direction': 'right', 'final_outcome': 'left', 'wizardAction': {'type': 'add_apple', 'side': 'left'}},
    'trial_h': {'initialConfig': {'left': {'bananas': 2, 'apples': 0}, 'right': {'bananas': 0, 'apples': 1}}, 'initial_direction': 'right', 'final_outcome': 'right', 'wizardAction': {'type': 'add_apple', 'side': 'left'}},
    'trial_i': {'initialConfig': {'left': {'bananas': 2, 'apples': 0}, 'right': {'bananas': 0, 'apples': 1}}, 'initial_direction': 'right', 'final_outcome': 'right', 'wizardAction': {'type': 'nothing', 'side': 'middle'}},
    
    # Config 3: 2B v 2A
    'trial_j': {'initialConfig': {'left': {'bananas': 2, 'apples': 0}, 'right': {'bananas': 0, 'apples': 2}}, 'initial_direction': 'left', 'final_outcome': 'left', 'wizardAction': {'type': 'add_apple', 'side': 'left'}},
    'trial_k': {'initialConfig': {'left': {'bananas': 2, 'apples': 0}, 'right': {'bananas': 0, 'apples': 2}}, 'initial_direction': 'left', 'final_outcome': 'right', 'wizardAction': {'type': 'add_apple', 'side': 'right'}},
    'trial_l': {'initialConfig': {'left': {'bananas': 2, 'apples': 0}, 'right': {'bananas': 0, 'apples': 2}}, 'initial_direction': 'left', 'final_outcome': 'left', 'wizardAction': {'type': 'nothing', 'side': 'middle'}},
    'trial_m': {'initialConfig': {'left': {'bananas': 2, 'apples': 0}, 'right': {'bananas': 0, 'apples': 2}}, 'initial_direction': 'right', 'final_outcome': 'left', 'wizardAction': {'type': 'add_apple', 'side': 'left'}},
    'trial_n': {'initialConfig': {'left': {'bananas': 2, 'apples': 0}, 'right': {'bananas': 0, 'apples': 2}}, 'initial_direction': 'right', 'final_outcome': 'right', 'wizardAction': {'type': 'nothing', 'side': 'middle'}},
}

def _load_human_responses(directory: str) -> Tuple[Dict[str, Dict[str, float]], Dict[str, int]]:
    """
    Aggregates human responses from all CSVs in a directory.
    Returns: ({trial_id: {verb: prob}}, {trial_id: N})
    """
    agg = defaultdict(lambda: defaultdict(int))
    
    # Check if directory exists
    if not os.path.exists(directory):
        print(f"Warning: Directory {directory} not found. Skipping.")
        return {}, {}

    for fname in os.listdir(directory):
        # Fix: Only read *_trials.csv files (ignore feedback.csv)
        if not fname.endswith('_trials.csv'): continue
        
        path = os.path.join(directory, fname)
        try:
            df = pd.read_csv(path)
            # Normalize column names if needed
            # Usually: trial_id, response
            for _, row in df.iterrows():
                tid = row['trial_id']
                resp = str(row['response']).lower().replace(" ", "_")
                
                # Normalize specific verb variations
                if resp == 'no_difference':
                    resp = 'made_no_difference'
                    
                agg[tid][resp] += 1
        except Exception as e:
            print(f"Error reading {fname}: {e}")
            
    # Normalize to probabilities
    probs = {}
    counts = {}
    for tid, cnts in agg.items():
        total = sum(cnts.values())
        if total == 0: continue
        probs[tid] = {k: v/total for k, v in cnts.items()}
        counts[tid] = total
        
    return probs, counts

def load_physical_data() -> List[Tuple[Dict[str, Any], Dict[str, float]]]:
    """
    Loads Physical domain data.
    Returns list of (trial_data, human_distribution).
    """
    human_probs, human_counts = _load_human_responses(PHYSICAL_HUMAN_DIR)
    
    data = []
    
    # Read definitions
    df_trials = pd.read_csv(PHYSICAL_TRIALS_PATH)
    for _, row in df_trials.iterrows():
        tid = row['trial_id']
        
        # Map fields to PhysicalDomain expectations
        # farmer_initial_direction_goal: apple -> right, banana -> left
        # (Assuming Apple=Right=18, Banana=Left=0 in standard grid)
        goal = row['farmer_initial_direction_goal']
        direction = 'right' if goal == 'apple' else 'left'
        
        trial_data = {
            'trial_id': tid,
            'rock_initial': bool(row['rock_initial_present']),
            'farmer_initial_direction': direction,
            'wizard_action': row['wizard_action'],
            'final_outcome': row['final_outcome'],
            'human_N': human_counts.get(tid, 0)
        }
        
        if tid in human_probs:
            data.append((trial_data, human_probs[tid]))
            
    return data
    
def load_belief_data() -> List[Tuple[Dict[str, Any], Dict[str, float]]]:
    """
    Loads Belief domain data.
    """
    human_probs, human_counts = _load_human_responses(BELIEF_HUMAN_DIR)
    
    data = []
    df_trials = pd.read_csv(BELIEF_TRIALS_PATH)
    
    for _, row in df_trials.iterrows():
        tid = row['trial_id']
        desc = row['scenario_description']
        
        # BeliefDomain parses 'scenario_description' directly
        trial_data = {
            'trial_id': tid,
            'scenario_description': desc,
            'human_N': human_counts.get(tid, 0)
        }
        
        if tid in human_probs:
             data.append((trial_data, human_probs[tid]))
             
    return data

def load_preference_data() -> List[Tuple[Dict[str, Any], Dict[str, float]]]:
    """
    Loads Preference domain data.
    """
    human_probs, human_counts = _load_human_responses(PREFERENCE_HUMAN_DIR)
    
    data = []
    for tid, tdef in PREFERENCE_TRIALS.items():
        if tid in human_probs:
            # tdef is already in correct format for Revealed Preference
            # Inject trial_id so it's preserved
            trial_data = tdef.copy()
            trial_data['trial_id'] = tid
            trial_data['human_N'] = human_counts.get(tid, 0)
            data.append((trial_data, human_probs[tid]))
            
    return data


def load_trial_data(filename: str = DEFAULT_DATA_DIR_SPEAKER + TRIAL_DATA_FILE) -> List[Dict[str, Any]]:
    """Load trial data from JSON."""
    with open(filename, 'r') as f:
        return json.load(f)


def load_trial_definitions(filepath: str) -> Dict[str, Any]:
    """Load trial scenario definitions from a CSV file into a dictionary."""
    df = pd.read_csv(filepath)
    return df.set_index('trial_id').to_dict('index')


def load_human_data(data_dir: str, task_filter: str = None) -> pd.DataFrame:
    """Load and combine all human trial CSV files."""
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

    if task_filter and 'task' in combined_df.columns:
        combined_df = combined_df[combined_df['task'] == task_filter]
        print(f"Loaded data from {len(csv_files)} participants, totaling {len(combined_df)} {task_filter} trials.")
    else:
        print(f"Loaded data from {len(csv_files)} participants, totaling {len(combined_df)} trials.")

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

    for response in expected_responses:
        if response not in response_counts.columns:
            response_counts[response] = 0

    for trial in expected_trials:
        if trial not in response_counts.index:
            response_counts.loc[trial] = 0

    return response_counts.reindex(index=expected_trials, columns=expected_responses)

