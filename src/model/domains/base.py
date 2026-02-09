from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, Literal


@dataclass
class WorldState:
    """
    Represents the world state w = (C, A, V) for verb classification.
    
    Fields match the paper's notation:
        C (necessity):  Counterfactual necessity of the wizard's action [0, 1]
        A (acted):      Whether the wizard actively intervened {0, 1}
        V (aligned):    Value alignment with farmer's preference [0, 1]
    """
    necessity: float       # C — counterfactual necessity
    acted: float           # A — wizard acted {0, 1}
    aligned: float         # V — value alignment
    
    actual_outcome: str    
    expected_outcome: str  
    preferred_outcome: str 
    
    # Debug info
    debug_necessity_info: Dict[str, float] = None
    debug_posterior: Dict[str, float] = None


# Backward compatibility alias
DomainState = WorldState


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
    def get_domain_state(self, trial_data: Dict[str, Any], theta: Optional[float] = None) -> WorldState:
        """
        Compute the world state (C, A, V) for a given trial.
        
        Args:
            trial_data: The trial data dictionary.
            theta: Optional preference parameter.
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of this domain (physical, belief, preference)."""
        pass
