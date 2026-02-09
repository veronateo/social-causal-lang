import numpy as np
from typing import Dict, Any, Optional, Literal
from .base import Domain, WorldState
from .physical_inference import PreferenceInference
from .physical_shared import FarmerGridWorld, rewards_from_theta
from ..config import ModelConfig


class PhysicalDomain(Domain):
    def __init__(
        self,
        config: ModelConfig = None,
        step_cost: float = 0.05, 
        base: float = 0.0, 
        scale: float = 1.0, 
        wizard_belief_p: float = 0.5,
        temperature: float = 0.1,
        alignment_mode: Literal['hard', 'soft'] = 'soft'
    ):
        """
        Initialize physical domain.
        
        Can be initialized either with a ModelConfig or individual parameters.
        If config is provided, it takes precedence for shared parameters.
        
        Args:
            config: Optional ModelConfig with unified parameters
            step_cost: Cost per step in grid world
            base: Base reward value
            scale: Reward scaling
            wizard_belief_p: Farmer's belief about wizard intervention
            temperature: Softmax temperature for inference
            alignment_mode: 'hard' (binary) or 'soft' (graded) alignment
        """
        super().__init__()
        
        # Use config if provided, otherwise use individual params
        if config is not None:
            step_cost = config.step_cost
            temperature = config.temperature
            alignment_mode = config.alignment_mode
        
        self.env = FarmerGridWorld()
        self.step_cost = step_cost
        self.base = base
        self.scale = scale
        self.temperature = temperature
        self.alignment_mode = alignment_mode
        # Initialize inference module
        self.inference = PreferenceInference(
            wizard_belief_p=wizard_belief_p,
            step_cost=step_cost,
            base=base,
            scale=scale,
            environment=self.env,
            temperature=temperature
        )
    
    @property
    def name(self) -> str:
        return "physical"

    def normalize_trial(self, trial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure trial data has standard fields."""
        return trial_data

    def _get_preferred_outcome(self, theta: float) -> str:
        """Get deterministic preferred outcome for a given theta."""
        rewards = rewards_from_theta(theta, self.base, self.scale)
        return 'apple' if rewards['apple'] > rewards['banana'] else 'banana'

    def _simulate_inertial_path(self, trial_data: Dict[str, Any], theta: float) -> str:
        """Simulate what would happen if the wizard did nothing for a given theta."""
        rock_initial = trial_data['rock_initial']
        initial_direction = trial_data['farmer_initial_direction']
        
        # 1. Farmer advances N steps before wizard
        pos_after_initial = self.env.advance_n_steps(
            self.env.farmer_start, 
            initial_direction, 
            self.env.steps_before_wizard, 
            rock_present=rock_initial
        )
        
        # 2. Wizard does nothing (rock state stays same)
        rock_final = rock_initial
        
        # 3. Farmer re-evaluates and picks best direction from pos_after_initial
        rewards = rewards_from_theta(theta, self.base, self.scale)
        
        # Utilities from intermediate position
        cost_to_apple = abs(self.env.apple_pos - pos_after_initial) * self.step_cost
        cost_to_banana = abs(self.env.banana_pos - pos_after_initial) * self.step_cost
        
        # Blocking check
        is_apple_blocked = (rock_final and pos_after_initial < self.env.rock_pos)
        
        if is_apple_blocked:
            u_right = rewards['banana'] - (abs(self.env.rock_pos - 1 - pos_after_initial) + abs(self.env.banana_pos - (self.env.rock_pos - 1))) * self.step_cost
        else:
            u_right = rewards['apple'] - cost_to_apple
            
        u_left = rewards['banana'] - cost_to_banana
        
        return 'apple' if u_right > u_left else 'banana'

    def compute_necessity(self, trial_data: Dict[str, Any], posterior: Dict[float, float]) -> Dict[str, float]:
        """
        Compute necessity variants by simulating counterfactual wizard actions.
        """
        initial_direction = trial_data['farmer_initial_direction']
        rock_initial = trial_data['rock_initial']
        actual_outcome = trial_data['final_outcome']
        
        # Determine farmer position after initial movement (before wizard acts)
        pos_after_initial = self.env.advance_n_steps(
            self.env.farmer_start, 
            initial_direction, 
            self.env.steps_before_wizard, 
            rock_present=rock_initial
        )
        
        if rock_initial:
            possible_actions = ['nothing', 'remove_rock']
        else:
            possible_actions = ['nothing', 'place_rock']
        
        action_diff_probs = {}
        
        for action in possible_actions:
            # Determine final rock state
            if action == 'place_rock':
                rock_final = True
            elif action == 'remove_rock':
                rock_final = False
            else: # nothing
                rock_final = rock_initial
                
            # Compute E[P(different)] over posterior
            prob_diff_weighted = 0.0
            
            for theta, theta_prob in posterior.items():
                # Reconstruct Farmer Agent for utility calc
                
                # Rewards
                rewards = rewards_from_theta(theta, self.base, self.scale)
                
                # Calculate Utilities from pos_after_initial
                # Left (Banana)
                cost_to_banana = abs(self.env.banana_pos - pos_after_initial) * self.step_cost
                u_left = rewards['banana'] - cost_to_banana
                
                # Right (Apple) - Depends on rock
                cost_to_apple_direct = abs(self.env.apple_pos - pos_after_initial) * self.step_cost
                
                # Redirect cost
                cost_current_to_rock = abs((self.env.rock_pos - 1) - pos_after_initial) * self.step_cost
                cost_rock_to_banana = abs(self.env.banana_pos - (self.env.rock_pos - 1)) * self.step_cost
                cost_redirected = cost_current_to_rock + cost_rock_to_banana
                
                if rock_final:
                    # Blocked: Right leads to banana via redirect
                    u_right = rewards['banana'] - cost_redirected
                else:
                    # Clear: Right leads to apple
                    u_right = rewards['apple'] - cost_to_apple_direct
                    
                # Softmax prob of choosing Right (Apple-ward)
                # Note: physical_inference.py uses 'softmax_choice' which we need
                from .physical_inference import softmax_choice
                p_right = softmax_choice(u_left, u_right, self.temperature)
                
                # Map p_right to p_outcome
                # If blocked, going Right gets you Banana. If clear, Apple.
                # If rock_final=False: Left=Banana, Right=Apple.
                
                if rock_final:
                    p_apple = 0.0
                else:
                    p_apple = p_right
                
                # Probability of DIFFERENT outcome
                if actual_outcome == 'apple':
                    # Diff if outcome is banana
                    p_diff = 1.0 - p_apple
                else: # banana
                    # Diff if outcome is apple
                    p_diff = p_apple
                    
                prob_diff_weighted += theta_prob * p_diff
                
            action_diff_probs[action] = prob_diff_weighted
            
            action_diff_probs[action] = prob_diff_weighted
            
        nec_control = action_diff_probs.get('nothing', 0.0)
        
        # Max Necessity (vs best alternative)
        nec_max = max(action_diff_probs.values())
        
        # Average Necessity (Alternatives Only)
        # Exclude the actual action taken (or equivalent)
        w_action_raw = trial_data['wizard_action']
        actual_action = 'nothing'
        if isinstance(w_action_raw, str):
            actual_action = w_action_raw.lower()
        elif isinstance(w_action_raw, dict):
             # handle dict if needed, usually string in physical
             actual_action = w_action_raw.get('type', 'nothing')
             
        # Normalize actual_action to match keys
        if actual_action not in possible_actions:
            # Try to map 'place' -> 'place_rock' if needed, or assume data consistency
            if 'place' in actual_action: actual_action = 'place_rock'
            if 'remove' in actual_action: actual_action = 'remove_rock'
            
        alternatives = [p for a, p in action_diff_probs.items() if a != actual_action]
        
        if alternatives:
            nec_avg = sum(alternatives) / len(alternatives)
        else:
            # Fallback if no alternatives (shouldn't happen in defined domains)
            nec_avg = 0.0
        
        return {
            'control': nec_control,
            'max': nec_max,
            'avg': nec_avg,
            'debug_info': action_diff_probs
        }


        
    def get_domain_state(self, trial_data: Dict[str, Any], theta: Optional[float] = None) -> WorldState:
        actual_outcome = trial_data['final_outcome']
        
        # Posterior over farmer preferences
        if theta is not None:
            posterior = {theta: 1.0}
        else:
            posterior = self.inference.infer_preference_distribution(trial_data)
        
        # Expected outcome based on initial direction (for logging)
        initial_direction = trial_data['farmer_initial_direction']
        expected_outcome = 'apple' if initial_direction == 'right' else 'banana'
        
        # V — Value alignment: does outcome match farmer's preference?
        if self.alignment_mode == 'hard':
            aligned = sum(
                prob for t, prob in posterior.items()
                if self._get_preferred_outcome(t) == actual_outcome
            )
        else:  # soft
            aligned = sum(
                prob * self.inference.alignment_probability(t, actual_outcome)
                for t, prob in posterior.items()
            )
        
        # A — Wizard acted?
        wizard_action = trial_data['wizard_action']
        acted = 0.0 if 'nothing' in str(wizard_action).lower() else 1.0
        
        # C — Counterfactual necessity (avg over alternative actions)
        nec_stats = self.compute_necessity(trial_data, posterior)
        
        preferred_outcome = 'probabilistic' if theta is None else self._get_preferred_outcome(theta)

        return WorldState(
            necessity=nec_stats['avg'],
            acted=acted,
            aligned=aligned,
            actual_outcome=actual_outcome,
            expected_outcome=expected_outcome,
            preferred_outcome=preferred_outcome,
            debug_necessity_info=nec_stats.get('debug_info'),
            debug_posterior=posterior
        )
