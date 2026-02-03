"""
Preference Domain Inference Module

Bayesian inference of farmer's fruit preferences from observed basket choices.
Uses softmax/soft rational choice for graded uncertainty.

Grid World:
- 11 tiles (positions 0-10)
- Farmer starts at position 5
- Left basket at position 0, right basket at position 10
- Farmer moves 2 steps before wizard acts
"""

import numpy as np
from typing import Dict, Any

EPS = 1e-9

# Grid world constants
GRID_SIZE = 11
FARMER_START = 5
LEFT_BASKET_POS = 0
RIGHT_BASKET_POS = 10
STEPS_BEFORE_WIZARD = 2


def theta_grid(bins: int) -> np.ndarray:
    """Generate evenly spaced theta values from 0 to 1."""
    return np.linspace(0, 1, bins)


def softmax_choice(u_left: float, u_right: float, temperature: float = 1.0) -> float:
    """
    Softmax probability of choosing right given utilities.
    
    P(right) = exp(u_right / T) / (exp(u_left / T) + exp(u_right / T))
    
    Args:
        u_left: Utility of left option
        u_right: Utility of right option  
        temperature: Softmax temperature (lower = more deterministic)
    
    Returns:
        Probability of choosing right (P(left) = 1 - P(right))
    """
    # Subtract max for numerical stability
    max_u = max(u_left, u_right)
    exp_left = np.exp((u_left - max_u) / temperature)
    exp_right = np.exp((u_right - max_u) / temperature)
    
    p_right = exp_right / (exp_left + exp_right + EPS)
    return p_right


