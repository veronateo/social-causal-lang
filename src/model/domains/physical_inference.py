import numpy as np
from typing import Dict, Any, List
from .physical_shared import FarmerGridWorld, rewards_from_theta
import numpy as np

EPS = 1e-9


class FarmerAgent:
    """A rational farmer agent with continuous preferences."""
    def __init__(
        self,
        theta: float,             
        wizard_belief_p: float,   
        step_cost: float,         
        base: float,              
        scale: float,             
        environment: FarmerGridWorld = None
    ):
        self.theta = theta
        self.rewards = rewards_from_theta(theta, base, scale)
        
        self.p = wizard_belief_p
        self.step_cost = step_cost
        self.env = environment or FarmerGridWorld()

    def compute_expected_utility(self, target: str, initial_rock_present: bool) -> float:
        cost_to_apple_direct = abs(self.env.apple_pos - self.env.farmer_start) * self.step_cost
        cost_to_banana_direct = abs(self.env.banana_pos - self.env.farmer_start) * self.step_cost
        
        cost_farmer_to_rock = abs((self.env.rock_pos - 1) - self.env.farmer_start) * self.step_cost
        cost_rock_to_banana = abs(self.env.banana_pos - (self.env.rock_pos - 1)) * self.step_cost
        cost_redirected_to_banana = cost_farmer_to_rock + cost_rock_to_banana
        
        if target == 'apple':
            if not initial_rock_present:
                expected_cost = self.p * cost_to_apple_direct + (1-self.p) * cost_redirected_to_banana
                return (self.p * self.rewards['apple'] + (1-self.p) * self.rewards['banana'] - expected_cost)
            else:
                expected_cost = self.p * cost_redirected_to_banana + (1-self.p) * cost_to_apple_direct
                return (self.p * self.rewards['banana'] + (1-self.p) * self.rewards['apple'] - expected_cost)
        else:
            return self.rewards['banana'] - cost_to_banana_direct

def theta_grid(bins: int) -> np.ndarray:
    return np.linspace(0, 1, bins)

class PreferenceInference:
    """Infer farmer preference from observed behavior using continuous theta model."""
    def __init__(
        self,
        wizard_belief_p: float = 0.5,
        step_cost: float = 0.05,
        theta_bins: int = 11,
        base: float = 0.0,
        scale: float = 1.0,
        environment: FarmerGridWorld = None,
        temperature: float = 0.1
    ):
        self.p = wizard_belief_p
        self.env = environment or FarmerGridWorld()
        self.step_cost = step_cost
        self.theta_bins = theta_bins
        self.base = base
        self.scale = scale
        self.temperature = temperature
    
    def infer_most_likely_theta(self, trial_data: Dict[str, Any]) -> float:
        """Return the theta value with highest posterior probability."""
        dist = self.infer_preference_distribution(trial_data)
        return max(dist.items(), key=lambda x: x[1])[0]

    def infer_preference_distribution(self, trial_data: Dict[str, Any]) -> Dict[float, float]:
        """
        Bayesian preference inference using both initial and final decisions.
        """
        thetas = theta_grid(self.theta_bins)

        rock_initial = trial_data['rock_initial']
        observed_direction = trial_data['farmer_initial_direction']
        
        # Additional fields 
        wizard_action = trial_data['wizard_action']
        final_outcome = trial_data['final_outcome']
        
        if trial_data.get('farmer_final_direction'):
            final_direction = trial_data['farmer_final_direction']
        else:
            final_direction = 'right' if final_outcome == 'apple' else 'left' 

        likelihoods = {}
        
        for theta in thetas:
            farmer = FarmerAgent(
                theta=theta, 
                wizard_belief_p=self.p,
                step_cost=self.step_cost,
                base=self.base,
                scale=self.scale,
                environment=self.env
            )
            
            # Initial direction / choice
            eu_right = farmer.compute_expected_utility('apple', rock_initial)
            eu_left = farmer.compute_expected_utility('banana', rock_initial)

            # Softmax probability of choosing each direction
            p_right_initial = softmax_choice(eu_left, eu_right, self.temperature)
            initial_likelihood = p_right_initial if observed_direction == 'right' else (1.0 - p_right_initial)
            initial_likelihood = max(initial_likelihood, EPS)
            
            # Response to wizard
            final_rock_state = (wizard_action == 'place_rock') or \
                               (wizard_action != 'remove_rock' and rock_initial)
            
            # Farmer position after wizard action
            pos_after_initial = self.env.advance_n_steps(
                self.env.farmer_start,
                observed_direction,
                self.env.steps_before_wizard,
                rock_present=rock_initial
            )
            
            # Calculate utilities from this position
            # Left (banana) is always safe/direct from here
            cost_to_banana_direct = abs(self.env.banana_pos - pos_after_initial) * farmer.step_cost
            u_left = farmer.rewards['banana'] - cost_to_banana_direct

            # Right (apple) depends on rock
            cost_to_apple_direct = abs(self.env.apple_pos - pos_after_initial) * farmer.step_cost
            
            # Calculate redirect Cost (Right -> Rock -> Banana)
            # Distance from current -> Rock -> Banana
            cost_current_to_rock = abs((self.env.rock_pos - 1) - pos_after_initial) * farmer.step_cost
            cost_rock_to_banana = abs(self.env.banana_pos - (self.env.rock_pos - 1)) * farmer.step_cost
            cost_redirected = cost_current_to_rock + cost_rock_to_banana
            
            if final_rock_state:
                # Blocked: Right leads to banana via redirect
                # U(Right) = Reward(Banana) - Cost(Redirect)
                u_right = farmer.rewards['banana'] - cost_redirected
            else:
                # Clear: Right leads to apple
                # U(Right) = Reward(Apple) - Cost(Direct)
                u_right = farmer.rewards['apple'] - cost_to_apple_direct

            # Final direction likelihood - use softmax
            p_right_final = softmax_choice(u_left, u_right, self.temperature)
            final_dir_lik = p_right_final if final_direction == 'right' else (1.0 - p_right_final)
            final_dir_lik = max(final_dir_lik, EPS)

            likelihoods[theta] = initial_likelihood * final_dir_lik
            
        # Normalize
        total = sum(likelihoods.values()) + EPS
        posterior = {t: l/total for t, l in likelihoods.items()}
        return posterior


    def alignment_probability(
        self, 
        theta: float, 
        actual_outcome: str
    ) -> float:
        """
        Compute probability that actual outcome aligns with farmer's preference.
        
        This is the softmax probability that the farmer prefers `actual_outcome`
        given their preference theta.
        """
        rewards = rewards_from_theta(theta, self.base, self.scale)
        u_apple = rewards['apple']
        u_banana = rewards['banana']
        
        # Softmax probability of preferring apple vs banana
        p_apple = softmax_choice(u_banana, u_apple, self.temperature)
        
        if actual_outcome == 'apple':
            return p_apple
        else:
            return 1.0 - p_apple


def softmax_choice(u_left: float, u_right: float, temperature: float = 1.0) -> float:
    """
    Softmax probability of choosing right given utilities.
    
    P(right) = exp(u_right / T) / (exp(u_left / T) + exp(u_right / T))
    """
    # Subtract max for numerical stability
    max_u = max(u_left, u_right)
    exp_left = np.exp((u_left - max_u) / temperature)
    exp_right = np.exp((u_right - max_u) / temperature)
    
    p_right = exp_right / (exp_left + exp_right + EPS)
    return p_right