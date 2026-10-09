"""Causal, atomic synthetic interventions; doses are priors, not fitted events."""
from dataclasses import replace
from math import isfinite

from apexsim.research.fienia_strategy import PaperStrategyState
from apexsim.research.sac_env import StrategyLearningEnv


def apply_wear_shock(env: StrategyLearningEnv, dose: float) -> PaperStrategyState:
    """Change only current wear before a decision, rejecting invalid events atomically."""
    state = env.state
    if env.model.is_done(state):
        raise ValueError("Cannot disturb a terminal state")
    if isinstance(dose, bool) or not isinstance(dose, (int, float)) or not isfinite(dose) or dose < 0:
        raise ValueError("Wear dose must be finite and nonnegative")
    candidate = replace(state, tyre_wear=state.tyre_wear + dose)
    if not 0 <= candidate.tyre_wear <= 1.25:
        raise ValueError("Wear shock exceeds the unclipped model domain")
    env.model.validate_state(candidate)
    env.base.state = candidate
    return candidate
