import numpy as np

def rewards_from_theta(theta: float, base: float, scale: float):
    return {
        'apple': base + theta * scale,
        'banana': base + (1 - theta) * scale
    }

class FarmerGridWorld:
    """Original Grid world environment logic."""
    def __init__(self, grid_size=19):
        self.states = list(range(grid_size))
        self.farmer_start = 9
        self.apple_pos = 18
        self.banana_pos = 0
        self.rock_pos = 14
        self.steps_before_wizard = 4
        
    def transition(self, state, action, rock_present=False):
        next_state = state + (1 if action == 'right' else -1)
        if rock_present and next_state == self.rock_pos:
            return state  # Blocked by rock, stay in current state
        return np.clip(next_state, 0, len(self.states)-1)
    
    def advance_n_steps(self, start_state, action, n, rock_present=False):
        s = start_state
        for _ in range(n):
            s = self.transition(s, action, rock_present=rock_present)
            if s in [self.apple_pos, self.banana_pos]:
                break
        return s
