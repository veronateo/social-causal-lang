from typing import Dict, Any, Literal, Optional
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
    reward_scale: float = 1.0
    
    # Semantic parameters
    # Semantic parameters (Unified)
    lambda_act: float = 1.0     # hard constraint for Action
    lambda_align: float = 1.0   # hard constraint for Alignment
    
    # Utterance costs (baseline: caused = 0.0)
    cost_enabled: float = 0.0
    cost_allowed: float = 0.0
    cost_mnd: float = 0.0
    cost_caused: float = 0.0
    
    necessity_mode: Literal['control', 'max', 'avg'] = 'avg'
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'temperature': self.temperature,
            'step_cost': self.step_cost,
            'alpha': self.alpha,
            'alignment_mode': self.alignment_mode,
            'lambda_action_yes': self.lambda_action_yes,
            'lambda_action_no': self.lambda_action_no,
            'lambda_align_bad': self.lambda_align_bad,
            'lambda_align_good': self.lambda_align_good,
            'cost_enabled': self.cost_enabled,
            'cost_allowed': self.cost_allowed,
            'cost_mnd': self.cost_mnd,
            'necessity_mode': self.necessity_mode
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> 'ModelConfig':
        """Create from dictionary."""
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

# Data paths
TRIAL_DATA_FILE = 'trial_data.json'
TRIALS_CSV_FILE = 'trials.csv'
DEFAULT_DATA_DIR_SPEAKER = '../data/physical_speaker/'
DEFAULT_DATA_DIR_LISTENER = '../data/physical_listener/'
DEFAULT_OUTPUT_DIR = 'results'

# RSA parameters
RSA_PARAMS = {
    'farmer_step_cost': {'default': 0.05, 'bounds': (0.0, 0.1)},
    # 'wizard_belief_p': {'default': 0.5, 'bounds': (0.0, 1.0)},
    # 'classifier_impact_sensitivity': {'default': 0.5, 'bounds': (0.0, 5.0)},
    'classifier_effect_threshold': {'default': 0.1, 'bounds': (0.0, 0.1)},
    # 'classifier_soft_and_mismatch_weight': {'default': 0.5, 'bounds': (0.0, 1.0)},
    'rationality_alpha': {'default': 1.0, 'bounds': (0.0, 20.0)}
}

RSA_DEFAULTS = {k: v['default'] for k, v in RSA_PARAMS.items()}
RSA_BOUNDS = {k: v['bounds'] for k, v in RSA_PARAMS.items()}

FIXED_PARAMS = {
    "inference": {
        # "temperature": 0.01, 
        "wizard_belief_p": 0.5
    },
    "classifier": {
        "soft_and_mismatch_weight": 0.0
    },
    "preference_model": {
        "type": "continuous",
        "bins": 11,
        "base": 0.0,
        "scale": 1.0
    }
}

# Optimization configuration
OPTIM_CONFIG = {
    'n_starts': 50,
    'maxiter': 100,
    'ftol': 1e-5,
    'gtol': 1e-5,
    'early_stop_threshold': 0.001,
    'max_stagnant': 3
}

def get_model_config() -> Dict[str, Any]:
    """Build complete model config with defaults"""
    return {
        **FIXED_PARAMS,
        "inference": {
            **FIXED_PARAMS["inference"]
        },
        "environment": {"farmer_step_cost": RSA_DEFAULTS['farmer_step_cost']},
        "classifier": {
            "effect_threshold": RSA_DEFAULTS['classifier_effect_threshold'],
            "soft_and_mismatch_weight": FIXED_PARAMS["classifier"]["soft_and_mismatch_weight"]
        }
    }
