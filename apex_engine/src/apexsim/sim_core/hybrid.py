from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


class ResidualModel(Protocol):
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Return residual corrections [delta_speed, delta_tyre_health, delta_fuel]."""


@dataclass
class HybridCorrection:
    max_speed_delta_mps: float = 4.0
    max_health_delta: float = 0.01
    max_fuel_delta_kg: float = 0.02

    def apply(self, physics_state: np.ndarray, residual: np.ndarray) -> np.ndarray:
        limits = np.array(
            [self.max_speed_delta_mps, self.max_health_delta, self.max_fuel_delta_kg],
            dtype=float,
        )
        return physics_state + np.clip(residual, -limits, limits)


class NoOpResidualModel:
    def predict(self, features: np.ndarray) -> np.ndarray:
        batch = 1 if features.ndim == 1 else len(features)
        output = np.zeros((batch, 3), dtype=float)
        return output[0] if features.ndim == 1 else output
