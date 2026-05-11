import numpy as np
import pandas as pd
from typing import Dict, List
from src.model.config import EPS


def compute_aic_bic(nll: float, n_params: int, n_samples: int):
    """Compute AIC and BIC from negative log-likelihood."""
    aic = 2 * n_params + 2 * nll * n_samples
    bic = n_params * np.log(n_samples) + 2 * nll * n_samples
    return aic, bic


def mean_kl_divergence(human_groups: List, model_groups: List, eps: float = 1e-10) -> float:
    """
    Mean KL(human || model) across groups.
    human_groups, model_groups: list of arrays, one per group.
    Each group sums to 1. Returns mean KL in nats.
    """
    kls = []
    for h_group, m_group in zip(human_groups, model_groups):
        h = np.asarray(h_group, dtype=float)
        m = np.asarray(m_group, dtype=float)
        h_safe = np.where(h > 0, h, 1.0) 
        m_safe = m + eps
        # 0 * log(0) = 0 by convention
        kl = np.sum(np.where(h > 0, h * np.log(h_safe / m_safe), 0.0))
        kls.append(kl)
    return float(np.mean(kls))


def mean_jsd_arrays(human_groups: List, model_groups: List, eps: float = 1e-10) -> float:
    """
    Mean JSD(human || model) across groups (base 2, bounded [0, 1]).
    human_groups, model_groups: list of arrays, one per group.
    """
    jsds = []
    for h_group, m_group in zip(human_groups, model_groups):
        h = np.asarray(h_group, dtype=float)
        m = np.asarray(m_group, dtype=float)
        mix = 0.5 * (h + m)
        mix_safe = mix + eps
        h_safe = np.where(h > 0, h, 1.0)
        m_safe = np.where(m > 0, m, 1.0)
        kl_hm = np.sum(np.where(h > 0, h * np.log2(h_safe / mix_safe), 0.0))
        kl_mh = np.sum(np.where(m > 0, m * np.log2(m_safe / mix_safe), 0.0))
        jsds.append(float(0.5 * kl_hm + 0.5 * kl_mh))
    return float(np.mean(jsds)) if jsds else float("nan")


def jsd(p: Dict[str, float], q: Dict[str, float], eps: float = 1e-10) -> float:
    """
    Jensen-Shannon Divergence between two distributions (base 2, bounded [0, 1]).
    p, q: dicts mapping keys to probabilities.
    """
    keys = sorted(set(p) | set(q))
    p_arr = np.array([p.get(k, 0.0) for k in keys], dtype=float)
    q_arr = np.array([q.get(k, 0.0) for k in keys], dtype=float)
    m = 0.5 * (p_arr + q_arr)
    m_safe = m + eps

    def _kl(a, b):
        a_safe = np.where(a > 0, a, 1.0)
        return np.sum(np.where(a > 0, a * np.log2(a_safe / b), 0.0))

    return float(0.5 * _kl(p_arr, m_safe) + 0.5 * _kl(q_arr, m_safe))


def tvd(p: Dict[str, float], q: Dict[str, float]) -> float:
    """Total Variation Distance: 0.5 * sum(|p_i - q_i|). Bounded [0, 1]."""
    keys = sorted(set(p) | set(q))
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


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
