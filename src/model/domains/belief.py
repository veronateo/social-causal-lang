from typing import Dict, Any, Optional, Literal
from .base import Domain, WorldState
import random
import math
from ..config import ModelConfig

class BeliefDomain(Domain):
    """Belief domain: gold/rocks scenarios with wizard signs.
    Note: This domain uses only ``temperature`` and ``alignment_mode`` from
    the supplied ModelConfig. ``step_cost`` is accepted but not used.
    """
    def __init__(
        self,
        config: ModelConfig = None,
        temperature: float = 0.1,
        alignment_mode: Literal['hard', 'soft'] = 'soft'
    ):
        super().__init__()

        if config is not None:
            temperature = config.temperature
            alignment_mode = config.alignment_mode

        self.temperature = temperature
        self.alignment_mode = alignment_mode
    
    @property
    def name(self) -> str:
        return "belief"

    def normalize_trial(self, trial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure trial data has standard fields."""
        return trial_data

    def _parse_scenario(self, trial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse structured state from scenario description."""
        desc = trial_data.get('scenario_description', '').lower()
        
        # Initial Belief
        if 'no initial belief' in desc or 'no belief' in desc:
            initial_belief = 'none'
        elif 'true initial belief' in desc or 'true belief' in desc:
            initial_belief = 'true'
        elif 'false initial belief' in desc or 'false belief' in desc:
            initial_belief = 'false'
        else:
            initial_belief = 'none'
            
        # Wizard Action
        if 'wizard shows true sign' in desc or 'true sign' in desc:
            wizard_action = 'true_sign'
        elif 'wizard shows false sign' in desc or 'false sign' in desc:
            wizard_action = 'false_sign'
        elif 'wizard does nothing' in desc:
            wizard_action = 'nothing'
        else:
             wizard_action = 'nothing'
             
        # Farmer reaction
        if 'ignores' in desc:
            farmer_trust = 'ignores'
        else:
            farmer_trust = 'listens'

        # Guess (only relevant if no initial belief)
        latent_guess = None
        
        should_infer_guess = (initial_belief == 'none') and (
            wizard_action == 'nothing' or farmer_trust == 'ignores'
        )
        
        if 'guesses correctly' in desc:
            latent_guess = 'correct'
        elif 'guesses incorrectly' in desc:
            latent_guess = 'incorrect'
        elif should_infer_guess:
            if 'gets gold' in desc:
                latent_guess = 'correct'
            elif 'gets rocks' in desc:
                latent_guess = 'incorrect'

        return {
            'initial_belief': initial_belief,
            'wizard_action': wizard_action,
            'farmer_trust': farmer_trust,
            'latent_guess': latent_guess,
            'actual_outcome_val': 1.0 if 'gets gold' in desc else 0.0
        }

    def _softmax_prob(self, u_target: float, u_other: float) -> float:
        """Probability of choosing target given utilities and temperature."""
        if self.temperature < 1e-10:
            return 1.0 if u_target > u_other else 0.0
            
        # P(target) = exp(u_t/T) / (exp(u_t/T) + exp(u_o/T))
        #           = 1 / (1 + exp((u_o - u_t)/T))
        try:
            return 1.0 / (1.0 + math.exp((u_other - u_target) / self.temperature))
        except OverflowError:
            return 0.0 if u_other > u_target else 1.0

    def _simulate_outcome_prob(self, initial_belief: str, wizard_action: str, farmer_trust: str, latent_guess: Optional[str] = None) -> float:
        """
        Return P(gold) given state.
        """
        
        def get_belief_prob():
            # If agent believes X leads to Gold, they assign U(X)=1, U(not-X)=0
            # Choose X with p = softmax(1, 0)
            p_choose_perceived_best = self._softmax_prob(1.0, 0.0)
            
            if initial_belief == 'true': 
                # Guess is correct (gold)
                return p_choose_perceived_best
                
            if initial_belief == 'false': 
                # Guess is wrong (rocks)
                return 1.0 - p_choose_perceived_best
                
            # No belief -> guess
            if latent_guess == 'correct': 
                return p_choose_perceived_best
            if latent_guess == 'incorrect': 
                return 1.0 - p_choose_perceived_best
                
            return 0.5 
        
        # If wizard does nothing, farmer acts on belief/guess
        if wizard_action == 'nothing':
            return get_belief_prob()
            
        # If farmer ignores wizard, act on belief/guess
        if farmer_trust == 'ignores':
            return get_belief_prob()
            
        # If farmer listens and wizard acts
        if farmer_trust == 'listens':
            p_choose_sign = self._softmax_prob(1.0, 0.0)
            
            if wizard_action == 'true_sign': 
                return p_choose_sign
            if wizard_action == 'false_sign': 
                return 1.0 - p_choose_sign
            
        return 0.5 # Fallback

    def compute_dependence(self, state: Dict[str, Any]) -> Dict[str, float]:
        """
        Compute dependence variants by simulating counterfactual wizard actions.
        """
        initial_belief = state['initial_belief']
        farmer_trust = state['farmer_trust']
        actual_val = state['actual_outcome_val']
        latent_guess = state['latent_guess']
        
        possible_actions = ['nothing', 'true_sign', 'false_sign']
        
        action_diff_probs = {}
        
        for action in possible_actions:
            # Simulate P(gold) in counterfactual
            p_gold_cf = self._simulate_outcome_prob(initial_belief, action, farmer_trust, latent_guess)
            
            # P(Outcome != Actual)
            if actual_val == 1.0:
                p_diff = 1.0 - p_gold_cf
            else:
                p_diff = p_gold_cf
                
            action_diff_probs[action] = p_diff
            
        nec_control = action_diff_probs.get('nothing', 0.0)
        nec_max = max(action_diff_probs.values())
        
        # Average dependence (alternatives only)
        actual_action = state['wizard_action']
        alternatives = [p for a, p in action_diff_probs.items() if a != actual_action]
        
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
        # Parse state
        state = self._parse_scenario(trial_data)
        
        # Actual outcome
        actual_val = state['actual_outcome_val']
        actual_outcome = 'gold' if actual_val == 1.0 else 'rocks'
        
        # Expected outcome (inertial / control)
        # What would happen if wizard did nothing?
        inertial_prob = self._simulate_outcome_prob(
            state['initial_belief'], 
            'nothing', 
            state['farmer_trust'],
            state['latent_guess']
        )

        if inertial_prob > 0.5:
            expected_outcome = 'gold'
        elif inertial_prob < 0.5:
            expected_outcome = 'rocks'
        else:
            expected_outcome = 'uncertain'
        
        # V — Value alignment: did outcome match farmer's goal (prefer gold)?
        if self.alignment_mode == 'hard':
            aligned = actual_val
        else:
            # Soft alignment: P(choice | preference) via softmax
            p_gold = self._softmax_prob(1.0, 0.0)
            aligned = p_gold if actual_val == 1.0 else 1.0 - p_gold
        
        # A — Wizard acted?
        wizard_action = state['wizard_action']
        acted = 1.0 if wizard_action != 'nothing' else 0.0
        
        # C — Counterfactual dependence (avg over alternative actions)
        nec_stats = self.compute_dependence(state)
        
        preferred_outcome = 'gold'

        return WorldState(
            dependence=nec_stats['avg'],
            acted=acted,
            aligned=aligned,
            actual_outcome=actual_outcome,
            expected_outcome=expected_outcome,
            preferred_outcome=preferred_outcome,
            debug_dependence_info=nec_stats.get('debug_info'),
            debug_posterior={'initial_belief': state.get('initial_belief'), 'trust': state.get('farmer_trust')}
        )
