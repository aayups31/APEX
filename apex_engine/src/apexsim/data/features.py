from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from apexsim.contracts import MODEL_INPUT_COLUMNS, TARGET_COLUMNS


@dataclass
class Standardizer:
    input_mean: np.ndarray
    input_std: np.ndarray
    target_mean: np.ndarray
    target_std: np.ndarray

    @classmethod
    def fit(cls, frame: pd.DataFrame) -> "Standardizer":
        x = frame[MODEL_INPUT_COLUMNS].to_numpy(np.float32)
        y = frame[TARGET_COLUMNS].to_numpy(np.float32)
        x_std = x.std(axis=0)
        y_std = y.std(axis=0)
        return cls(
            input_mean=x.mean(axis=0),
            input_std=np.where(x_std < 1e-6, 1.0, x_std),
            target_mean=y.mean(axis=0),
            target_std=np.where(y_std < 1e-6, 1.0, y_std),
        )

    def transform_inputs(self, values: np.ndarray) -> np.ndarray:
        return (values - self.input_mean) / self.input_std

    def transform_targets(self, values: np.ndarray) -> np.ndarray:
        return (values - self.target_mean) / self.target_std

    def inverse_targets(self, values: np.ndarray) -> np.ndarray:
        return values * self.target_std + self.target_mean

    def to_dict(self) -> dict[str, list[float]]:
        return {
            "input_mean": self.input_mean.tolist(),
            "input_std": self.input_std.tolist(),
            "target_mean": self.target_mean.tolist(),
            "target_std": self.target_std.tolist(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, list[float]]) -> "Standardizer":
        return cls(**{key: np.asarray(value, dtype=np.float32) for key, value in payload.items()})
