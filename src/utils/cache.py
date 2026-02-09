import json
import hashlib
from typing import Dict, Any, List


def hash_trial_data(trial_data: Dict[str, Any]) -> str:
    """Create a hash key for trial data for caching."""
    key_data = {
        'trial_id': trial_data.get('trial_id'),
        'farmer_action': trial_data.get('farmer_action'),
        'wizard_action': trial_data.get('wizard_action'),
        'rock_present': trial_data.get('rock_present'),
        'outcome': trial_data.get('outcome')
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


def hash_trial_set(possible_trials: List[Dict[str, Any]]) -> str:
    """Create a hash key for a set of possible trials."""
    trial_ids = sorted([trial.get('trial_id') for trial in possible_trials])
    key_str = json.dumps(trial_ids, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


def hash_parameters(params: Dict[str, Any]) -> str:
    """Create a hash key for parameter dictionary."""
    key_str = json.dumps(params, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


class SimpleCache:
    """A simple LRU cache with optional size limit."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = {}
        self.access_order = []

    def get(self, key: str, default=None):
        """Get item from cache."""
        if key in self.cache:
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return default

    def put(self, key: str, value: Any):
        """Put item in cache."""
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.max_size:
            lru_key = self.access_order.pop(0)
            del self.cache[lru_key]

        self.cache[key] = value
        self.access_order.append(key)

    def clear(self):
        """Clear all cached items."""
        self.cache.clear()
        self.access_order.clear()

    def __contains__(self, key: str) -> bool:
        return key in self.cache

    def size(self) -> int:
        return len(self.cache)
