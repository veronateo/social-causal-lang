from typing import Dict, Any, Literal
from dataclasses import dataclass

# Constants
SEED = 42
EPS = 1e-10
ALL_VERBS = ['caused', 'enabled', 'allowed', 'made_no_difference']


@dataclass
class ModelConfig:
    """
    Configuration for domain models with fittable parameters.
    
    Attributes:
        temperature: Softmax temperature for choice model (lower = more deterministic)
        step_cost: Cost per step in grid world
        alpha: Rationality parameter for pragmatic speaker
        alignment_mode: 'hard' (binary) or 'soft' (graded) alignment
    """
    temperature: float = 0.1
    step_cost: float = 0.05
    alpha: float = 1.0
    alignment_mode: Literal['hard', 'soft'] = 'soft'
    
    # Utterance costs (baseline: caused = 0.0)
    cost_enabled: float = 0.0
    cost_allowed: float = 0.0
    cost_mnd: float = 0.0
    cost_caused: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'temperature': self.temperature,
            'step_cost': self.step_cost,
            'alpha': self.alpha,
            'alignment_mode': self.alignment_mode,
            'cost_enabled': self.cost_enabled,
            'cost_allowed': self.cost_allowed,
            'cost_mnd': self.cost_mnd,
            'cost_caused': self.cost_caused,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> 'ModelConfig':
        """Create from dictionary."""
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

# Data paths
TRIAL_DATA_FILE = 'trial_data.json'
TRIALS_CSV_FILE = 'trials.csv'
DEFAULT_DATA_DIR_SPEAKER = '../data/physical_speaker/'

# Optimization configuration
OPTIM_CONFIG = {
    'n_starts': 20,
    'maxiter': 200,
    'ftol': 1e-6,
}

