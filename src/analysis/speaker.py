import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from src.utils import get_trial_response_counts


def normalize_response_counts(response_counts: pd.DataFrame) -> pd.DataFrame:
    """Convert response counts to probability distributions for each trial."""
    totals = response_counts.sum(axis=1)
    normalized = response_counts.div(totals, axis=0).fillna(0)
    return normalized


def bootstrap_human_data(df: pd.DataFrame, n_bootstrap: int = 1000, ci: float = 0.95, seed: int = None) -> pd.DataFrame:
    """Bootstrap participant-level resampling to get confidence intervals."""
    if seed is not None:
        np.random.seed(seed)

    participants = df['participant_id'].unique()
    n_participants = len(participants)

    bootstrap_proportions = []

    for _ in range(n_bootstrap):
        # Resample participants with replacement
        resampled_participants = np.random.choice(participants, size=n_participants, replace=True)

        # For participants sampled multiple times, duplicate their data
        resampled_rows = []
        for p in resampled_participants:
            p_data = df[df['participant_id'] == p]
            resampled_rows.append(p_data)
        resampled_data = pd.concat(resampled_rows, ignore_index=True)

        # Calculate proportions for this bootstrap sample
        counts = get_trial_response_counts(resampled_data)
        proportions = normalize_response_counts(counts)
        bootstrap_proportions.append(proportions)

    # Convert to 3D array: [n_bootstrap x n_trials x n_responses]
    bootstrap_array = np.array([prop.values for prop in bootstrap_proportions])

    # Calculate mean and CI bounds
    alpha = 1 - ci
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100

    mean = np.mean(bootstrap_array, axis=0)
    ci_lower = np.percentile(bootstrap_array, lower_percentile, axis=0)
    ci_upper = np.percentile(bootstrap_array, upper_percentile, axis=0)

    # Convert to DataFrame with mean, lower, upper
    trial_ids = bootstrap_proportions[0].index
    responses = bootstrap_proportions[0].columns

    result = pd.DataFrame({
        'trial_id': np.repeat(trial_ids, len(responses)),
        'response': list(responses) * len(trial_ids),
        'mean': mean.flatten(),
        'ci_lower': ci_lower.flatten(),
        'ci_upper': ci_upper.flatten()
    })

    return result


def get_modal_verbs(speaker_data: pd.DataFrame) -> Dict[str, str]:
    """Get modal verb for each trial."""
    modal_verbs = {}

    for trial_id in speaker_data['trial_id'].unique():
        trial_responses = speaker_data[speaker_data['trial_id'] == trial_id]['response']
        modal_verb = trial_responses.mode()[0]
        modal_verbs[trial_id] = modal_verb

    return modal_verbs


def prepare_model_dataframe(predictions: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert model predictions to dataframe"""
    return pd.DataFrame([r['verb_distribution'] for r in predictions],
                       index=[r['trial_id'] for r in predictions])


def get_error_bars(trial_id: str, verbs: List[str], values: np.ndarray,
                   error_bars: Optional[pd.DataFrame]) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """Extract error bars for a trial"""
    if error_bars is None:
        return None, None

    trial_errors = error_bars[error_bars['trial_id'] == trial_id]
    trial_errors = trial_errors.set_index('response').reindex(verbs)

    if trial_errors.empty:
        return None, None

    yerr_lower, yerr_upper = [], []
    for i, verb in enumerate(verbs):
        val = values[i]
        lower = trial_errors.loc[verb, 'ci_lower'] if verb in trial_errors.index else val
        upper = trial_errors.loc[verb, 'ci_upper'] if verb in trial_errors.index else val
        yerr_lower.append(val - lower)
        yerr_upper.append(upper - val)

    return np.array(yerr_lower), np.array(yerr_upper)
