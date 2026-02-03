from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, Literal

@dataclass
class DomainState:
    """Represents the semantic state of a trial for verb classification."""
    changed: float         # Degree of change (Observable): |actual - expected|
    aligned: float         # Degree of alignment (Inferred): P(actual = preferred)
    wizard_acted: float    # Degree of wizard intervention (Observable): 0.0 or 1.0
    # control: float         # Capacity (Inferred): Did wizard have power to influence?
    actual_outcome: str    
    expected_outcome: str  
    preferred_outcome: str 
    
    # Necessity variants (Counterfactuals)
    necessity_control: float = 0.0 # vs Do Nothing
    necessity_max: float = 0.0     # vs Best Alternative
    necessity_avg: float = 0.0     # vs Average Alternative
    
    # Debug info
    debug_necessity_info: Dict[str, float] = None
    debug_posterior: Dict[str, float] = None

class Domain(ABC):
    """Abstract base class for experiment-specific world models."""
    
    def __init__(self):
        """Initialize the domain model."""
        pass
    
    @abstractmethod
    def normalize_trial(self, trial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize raw trial data into a standard format."""
        pass
    
    @abstractmethod
    def get_domain_state(self, trial_data: Dict[str, Any], theta: Optional[float] = None) -> DomainState:
        """
        Compute the domain state (Changed, Aligned, Acted) for a given trial.
        
        Args:
            trial_data: The trial data dictionary.
            theta: Optional preference parameter (for physical domain).
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of this domain (physical, belief, preference)."""
        pass

