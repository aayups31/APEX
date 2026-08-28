"""Reproducible tyre-energy forecasting protocol from Todd et al. (2025)."""
from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

TARGET_COLUMNS = tuple(
    f"tyre_energy_{name}_kj"
    for name in ("front_left", "front_right", "rear_left", "rear_right")
)


class TrackStateEncoding(str, Enum):
    EXCLUDE = "exclude"
    ONE_HOT = "one_hot"
    ORDINAL = "ordinal"
    GREEN_ONLY = "green_only"


@dataclass(frozen=True)
class WindowedTyreDataset:
    x: np.ndarray  # [N, T, F]
    y: np.ndarray  # [N, 4]
    feature_names: tuple[str, ...]
    event_ids: np.ndarray
    row_indices: np.ndarray

    def __post_init__(self) -> None:
        if self.x.ndim != 3 or self.y.ndim != 2 or self.y.shape[1] != 4:
            raise ValueError("Expected x=[N,T,F] and y=[N,4]")
        if len(self.x) != len(self.y) or len(self.x) != len(self.event_ids):
            raise ValueError("Window arrays must have equal first dimension")


@dataclass(frozen=True)
class EventSplit:
    train_events: tuple[str, ...]
    validation_events: tuple[str, ...]
    test_events: tuple[str, ...]

    def validate(self) -> None:
        train, val, test = map(set, (self.train_events, self.validation_events, self.test_events))
        if train & val or train & test or val & test:
            raise ValueError("Event split leakage detected")


def _encode_track_state(frame: pd.DataFrame, encoding: TrackStateEncoding) -> tuple[pd.DataFrame, list[str]]:
    out = frame.copy()
    if "track_state" not in out.columns:
        return out, []
    state = out["track_state"].astype(str).str.upper()
    if encoding == TrackStateEncoding.GREEN_ONLY:
        out = out[state.eq("GREEN")].copy()
        out = out.drop(columns=["track_state"])
        return out, []
    if encoding == TrackStateEncoding.EXCLUDE:
        return out.drop(columns=["track_state"]), []
    if encoding == TrackStateEncoding.ORDINAL:
        order = {"GREEN": 0.0, "YELLOW": 1.0, "VSC": 2.0, "SAFETY_CAR": 3.0, "RED": 4.0}
        out["track_state_ordinal"] = state.map(order).fillna(-1.0)
        out = out.drop(columns=["track_state"])
        return out, ["track_state_ordinal"]
    dummies = pd.get_dummies(state, prefix="track_state", dtype=float)
    out = pd.concat([out.drop(columns=["track_state"]), dummies], axis=1)
    return out, list(dummies.columns)


def build_tyre_energy_windows(
    frame: pd.DataFrame,
    feature_columns: Sequence[str],
    event_column: str = "event_id",
    sequence_column: str = "time_s",
    window: int = 100,
    encoding: TrackStateEncoding = TrackStateEncoding.ONE_HOT,
) -> WindowedTyreDataset:
    """Create past-covariate -> immediate next four-energy windows.

    Windows never cross event boundaries. Target history is intentionally not
    included unless the caller explicitly lists it in ``feature_columns``.
    """
    if window <= 0:
        raise ValueError("window must be positive")
    required = {event_column, sequence_column, *feature_columns, *TARGET_COLUMNS}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Missing tyre forecasting columns: {missing}")

    encoded, added = _encode_track_state(frame, encoding)
    features = [c for c in feature_columns if c != "track_state"] + added
    x_rows: list[np.ndarray] = []
    y_rows: list[np.ndarray] = []
    event_rows: list[str] = []
    indices: list[int] = []

    for event, group in encoded.groupby(event_column, sort=False):
        group = group.sort_values(sequence_column, kind="stable")
        values = group[features].astype(float).to_numpy()
        targets = group[list(TARGET_COLUMNS)].astype(float).to_numpy()
        original_indices = group.index.to_numpy()
        for target_i in range(window, len(group)):
            x_rows.append(values[target_i - window:target_i])
            y_rows.append(targets[target_i])
            event_rows.append(str(event))
            indices.append(int(original_indices[target_i]))
    x = np.stack(x_rows) if x_rows else np.empty((0, window, len(features)), dtype=np.float32)
    y = np.stack(y_rows) if y_rows else np.empty((0, 4), dtype=np.float32)
    return WindowedTyreDataset(
        x=x.astype(np.float32),
        y=y.astype(np.float32),
        feature_names=tuple(features),
        event_ids=np.asarray(event_rows, dtype=object),
        row_indices=np.asarray(indices, dtype=np.int64),
    )


def make_event_split(event_ids: Iterable[str], train_fraction: float = 0.60, validation_fraction: float = 0.20, seed: int = 42) -> EventSplit:
    events = np.asarray(sorted(set(map(str, event_ids))), dtype=object)
    if len(events) < 3:
        raise ValueError("At least three events are required for train/validation/test splitting")
    rng = np.random.default_rng(seed)
    rng.shuffle(events)
    n_train = max(1, round(len(events) * train_fraction))
    n_val = max(1, round(len(events) * validation_fraction))
    if n_train + n_val >= len(events):
        n_train = len(events) - 2
        n_val = 1
    split = EventSplit(
        train_events=tuple(map(str, events[:n_train])),
        validation_events=tuple(map(str, events[n_train:n_train + n_val])),
        test_events=tuple(map(str, events[n_train + n_val:])),
    )
    split.validate()
    return split


