"""
Rational Speech Act (RSA) model for causal verb selection.

Architecture:
    L0 (Literal Listener): P(w|u) ∝ ⟦u⟧(w) · P(w)
    S1 (Pragmatic Speaker): P(u|w) ∝ exp(α · log L0(w|u))
"""
from typing import Dict, Optional
import numpy as np
from .semantics import Semantics, ABLATION_TYPES
from .domains.base import WorldState


class RSACausalVerbModel:
    """
    Rational Speech Act model for causal verb selection.
    
    Architecture:
    - L0 (Literal Listener): P(w|u) ∝ ⟦u⟧(w) · P(w)
      Computed for continuous worlds w using a precomputed grid for normalization.
    - S1 (Pragmatic Speaker): P(u|w_actual) ∝ exp(α · (ln P_L0(w_actual|u) - cost(u)))
    """
    def __init__(self, 
                 rationality_alpha: float = 1.0, 
                 costs: Dict[str, float] = None,
                 grid_resolution: int = 11,
                 ablation: Optional[str] = None):
        self.alpha = rationality_alpha
        
        if ablation is not None and ablation not in ABLATION_TYPES:
            raise ValueError(f"Invalid ablation type: {ablation}. Must be one of {ABLATION_TYPES}")
        self.ablation = ablation
        self.costs = costs or {
            'caused': 0.0, 
            'enabled': 0.0, 
            'allowed': 0.0, 
            'made_no_difference': 0.0
        }
        self.semantics = Semantics(
            ablation=ablation
        )
        self.verbs = ['caused', 'enabled', 'allowed', 'made_no_difference']
        
        # Precompute the marginal probability of each verb P(u) over the world prior
        self.verb_marginals = self._precompute_verb_marginals(grid_resolution)
    
    
    def _precompute_verb_marginals(self, resolution: int) -> Dict[str, float]:
        """
        Compute P(u) = Σ_w P(u|w) P(w) using vectorized operations.
        Assumes uniform P(w) over world states (C, A, V).
        """
        # Create grid points for continuous dimensions
        grid_C = np.linspace(0, 1, resolution)  # Counterfactual necessity
        grid_V = np.linspace(0, 1, resolution)  # Value alignment
        grid_A = np.array([0.0, 1.0])            # Action (binary)
        
        # Create meshgrid for 3 dimensions
        grids = np.meshgrid(grid_C, grid_A, grid_V, indexing='ij')
        
        C = grids[0].flatten()
        A = grids[1].flatten()
        V = grids[2].flatten()
        
        # Ablation flags
        use_aligned = self.ablation not in ['no_aligned', 'no_aligned_no_causal']
        use_causal = self.ablation not in ['no_causal', 'no_aligned_no_causal']
        
        eff_C = C if use_causal else np.ones_like(C)
        eff_V = V if use_aligned else np.ones_like(V)
            
        # Semantic denotations (vectorized)
        scores = {
            'caused':              eff_C * A,
            'enabled':             eff_C * A * eff_V,
            'allowed':             eff_C * eff_V,
            'made_no_difference':  1.0 - eff_C,
        }
            
        # Apply epsilon smoothing
        epsilon = self.semantics.epsilon
        for u in self.verbs:
            scores[u] = scores[u] * (1 - epsilon) + (epsilon / 4.0)
            
        # Compute marginals: P(u) = mean over grid (uniform prior)
        marginals = {}
        for u in self.verbs:
            marginals[u] = np.mean(scores[u])
            
        return marginals

    def pragmatic_speaker_s1(self, state: WorldState) -> Dict[str, float]:
        """
        Compute S1 speaker probabilities P(u | w_actual).
        
        S1(u | w) ∝ exp(α · log L0(w | u))
        
        where L0(w | u) ∝ ⟦u⟧(w) / P(u)
        """
        utilities = []
        truth_values = self.semantics.get_verb_probabilities(state)
        
        for u in self.verbs:
            # Semantic truth value ⟦u⟧(w_actual)
            likelihood = truth_values.get(u, 0.0)
            
            # Marginal P(u) — the "extension size" of the verb
            marginal = self.verb_marginals.get(u, 1e-9)
            
            # Literal listener inference P(w | u), normalized by verb frequency
            prob_listener_infers_correctly = likelihood / marginal
            prob_listener_infers_correctly = max(prob_listener_infers_correctly, 1e-10)
            
            # S1 utility: α · ln P(w|u)
            util = np.log(prob_listener_infers_correctly)
            utilities.append(util * self.alpha)
            
        probs = softmax(np.array(utilities))
        return dict(zip(self.verbs, probs))



def softmax(x: np.ndarray) -> np.ndarray:
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()