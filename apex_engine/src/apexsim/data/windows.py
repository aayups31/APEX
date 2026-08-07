from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from apexsim.contracts import MODEL_INPUT_COLUMNS, STATE_COLUMNS, TARGET_COLUMNS
from apexsim.data.features import Standardizer


@dataclass(frozen=True)
class WindowIndex:
    session_id: str
    start: int
    stop: int


def split_sessions(
    frame: pd.DataFrame,
    train_fraction: float,
    val_fraction: float,
    seed: int,
) -> dict[str, list[str]]:
    sessions = sorted(frame.session_id.unique().tolist())
    rng = np.random.default_rng(seed)
    rng.shuffle(sessions)
    n = len(sessions)
    n_train = max(1, int(round(n * train_fraction)))
    n_val = max(1, int(round(n * val_fraction)))
    if n_train + n_val >= n:
        n_val = 1
        n_train = max(1, n - 2)
    return {
        "train": sessions[:n_train],
        "val": sessions[n_train : n_train + n_val],
        "test": sessions[n_train + n_val :],
    }


class TelemetryWindowDataset(Dataset):
    """Returns histories and next-state sequences without crossing session boundaries."""

    def __init__(
        self,
        frame: pd.DataFrame,
        session_ids: list[str],
        sequence_length: int,
        prediction_horizon: int,
        standardizer: Standardizer,
        max_windows: int | None = None,
    ) -> None:
        self.sequence_length = sequence_length
        self.prediction_horizon = prediction_horizon
        self.standardizer = standardizer
        self.sessions: dict[str, pd.DataFrame] = {}
        self.indices: list[WindowIndex] = []
        total = sequence_length + prediction_horizon
        for session_id in session_ids:
            session = (
                frame[frame.session_id == session_id]
                .sort_values("timestamp_s")
                .reset_index(drop=True)
            )
            self.sessions[session_id] = session
            for start in range(0, len(session) - total + 1):
                self.indices.append(WindowIndex(session_id, start, start + total))
        if max_windows is not None and len(self.indices) > max_windows:
            positions = np.linspace(0, len(self.indices) - 1, max_windows).astype(int)
            self.indices = [self.indices[i] for i in positions]

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor | str]:
        item = self.indices[index]
        window = self.sessions[item.session_id].iloc[item.start : item.stop]
        history = window.iloc[: self.sequence_length]
        future = window.iloc[self.sequence_length :]
        x_history = history[MODEL_INPUT_COLUMNS].to_numpy(np.float32)
        x_future = future[MODEL_INPUT_COLUMNS].to_numpy(np.float32)
        y_future = future[TARGET_COLUMNS].to_numpy(np.float32)
        state_history = history[STATE_COLUMNS].to_numpy(np.float32)
        return {
            "history": torch.from_numpy(self.standardizer.transform_inputs(x_history).astype(np.float32)),
            "future_inputs": torch.from_numpy(self.standardizer.transform_inputs(x_future).astype(np.float32)),
            "future_targets": torch.from_numpy(self.standardizer.transform_targets(y_future).astype(np.float32)),
            "state_history": torch.from_numpy(self.standardizer.transform_targets(state_history).astype(np.float32)),
            "session_id": item.session_id,
        }
