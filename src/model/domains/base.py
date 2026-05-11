from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, Literal


@dataclass
class WorldState:
    """
    Represents the world state w = (C, A, V) for expression classification.
    """
    dependence: float       # C — counterfactual dependence
    acted: float           # A — wizard acted
    aligned: float         # V — value alignment
    
    actual_outcome: str    
    expected_outcome: str  
    preferred_outcome: str 
    
    # Debug info
    debug_dependence_info: Dict[str, float] = None
    debug_posterior: Dict[str, float] = None



class Domain(ABC):
    """Abstract base class for experiment-specific world models."""
    
    def __init__(self):
        pass
    
    @abstractmethod
    def normalize_trial(self, trial_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_domain_state(self, trial_data: Dict[str, Any], theta: Optional[float] = None) -> WorldState:
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