class BasketPreferenceInference:
    """
    Infer farmer's fruit preferences from basket choice behavior.
    
    Grid world: 11 tiles (0-10), farmer at 5, baskets at 0 and 10.
    
    theta ∈ [0, 1] where higher theta = stronger apple preference.
    - u_apple(θ) = θ
    - u_banana(θ) = 1 - θ
    - U(basket) = fruit_utility - step_cost * distance
    
    Uses softmax for graded/probabilistic choice modeling.
    """
    
    def __init__(
        self, 
        theta_bins: int = 11, 
        temperature: float = 0.1,
        step_cost: float = 0.05,
        scale: float = 1.0
    ):
        """
        Args:
            theta_bins: Number of bins for discretizing theta
            temperature: Softmax temperature for choice model
            step_cost: Cost per step in grid world
        """
        self.theta_bins = theta_bins
        self.temperature = temperature
        self.step_cost = step_cost
        self.scale = scale
        
        # Grid world setup
        self.farmer_start = FARMER_START
        self.left_pos = LEFT_BASKET_POS
        self.right_pos = RIGHT_BASKET_POS
        self.steps_before_wizard = STEPS_BEFORE_WIZARD
    
    def basket_utility(
        self, 
        basket: Dict[str, int], 
        theta: float, 
        farmer_pos: float = None,
        basket_side: str = None
    ) -> float:
        """
        Compute utility of a basket given preference parameter theta.
        
        U(basket) = fruit_utility - step_cost × distance
        
        Args:
            basket: Dict with 'apples' and 'bananas' counts
            theta: Preference parameter (higher = prefers apples)
            farmer_pos: Current farmer position (for distance calculation)
            basket_side: 'left' or 'right' (for basket position)
        """
        n_apples = basket.get('apples', 0)
        n_bananas = basket.get('bananas', 0)
        n_bananas = basket.get('bananas', 0)
        u_apple = theta * self.scale
        u_banana = (1 - theta) * self.scale
        fruit_utility = n_apples * u_apple + n_bananas * u_banana
        
        # Add travel cost if position provided
        if farmer_pos is not None and basket_side is not None:
            basket_pos = self.left_pos if basket_side == 'left' else self.right_pos
            distance = abs(basket_pos - farmer_pos)
            travel_cost = distance * self.step_cost
            return fruit_utility - travel_cost
        
        return fruit_utility
    
    def _get_farmer_position(self, initial_direction: str) -> float:
        """
        Get farmer position after initial movement (before wizard acts).
        
        Farmer moves 2 steps in initial direction.
        """
        if initial_direction == 'left':
            return self.farmer_start - self.steps_before_wizard
        else:  # right
            return self.farmer_start + self.steps_before_wizard
    
    def choice_probability(
        self, 
        u_left: float, 
        u_right: float, 
        chosen: str
    ) -> float:
        """
        Compute P(chosen | utilities) using softmax.
        
        Returns probability of the observed choice.
        """
        p_right = softmax_choice(u_left, u_right, self.temperature)
        
        if chosen == 'right':
            return max(p_right, EPS)
        else:
            return max(1.0 - p_right, EPS)
    
    def _apply_wizard_action(
        self, 
        initial_config: Dict[str, Dict[str, int]], 
        wizard_action: Dict[str, Any]
    ) -> Dict[str, Dict[str, int]]:
        """
        Apply wizard action to basket configuration.
        
        Returns the final basket configuration after wizard intervention.
        """
        # Deep copy
        final_config = {
            'left': dict(initial_config['left']),
            'right': dict(initial_config['right'])
        }
        
        action_type = wizard_action.get('type', 'nothing')
        target_side = wizard_action.get('side', 'middle')
        
        if action_type == 'add_apple' and target_side in ['left', 'right']:
            final_config[target_side]['apples'] = final_config[target_side].get('apples', 0) + 1
        elif action_type == 'add_banana' and target_side in ['left', 'right']:
            final_config[target_side]['bananas'] = final_config[target_side].get('bananas', 0) + 1
        # 'nothing' leaves config unchanged
        
        return final_config
    
    def infer_preference_distribution(self, trial_data: Dict[str, Any]) -> Dict[float, float]:
        """
        Infer posterior distribution over theta from observed behavior.
        
        Uses softmax likelihood for both initial and final choices,
        giving a smooth posterior over theta.
        
        Returns:
            Dict mapping theta values to posterior probabilities.
        """
        thetas = theta_grid(self.theta_bins)
        
        # Extract trial data
        initial_config = trial_data.get('initialConfig', trial_data.get('initial_config', {}))
        initial_direction = trial_data.get('initialDirection', trial_data.get('initial_direction'))
        wizard_action = trial_data.get('wizardAction', trial_data.get('wizard_action', {}))
        final_outcome = trial_data.get('finalOutcome', trial_data.get('final_outcome'))
        
        # Handle wizard_action as string or dict
        if isinstance(wizard_action, str):
            wizard_action = {'type': wizard_action, 'side': 'middle'}
        
        # Compute final basket configuration after wizard action
        final_config = self._apply_wizard_action(initial_config, wizard_action)
        
        # Farmer positions at different stages
        farmer_pos_initial = self.farmer_start  # Before any movement
        farmer_pos_after_wizard = self._get_farmer_position(initial_direction)  # After 2 steps
        
        likelihoods = {}
        
        for theta in thetas:
            # 1. Initial direction likelihood (from start position)
            u_left_initial = self.basket_utility(
                initial_config['left'], theta, farmer_pos_initial, 'left'
            )
            u_right_initial = self.basket_utility(
                initial_config['right'], theta, farmer_pos_initial, 'right'
            )
            initial_likelihood = self.choice_probability(
                u_left_initial, u_right_initial, initial_direction
            )
            
            # 2. Final outcome likelihood (from position after wizard, with final config)
            u_left_final = self.basket_utility(
                final_config['left'], theta, farmer_pos_after_wizard, 'left'
            )
            u_right_final = self.basket_utility(
                final_config['right'], theta, farmer_pos_after_wizard, 'right'
            )
            final_likelihood = self.choice_probability(
                u_left_final, u_right_final, final_outcome
            )
            
            likelihoods[theta] = initial_likelihood * final_likelihood
        
        # Normalize to get posterior
        total = sum(likelihoods.values()) + EPS
        posterior = {t: l / total for t, l in likelihoods.items()}
        
        return posterior
    
    def infer_most_likely_theta(self, trial_data: Dict[str, Any]) -> float:
        """Return the theta value with highest posterior probability."""
        dist = self.infer_preference_distribution(trial_data)
        return max(dist.items(), key=lambda x: x[1])[0]
    
    def alignment_probability(
        self, 
        theta: float, 
        actual_outcome: str, 
        basket_config: Dict[str, Dict[str, int]],
        farmer_pos: float = None
    ) -> float:
        """
        Compute probability that actual outcome aligns with farmer's preference.
        
        This is the softmax probability that the farmer would choose `actual_outcome`
        given their preference theta and the basket configuration.
        
        If P(actual | theta) is high, the farmer "got what they wanted" → aligned.
        """
        if farmer_pos is None:
            farmer_pos = self.farmer_start
            
        u_left = self.basket_utility(basket_config['left'], theta, farmer_pos, 'left')
        u_right = self.basket_utility(basket_config['right'], theta, farmer_pos, 'right')
        
        p_right = softmax_choice(u_left, u_right, self.temperature)
        
        if actual_outcome == 'right':
            return p_right
        else:
            return 1.0 - p_right
    
    def get_preferred_side(
        self, 
        theta: float, 
        basket_config: Dict[str, Dict[str, int]],
        farmer_pos: float = None
    ) -> str:
        """
        Determine which side the farmer prefers given theta and basket config.
        
        Returns the side with higher utility (deterministic, for backward compatibility).
        """
        if farmer_pos is None:
            farmer_pos = self.farmer_start
            
        u_left = self.basket_utility(basket_config['left'], theta, farmer_pos, 'left')
        u_right = self.basket_utility(basket_config['right'], theta, farmer_pos, 'right')
        
        TOLERANCE = 1e-9
        if u_left - u_right > TOLERANCE:
            return 'left'
        elif u_right - u_left > TOLERANCE:
            return 'right'
        else:
            return 'indifferent'
