from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.multioutput import MultiOutputRegressor


class PersistenceBaseline:
    """Predict that the next state is identical to the current state."""

    def predict(self, current_state: np.ndarray, horizon: int) -> np.ndarray:
        return np.repeat(current_state[None, :], horizon, axis=0)


class LinearTransitionBaseline:
    """Ridge regression for one-step state transitions."""

    def __init__(self, alpha: float = 1.0) -> None:
        self.model = MultiOutputRegressor(Ridge(alpha=alpha))

    def fit(self, inputs: np.ndarray, next_states: np.ndarray) -> "LinearTransitionBaseline":
        self.model.fit(inputs, next_states)
        return self

    def predict(self, inputs: np.ndarray) -> np.ndarray:
        return self.model.predict(inputs)
