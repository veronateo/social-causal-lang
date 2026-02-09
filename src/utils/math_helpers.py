import math
import numpy as np
from scipy.special import softmax, expit


def sigmoid(x):
    """Numerically stable sigmoid function."""
    x = max(min(x, 700), -700)
    if x >= 0:
        exp_neg_x = math.exp(-x)
        return 1 / (1 + exp_neg_x)
    else:
        exp_x = math.exp(x)
        return exp_x / (1 + exp_x)


def sigmoid_vec(x):
    """Vectorized sigmoid — handles scalars, lists, and arrays."""
    if isinstance(x, (list, np.ndarray)):
        return expit(np.array(x))
    else:
        return sigmoid(x)


def softmax_vec(x, axis=-1):
    """Vectorized softmax wrapper."""
    return softmax(np.array(x), axis=axis)


def exp(x, max_exp=700):
    """Exponential with overflow protection."""
    return math.exp(max(min(x, max_exp), -max_exp))
