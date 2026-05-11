from typing import Dict, Optional
from .domains.base import WorldState

# Valid ablation types
ABLATION_TYPES = [None, 'no_aligned', 'no_causal', 'no_aligned_no_causal', 'no_costs']


class Semantics:
    """
    Computes semantic truth values for each causal expression given a world state w = (C, A, V).
    """
    def __init__(self, 
                 epsilon: float = 0.01, 
                 ablation: Optional[str] = None):
        self.epsilon = epsilon
        if ablation is not None and ablation not in ABLATION_TYPES:
            raise ValueError(f"Invalid ablation type: {ablation}. Must be one of {ABLATION_TYPES}")
        self.ablation = ablation
        
    def get_verb_probabilities(self, state: WorldState) -> Dict[str, float]:
        """
        Compute semantic truth values for each causal expression.
        """
        C = float(state.dependence)   # Counterfactual dependence
        A = float(state.acted)       # Wizard acted {0, 1}
        V = float(state.aligned)     # Value alignment [0, 1]
            
        # Ablation flags
        use_aligned = self.ablation not in ['no_aligned', 'no_aligned_no_causal']
        use_causal = self.ablation not in ['no_causal', 'no_aligned_no_causal']
        
        eff_C = C if use_causal else 1.0
        eff_V = V if use_aligned else 1.0
            
        # Semantic denotations 
        scores = {
            'caused':              eff_C * A,
            'enabled':             eff_C * A * eff_V,
            'allowed':             eff_C * eff_V,
            'made_no_difference':  1.0 - eff_C,
        }
        
        # Epsilon smoothing
        for k in scores:
            scores[k] = scores[k] * (1 - self.epsilon) + (self.epsilon / 4.0)
        
        # Normalize
        total = sum(scores.values())
        if total == 0:
            scores = {k: 0.25 for k in scores}
        else:
            scores = {k: v / total for k, v in scores.items()}
        
        return scores
