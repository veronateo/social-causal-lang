from typing import Dict, Any, Optional, Literal, Union
from .base import Domain, WorldState
from .preference_inference import BasketPreferenceInference
from ..config import ModelConfig


class PreferenceDomain(Domain):
    def __init__(
        self, 
        config: ModelConfig = None,
        theta_bins: int = 11, 
        temperature: float = 0.1,
        step_cost: float = 0.05,
        alignment_mode: Literal['hard', 'soft'] = 'soft',
        scale: float = 1.0
    ):
        """
        Initialize preference domain.

        Args:
            config: Optional ModelConfig with unified parameters
            theta_bins: Number of bins for discretizing theta
            temperature: Softmax temperature for inference
            step_cost: Cost per step in grid world
            alignment_mode: 'hard' (binary) or 'soft' (graded) alignment
        """
        super().__init__()
        
        # Use config if provided, otherwise use individual params
        if config is not None:
            temperature = config.temperature
            step_cost = config.step_cost
            alignment_mode = config.alignment_mode
        
        self.inference = BasketPreferenceInference(
            theta_bins=theta_bins,
            temperature=temperature,
            step_cost=step_cost,
            scale=scale
        )
        self.alignment_mode = alignment_mode
        self.step_cost = step_cost
        self.temperature = temperature
    
    @property
    def name(self) -> str:
        return "preference"

    def normalize_trial(self, trial_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = trial_data.copy()
        
        # Normalize keys (camelCase -> snake_case)
        if 'initialDirection' in trial_data:
            normalized['initial_direction'] = trial_data['initialDirection']
        
        if 'finalOutcome' in trial_data:
            normalized['final_outcome'] = trial_data['finalOutcome']
        
        if 'initialConfig' in trial_data:
            normalized['initial_config'] = trial_data['initialConfig']
        
        if 'wizardAction' in trial_data:
            normalized['wizard_action'] = trial_data['wizardAction']
            
        return normalized

    def _get_preferred_side(self, theta: float, trial_data: Dict[str, Any]) -> str:
        """
        Determine which side the farmer prefers for a given theta based on final basket configuration (after wizard action).
        """
        data = self.normalize_trial(trial_data)
        initial_config = data.get('initial_config', data.get('initialConfig', {}))
        wizard_action = data.get('wizard_action', data.get('wizardAction', {}))
        initial_direction = data.get('initial_direction', data.get('initialDirection'))
        
        # Apply wizard action to get final config
        final_config = self.inference._apply_wizard_action(initial_config, wizard_action)
        
        # Farmer position after initial movement
        farmer_pos = self.inference._get_farmer_position(initial_direction)
        
        return self.inference.get_preferred_side(theta, final_config, farmer_pos)
        
    
    def compute_dependence(self, trial_data: Dict[str, Any], posterior: Dict[float, float]) -> Dict[str, float]:
        """
        Compute dependence variants by simulating counterfactual wizard actions.
        
        Returns dictionary with:
        - 'control': vs "nothing"
        - 'max': vs best alternative (max difference)
        - 'avg': vs average of all alternatives
        """
        data = self.normalize_trial(trial_data)
        initial_config = data.get('initial_config', data.get('initialConfig', {}))
        initial_direction = data.get('initial_direction')
        actual_outcome = data['final_outcome']
        
        # Farmer position after initial movement
        farmer_pos = self.inference._get_farmer_position(initial_direction)
        
        # Define all possible wizard actions (Universe of options)
        possible_actions = [
            {'type': 'nothing', 'side': 'middle'},
            {'type': 'add_apple', 'side': 'left'},
            {'type': 'add_apple', 'side': 'right'}
        ]
        
        # Calculate P(change) for each action, marginalized over theta
        action_diff_probs = {}
        
        for action in possible_actions:
            # Construct action key for identification
            key = f"{action['type']}_{action['side']}"
            
            # Apply counterfactual action
            cf_config = self.inference._apply_wizard_action(initial_config, action)
            
            # Compute E[P(different outcome)] over theta posterior
            prob_diff_weighted = 0.0
            for theta, theta_prob in posterior.items():
                # Prob of choosing Right given this config
                u_left = self.inference.basket_utility(cf_config['left'], theta, farmer_pos, 'left')
                u_right = self.inference.basket_utility(cf_config['right'], theta, farmer_pos, 'right')
                p_right = self.inference.choice_probability(u_left, u_right, 'right')
                
                # Probability of different outcome
                if actual_outcome == 'left':
                    p_diff = p_right
                else: # actual == 'right'
                    p_diff = 1.0 - p_right
                    
                prob_diff_weighted += theta_prob * p_diff
                
            action_diff_probs[key] = prob_diff_weighted
            
        # 1. Control dependence (vs "nothing")
        nec_control = action_diff_probs.get('nothing_middle', 0.0)
        
        # 2. Max dependence (vs action that causes most change)
        nec_max = max(action_diff_probs.values())
        
        # Average dependence (alternatives only)
        # Exclude actual action
        w_action_raw = trial_data.get('wizard_action', trial_data.get('wizardAction', {'type': 'nothing'}))
        actual_key = 'nothing_middle'
        
        if isinstance(w_action_raw, dict):
            t = w_action_raw.get('type', 'nothing')
            s = w_action_raw.get('side', 'middle')
            actual_key = f"{t}_{s}"
        elif isinstance(w_action_raw, str) and w_action_raw == 'nothing':
            actual_key = 'nothing_middle'
            
        alternatives = [p for a, p in action_diff_probs.items() if a != actual_key]
        
        if alternatives:
            nec_avg = sum(alternatives) / len(alternatives)
        else:
            nec_avg = 0.0
        
        return {
            'control': nec_control,
            'max': nec_max,
            'avg': nec_avg,
            'debug_info': action_diff_probs
        }

    def get_domain_state(self, trial_data: Dict[str, Any], theta: Optional[float] = None) -> WorldState:
        # Normalize
        data = self.normalize_trial(trial_data)
        
        expected_dir = data.get('initial_direction')
        actual_dir = data.get('final_outcome')
        wizard_action = data.get('wizard_action', data.get('wizardAction', {}))
        
        # A — Wizard acted?
        if isinstance(wizard_action, dict):
            w_type = wizard_action.get('type', 'nothing')
            acted = 1.0 if w_type != 'nothing' else 0.0
        elif isinstance(wizard_action, str):
            acted = 1.0 if wizard_action != 'nothing' else 0.0
        else:
            acted = 0.0
        
        # Get final basket configuration
        initial_config = data.get('initial_config', data.get('initialConfig', {}))
        wizard_action_dict = wizard_action if isinstance(wizard_action, dict) else {'type': wizard_action, 'side': 'middle'}
        final_config = self.inference._apply_wizard_action(initial_config, wizard_action_dict)
        
        # Farmer position after initial movement
        farmer_pos = self.inference._get_farmer_position(expected_dir)
        
        # Posterior for alignment and dependence
        if theta is not None:
            posterior = {theta: 1.0}
        else:
            posterior = self.inference.infer_preference_distribution(trial_data)
            
        # V — Value alignment: probability that actual outcome matches farmer's preference
        if self.alignment_mode == 'hard':
            # Hard alignment
            aligned = sum(
                prob for t, prob in posterior.items()
                if self._get_preferred_side(t, trial_data) == actual_dir
            )
        else:

            aligned = sum(
                prob * self.inference.alignment_probability(t, actual_dir, final_config, farmer_pos)
                for t, prob in posterior.items()
            )
        
        # C — Counterfactual dependence (avg over alternative actions)
        nec_stats = self.compute_dependence(trial_data, posterior)
        
        preferred_outcome = 'probabilistic' if theta is None else self._get_preferred_side(theta, trial_data)
        
        return WorldState(
            dependence=nec_stats['avg'],
            acted=acted,
            aligned=aligned,
            actual_outcome=actual_dir,
            expected_outcome=expected_dir,
            preferred_outcome=preferred_outcome,
            debug_dependence_info=nec_stats.get('debug_info'),
            debug_posterior=posterior
        )
