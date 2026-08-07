from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from apexsim.contracts import TARGET_COLUMNS
from apexsim.data.features import Standardizer
from apexsim.models.rssm import RSSMWorldModel


def evaluate_world_model(
    model: nn.Module,
    loader: DataLoader,
    standardizer: Standardizer,
    output_path: str | Path | None = None,
    device: str = "cpu",
) -> dict:
    model.eval()
    model.to(device)
    predictions: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    with torch.no_grad():
        for batch in loader:
            history = batch["history"].to(device)
            future_inputs = batch["future_inputs"].to(device)
            if isinstance(model, RSSMWorldModel):
                predicted, _ = model(history, future_inputs, future_targets=None)
            else:
                predicted = model(history, future_inputs)
            predictions.append(predicted.cpu().numpy())
            targets.append(batch["future_targets"].numpy())
    pred_z = np.concatenate(predictions, axis=0)
    target_z = np.concatenate(targets, axis=0)
    pred = standardizer.inverse_targets(pred_z)
    target = standardizer.inverse_targets(target_z)
    error = pred - target
    horizon_rmse = np.sqrt(np.mean(error**2, axis=(0, 2)))
    horizon_mae = np.mean(np.abs(error), axis=(0, 2))
    per_feature = {}
    for index, feature in enumerate(TARGET_COLUMNS):
        per_feature[feature] = {
            "mae": float(np.mean(np.abs(error[..., index]))),
            "rmse": float(np.sqrt(np.mean(error[..., index] ** 2))),
        }
    physical = {
        "negative_speed_rate": float(np.mean(pred[..., 0] < 0)),
        "extreme_speed_rate": float(np.mean(pred[..., 0] > 120)),
        "progress_unit_circle_error": float(
            np.mean(np.abs(pred[..., 2] ** 2 + pred[..., 3] ** 2 - 1.0))
        ),
    }
    metrics = {
        "overall_mae": float(np.mean(np.abs(error))),
        "overall_rmse": float(np.sqrt(np.mean(error**2))),
        "speed_mae_mps": per_feature["speed_mps"]["mae"],
        "speed_rmse_mps": per_feature["speed_mps"]["rmse"],
        "per_feature": per_feature,
        "horizon_mae": horizon_mae.tolist(),
        "horizon_rmse": horizon_rmse.tolist(),
        "physical_violations": physical,
        "samples": int(pred.shape[0]),
    }
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
