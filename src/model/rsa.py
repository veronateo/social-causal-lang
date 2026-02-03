from typing import Dict, Any, List, Optional
import numpy as np
from itertools import product
from .classifier import InertialVerbClassifier, ABLATION_TYPES
from .domains.base import DomainState

def softmax(x: np.ndarray) -> np.ndarray:
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()

class RSACausalVerbModel:
    """
    Rational Speech Act model for causal verb selection.
    
    Architecture:
    - L0 (Literal Listener): P(w|u) ~ P(u|w) * P(w)
      Here, we calculate this for continuous worlds w using a precomputed grid for normalization.
    - S1 (Pragmatic Speaker): P(u|w_actual) ~ exp(alpha * (ln P_L0(w_actual|u) - cost(u)))
    """
    def __init__(self, 
                 rationality_alpha: float = 1.0, 
                 costs: Dict[str, float] = None,
                 grid_resolution: int = 11,
                 use_valence_cost: bool = True,
                 strict_valence_semantics: bool = False,
                 valence_cost: float = 2.0,
                 ablation: Optional[str] = None,
                 lambda_act: float = 1.0,
                 lambda_align: float = 1.0,
                 necessity_mode: str = 'avg'):
        self.alpha = rationality_alpha
        self.use_valence_cost = use_valence_cost
        self.strict_valence_semantics = strict_valence_semantics
        self.valence_cost = valence_cost
        self.lambda_act = lambda_act
        self.lambda_align = lambda_align
        self.necessity_mode = necessity_mode
        
        if ablation is not None and ablation not in ABLATION_TYPES:
            raise ValueError(f"Invalid ablation type: {ablation}. Must be one of {ABLATION_TYPES}")
        self.ablation = ablation
        self.costs = costs or {
            'caused': 0.0, 
            'enabled': 0.0, 
            'allowed': 0.0, 
            'made_no_difference': 0.0
        }
        self.classifier = InertialVerbClassifier(
            ablation=ablation, 
            lambda_act=lambda_act,
            lambda_align=lambda_align,
            necessity_mode=necessity_mode
        )
        self.verbs = ['caused', 'enabled', 'allowed', 'made_no_difference']
        
        # Precompute the marginal probability of each verb P(u) over the world prior
        self.verb_marginals = self._precompute_verb_marginals(grid_resolution)
    
    
    def _precompute_verb_marginals(self, resolution: int) -> Dict[str, float]:
        """
        Compute P(u) = Sum_w P(u|w) P(w) using vectorized operations.
        Assumes Uniform P(w) over (Necessity, Aligned, Acted).
        """
        # 1. Create grid points
        grid_points = np.linspace(0, 1, resolution)
        grid_points_binary = np.array([0.0, 1.0])
        
        # 2. Create meshgrid for 3 dimensions (Necessity, Aligned, Action)
        # Shape: (resolution, resolution, 2)
        # Note: We use 'ij' indexing. Dimensions are:
        # 0: Necessity (resolution)
        # 1: Aligned (resolution)
        # 2: Action (2)
        grids = np.meshgrid(grid_points, grid_points, grid_points_binary, indexing='ij')
        
        # Flatten grids to list of points
        Nec = grids[0].flatten()
        A = grids[1].flatten()
        V = grids[2].flatten()
        
        # Ablation flags
        use_aligned = self.ablation not in ['no_aligned', 'no_aligned_no_causal']
        use_causal = self.ablation not in ['no_causal', 'no_aligned_no_causal']
        
        # Effective params
        eff_nec = Nec if use_causal else np.ones_like(Nec)
        
        # 3. Vectorized Semantic Evaluation
        def soft_factor(x, lam):
            return lam * x + (1.0 - lam)
            
        scores = {u: np.zeros_like(Nec) for u in self.verbs}
        
        # Action terms
        act_caused = soft_factor(V, self.lambda_act)
        act_enabled = V # Strict action for Enabled
        act_allowed = soft_factor(1.0 - V, self.lambda_act)
        
        # Alignment terms
        if use_aligned:
            align_bad = soft_factor(1.0 - A, self.lambda_align)
            align_good = soft_factor(A, self.lambda_align)
        else:
            align_bad = np.ones_like(A)
            align_good = np.ones_like(A)
            
        # Calculate scores
        scores['caused'] = eff_nec * act_caused # * align_bad
        scores['enabled'] = eff_nec * act_enabled * align_good
        # scores['allowed'] = eff_nec * act_allowed * align_good
        scores['allowed'] = eff_nec * align_good
        scores['made_no_difference'] = 1.0 - eff_nec
            
        # 4. Apply epsilon smoothing and normalize
        epsilon = self.classifier.epsilon
        verb_sums = np.zeros_like(Nec)
        for u in self.verbs:
            scores[u] = scores[u] * (1 - epsilon) + (epsilon / 4.0)
            verb_sums += scores[u]
            
        # 5. Compute Marginals (Standard RSA)
        # P(u) = \sum_w P(u|w) P(w)
        # With uniform P(w), this is mean of truth values across the grid
        marginals = {}
        for u in self.verbs:
            marginals[u] = np.mean(scores[u])
            
        return marginals

    def pragmatic_speaker_s1(self, state: DomainState) -> Dict[str, float]:
        """
        Compute S1 Speaker probabilities P(u | w_actual).
        
        We calculate P_L0(w_actual | u) dynamically:
           P_L0(w | u) = P(u | w) * P(w) / P(u)
           
        Since we assume Uniform P(w), this simplifies to:
           P_L0(w | u) propto P(u | w) / P(u)
        """
        utilities = []
        truth_values = self.classifier.get_verb_probabilities(state, strict_valence=self.strict_valence_semantics)
        
        for u in self.verbs:
            # 1. Truth Value P(u | w_actual)
            likelihood = truth_values.get(u, 0.0)
            
            # 2. Marginal P(u) (The "Extension Size" of the verb)
            # A specific, narrow verb has a low P(u), making it more informative if true.
            marginal = self.verb_marginals.get(u, 1e-9)
            
            # 3. Listener Inference P(w | u)
            # Normalized by the verb's general frequency
            prob_listener_infers_correctly = likelihood / marginal
            
            # Avoid log(0)
            prob_listener_infers_correctly = max(prob_listener_infers_correctly, 1e-10)
            
            # 4. Utility
            # S1 Speaker utility: alpha * ln P(w|u)
            util = np.log(prob_listener_infers_correctly)
            utilities.append(util * self.alpha)
            
        probs = softmax(np.array(utilities))
        return dict(zip(self.verbs, probs))
