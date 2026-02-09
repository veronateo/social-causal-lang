import numpy as np
import pandas as pd
from typing import Dict

from src.model.config import EPS


def compute_aic_bic(nll: float, n_params: int, n_samples: int):
    """Compute AIC and BIC from negative log-likelihood."""
    aic = 2 * n_params + 2 * nll * n_samples
    bic = n_params * np.log(n_samples) + 2 * nll * n_samples
    return aic, bic


def compute_nll_loss(human_dist: pd.Series, model_dist: Dict[str, float]) -> float:
    """Compute negative log-likelihood between human and model distributions."""
    verbs = ['caused', 'enabled', 'allowed', 'made_no_difference']
    loss = 0.0
    for verb in verbs:
        human_prob = human_dist.get(verb, 0.0)
        model_prob = max(model_dist.get(verb, EPS), EPS)
        if human_prob > 0:
            loss -= human_prob * np.log(model_prob)
    return loss
