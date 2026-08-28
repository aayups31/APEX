from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

from apexsim.contracts import MODEL_INPUT_COLUMNS
from apexsim.data.features import Standardizer
from apexsim.models.rssm import RSSMWorldModel


@dataclass(frozen=True)
class Scenario:
    throttle_scale: float = 1.0
    brake_scale: float = 1.0
    grip_multiplier: float = 1.0
    rain_delta: float = 0.0
    tyre_degradation_multiplier: float = 1.0


def apply_scenario(future_inputs_raw: np.ndarray, scenario: Scenario) -> np.ndarray:
    modified = future_inputs_raw.copy()
    index = {name: i for i, name in enumerate(MODEL_INPUT_COLUMNS)}
    modified[:, index["throttle"]] = np.clip(
        modified[:, index["throttle"]] * scenario.throttle_scale, 0.0, 1.0
    )
    modified[:, index["brake"]] = np.clip(
        modified[:, index["brake"]] * scenario.brake_scale, 0.0, 1.0
    )
    modified[:, index["grip_level"]] = np.clip(
        modified[:, index["grip_level"]] * scenario.grip_multiplier, 0.2, 1.5
    )
    modified[:, index["rainfall"]] = np.clip(
        modified[:, index["rainfall"]] + scenario.rain_delta, 0.0, 1.0
    )
    tyre_index = index["tyre_age_laps"]
    base_age = modified[0, tyre_index]
    modified[:, tyre_index] = base_age + (
        modified[:, tyre_index] - base_age
    ) * scenario.tyre_degradation_multiplier
    return modified


def rollout(
    model: nn.Module,
    history_raw: np.ndarray,
    future_inputs_raw: np.ndarray,
    standardizer: Standardizer,
    scenario: Scenario,
    device: str = "cpu",
) -> np.ndarray:
    model.eval().to(device)
    future_modified = apply_scenario(future_inputs_raw, scenario)
    history = torch.from_numpy(
        standardizer.transform_inputs(history_raw).astype(np.float32)[None, ...]
    ).to(device)
    future = torch.from_numpy(
        standardizer.transform_inputs(future_modified).astype(np.float32)[None, ...]
    ).to(device)
    with torch.no_grad():
        if isinstance(model, RSSMWorldModel):
            prediction_z, _ = model(history, future, future_targets=None)
        else:
            prediction_z = model(history, future)
    return standardizer.inverse_targets(prediction_z.cpu().numpy()[0])
