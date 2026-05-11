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
BELIEF_HUMAN_DIR = 'data/belief_speaker/humans'
BELIEF_TRIALS_PATH = 'data/belief_speaker/trials.csv'
PREFERENCE_HUMAN_DIR = 'data/preference_speaker/humans'
PREFERENCE_TRIALS_PATH = 'data/preference_speaker/trials.json'

# Shared domain constants
TRIAL_IDS = [f"trial_{c}" for c in "abcdefghij"]
VERBS = ["caused", "enabled", "allowed", "made_no_difference"]
UTTERANCES = [
    {"verb": v, "outcome": o}
    for v in VERBS
    for o in ["apple", "banana"]
]


def _load_preference_trials() -> dict:
    """Load preference trial definitions from JSON data file."""
    with open(PREFERENCE_TRIALS_PATH, 'r') as f:
        return json.load(f)

def _load_human_responses(directory: str) -> Tuple[Dict[str, Dict[str, float]], Dict[str, int]]:
    """
    Aggregates human responses from all CSVs in a directory.
    """
    agg = defaultdict(lambda: defaultdict(int))
    
    if not os.path.exists(directory):
        print(f"Warning: Directory {directory} not found. Skipping.")
        return {}, {}

    for fname in os.listdir(directory):
        if not fname.endswith('_trials.csv'): continue
        
        path = os.path.join(directory, fname)
        try:
            df = pd.read_csv(path)
            # Normalize column names if needed
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
    Loads physical domain data. Returns list of (trial_data, human_distribution).
    """
    human_probs, human_counts = _load_human_responses(PHYSICAL_HUMAN_DIR)
    
    data = []
    
    # Read definitions
    df_trials = pd.read_csv(PHYSICAL_TRIALS_PATH)
    for _, row in df_trials.iterrows():
        tid = row['trial_id']
        
        # Map fields to PhysicalDomain expectations
        # farmer_initial_direction_goal: apple -> right, banana -> left
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
    Loads belief domain data.
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
    Trial definitions are loaded from data/preference_speaker/trials.json.
    """
    human_probs, human_counts = _load_human_responses(PREFERENCE_HUMAN_DIR)
    preference_trials = _load_preference_trials()

    data = []
    for tid, tdef in preference_trials.items():
        if tid in human_probs:
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
    for subdir in ["humans/", ""]:
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
