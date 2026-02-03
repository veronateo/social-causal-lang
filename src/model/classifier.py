from typing import Dict, Tuple, Optional
from .domains.base import DomainState

# Valid ablation types
ABLATION_TYPES = [None, 'no_aligned', 'no_causal', 'no_aligned_no_causal', 'no_costs']

class InertialVerbClassifier:
    """
    Classifies verbs based on DomainState tuple (Changed, Aligned, Acted).
    Returns soft probabilities for usage in RSA.
    """
    def __init__(self, 
                 epsilon: float = 0.01, 
                 ablation: Optional[str] = None,
                 lambda_act: float = 0.5,
                 lambda_align: float = 0.5,
                 necessity_mode: str = 'avg'):
        self.epsilon = epsilon
        if ablation is not None and ablation not in ABLATION_TYPES:
            raise ValueError(f"Invalid ablation type: {ablation}. Must be one of {ABLATION_TYPES}")
        self.ablation = ablation
        self.lambda_act = lambda_act
        self.lambda_align = lambda_align
        self.necessity_mode = necessity_mode
        
    def _soft_factor(self, x: float, lam: float) -> float:
        """Soft constraint: λx + (1-λ)"""
        return lam * x + (1.0 - lam)
        
    def get_verb_probabilities(self, state: DomainState, strict_valence: bool = False) -> Dict[str, float]:
        """
        Compute semantic truth values (0-1) and return normalized distribution.

        Uses fuzzy logic formulas:
        - Caused:  nec * Soft(action, λ_act) * Soft(1-aligned, λ_align)
        - Enabled: nec * action * Soft(aligned, λ_align)
        # - Allowed: nec * Soft(1-action, λ_act) * Soft(aligned, λ_align)
        - Allowed: nec * Soft(aligned, λ_align)
        - No Diff: 1 - nec
        """
        # Inferred state variables
        A = float(state.aligned)
        V = float(state.wizard_acted)
        # control = float(getattr(state, 'control', 1.0))
        
        # Get Necessity based on mode
        # Default to 'control' if attribute missing (e.g. old states)
        try:
            necessity = float(getattr(state, f'necessity_{self.necessity_mode}'))
        except AttributeError:
            necessity = float(getattr(state, 'necessity_control', 0.0))
            
        # Ablation flags
        use_aligned = self.ablation not in ['no_aligned', 'no_aligned_no_causal']
        use_causal = self.ablation not in ['no_causal', 'no_aligned_no_causal']
        
        # Apply ablation masks
        
        eff_nec = necessity if use_causal else 1.0
        eff_aligned = A if use_aligned else 1.0 # If no_aligned, treat as 1 (so (1-A) becomes 0?)
        # Wait, if use_aligned=False, we remove the aligned term.
        
        scores = {}
        
        # Compute terms
        # Action terms
        act_caused = self._soft_factor(V, self.lambda_act)
        act_enabled = V # Strict action for Enabled
        act_allowed = self._soft_factor(1.0 - V, self.lambda_act)
        
        # Alignment terms
        if use_aligned:
            align_bad = self._soft_factor(1.0 - A, self.lambda_align)
            align_good = self._soft_factor(A, self.lambda_align)
        else:
            align_bad = 1.0
            align_good = 1.0
            
        # Calculate scores
        # Caused: nec * Soft(Act, yes) * Soft(1-A, bad)
        scores['caused'] = eff_nec * act_caused #* align_bad
        
        # Enabled: nec * Act * Soft(A, good)
        scores['enabled'] = eff_nec * act_enabled * align_good
        
        # Allowed: nec * Soft(1-Act, no) * Soft(A, good)
        # Allowed: nec * Soft(A, good)
        # scores['allowed'] = eff_nec * act_allowed * align_good
        scores['allowed'] = eff_nec * align_good
        
        # Made No Difference: 1 - nec
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
