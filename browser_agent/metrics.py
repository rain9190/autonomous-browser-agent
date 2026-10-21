"""Shared completion policy for the current reward-normalized MiniWoB set."""
import math
from numbers import Real

COMPLETION_METRIC = "terminal_full_credit_reward_1_v1"


def valid_reward(reward):
    return isinstance(reward, Real) and not isinstance(reward, bool) and math.isfinite(reward)


def positive_reward_terminal(reward, terminated, truncated, error=False):
    return bool(valid_reward(reward) and reward > 0 and terminated is True
                and truncated is False and not error)


def full_credit_success(reward, terminated, truncated, error=False):
    return bool(positive_reward_terminal(reward, terminated, truncated, error)
                and math.isclose(float(reward), 1.0, rel_tol=0.0, abs_tol=1e-9))