def subset_by_events(dataset: WindowedTyreDataset, events: Sequence[str]) -> WindowedTyreDataset:
    mask = np.isin(dataset.event_ids, np.asarray(events, dtype=object))
    return WindowedTyreDataset(
        x=dataset.x[mask],
        y=dataset.y[mask],
        feature_names=dataset.feature_names,
        event_ids=dataset.event_ids[mask],
        row_indices=dataset.row_indices[mask],
    )


class RidgeTyreEnergyForecaster:
    """Strong transparent baseline; flattens the complete covariate history."""

    def __init__(self, alpha: float = 1.0) -> None:
        self.model = Ridge(alpha=alpha)
        self.input_shape: tuple[int, int] | None = None

    def fit(self, x: np.ndarray, y: np.ndarray) -> RidgeTyreEnergyForecaster:
        self.input_shape = (x.shape[1], x.shape[2])
        self.model.fit(x.reshape(len(x), -1), y)
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        if self.input_shape is None:
            raise RuntimeError("Model is not fitted")
        return self.model.predict(x.reshape(len(x), -1))


class GRUTyreEnergyForecaster(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 128, layers: int = 2, dropout: float = 0.1) -> None:
        super().__init__()
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=layers,
            batch_first=True,
            dropout=dropout if layers > 1 else 0.0,
        )
        self.head = nn.Sequential(nn.LayerNorm(hidden_size), nn.Linear(hidden_size, 4), nn.Softplus())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        sequence, _ = self.gru(x)
        return self.head(sequence[:, -1])


def train_gru_forecaster(
    model: GRUTyreEnergyForecaster,
    train: WindowedTyreDataset,
    validation: WindowedTyreDataset | None = None,
    epochs: int = 5,
    batch_size: int = 128,
    learning_rate: float = 1e-3,
    gradient_clip_norm: float = 1.0,
    device: str = "cpu",
) -> list[dict[str, float]]:
    if len(train.x) == 0:
        raise ValueError("Training dataset is empty")
    model.to(device)
    loader = DataLoader(
        TensorDataset(torch.from_numpy(train.x), torch.from_numpy(train.y)),
        batch_size=batch_size,
        shuffle=True,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    history = []
    for epoch in range(epochs):
        model.train()
        total = 0.0
        count = 0
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad(set_to_none=True)
            pred = model(xb)
            loss = torch.mean((pred - yb) ** 2)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), gradient_clip_norm)
            optimizer.step()
            total += float(loss.detach()) * len(xb)
            count += len(xb)
        row = {"epoch": float(epoch + 1), "train_rmse": float(np.sqrt(total / max(count, 1)))}
        if validation is not None and len(validation.x):
            prediction = predict_torch(model, validation.x, batch_size=batch_size, device=device)
            row["validation_rmse"] = rmse(validation.y, prediction)
        history.append(row)
    return history


def predict_torch(model: nn.Module, x: np.ndarray, batch_size: int = 512, device: str = "cpu") -> np.ndarray:
    model.eval().to(device)
    outputs = []
    with torch.no_grad():
        for start in range(0, len(x), batch_size):
            xb = torch.from_numpy(x[start:start + batch_size]).to(device)
            outputs.append(model(xb).cpu().numpy())
    return np.concatenate(outputs) if outputs else np.empty((0, 4))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def smape(y_true: np.ndarray, y_pred: np.ndarray, epsilon: float = 1e-6) -> float:
    denominator = np.abs(y_true) + np.abs(y_pred) + epsilon
    return float(np.mean(200.0 * np.abs(y_pred - y_true) / denominator))


def temporal_permutation_importance(
    predictor: Callable[[np.ndarray], np.ndarray],
    x: np.ndarray,
    y: np.ndarray,
    feature_names: Sequence[str],
    seed: int = 42,
) -> pd.DataFrame:
    """Model-agnostic temporal perturbation importance inspired by TIME."""
    baseline = rmse(y, predictor(x))
    rng = np.random.default_rng(seed)
    rows = []
    for feature_i, name in enumerate(feature_names):
        perturbed = x.copy()
        flat = perturbed[:, :, feature_i].reshape(-1)
        rng.shuffle(flat)
        perturbed[:, :, feature_i] = flat.reshape(perturbed.shape[0], perturbed.shape[1])
        score = rmse(y, predictor(perturbed))
        rows.append({"feature": name, "baseline_rmse": baseline, "perturbed_rmse": score, "importance": score - baseline})
    return pd.DataFrame(rows).sort_values("importance", ascending=False).reset_index(drop=True)


def counterfactual_intervention(
    predictor: Callable[[np.ndarray], np.ndarray],
    x: np.ndarray,
    feature_index: int,
    replacement: float | np.ndarray,
) -> dict[str, np.ndarray]:
    factual = predictor(x)
    counterfactual_x = x.copy()
    counterfactual_x[:, :, feature_index] = replacement
    counterfactual = predictor(counterfactual_x)
    return {"factual": factual, "counterfactual": counterfactual, "delta": counterfactual - factual}
