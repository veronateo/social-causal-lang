from typing import Dict, Optional
from .domains.base import DomainState

# Valid ablation types
ABLATION_TYPES = [None, 'no_aligned', 'no_causal', 'no_aligned_no_causal', 'no_costs']

class InertialVerbClassifier:
    """
    Classifies verbs based on DomainState tuple (Necessity, Aligned, Acted).
    Returns soft probabilities for usage in RSA.
    
    Semantics:
    - Caused:  necessity * action
    - Enabled: necessity * action * aligned
    - Allowed: necessity * aligned
    - Made No Difference: 1 - necessity
    """
    def __init__(self, 
                 epsilon: float = 0.01, 
                 ablation: Optional[str] = None,
                 necessity_mode: str = 'avg'):
        self.epsilon = epsilon
        if ablation is not None and ablation not in ABLATION_TYPES:
            raise ValueError(f"Invalid ablation type: {ablation}. Must be one of {ABLATION_TYPES}")
        self.ablation = ablation
        self.necessity_mode = necessity_mode
        
    def get_verb_probabilities(self, state: DomainState) -> Dict[str, float]:
        """
        Compute semantic truth values (0-1) and return normalized distribution.
        """
        A = float(state.aligned)
        V = float(state.wizard_acted)
        
        # Get necessity based on mode
        try:
            necessity = float(getattr(state, f'necessity_{self.necessity_mode}'))
        except AttributeError:
            necessity = float(getattr(state, 'necessity_control', 0.0))
            
        # Ablation flags
        use_aligned = self.ablation not in ['no_aligned', 'no_aligned_no_causal']
        use_causal = self.ablation not in ['no_causal', 'no_aligned_no_causal']
        
        eff_nec = necessity if use_causal else 1.0
        
        # Alignment terms (ablated → treat as 1.0, removing alignment influence)
        if use_aligned:
            align_good = A
        else:
            align_good = 1.0
            
        # Calculate scores
        scores = {}
        scores['caused'] = eff_nec * V
        scores['enabled'] = eff_nec * V * align_good
        scores['allowed'] = eff_nec * align_good
        scores['made_no_difference'] = 1.0 - eff_nec
        
        # Apply epsilon smoothing
        for k in scores:
            scores[k] = scores[k] * (1 - self.epsilon) + (self.epsilon / 4.0)
        
        # Normalize
        total = sum(scores.values())
        if total == 0:
            scores = {k: 0.25 for k in scores}
        else:
            scores = {k: v / total for k, v in scores.items()}
        
        return scores
