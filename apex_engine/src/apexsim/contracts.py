from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pandas as pd

# Canonical columns are deliberately independent of FastF1, OpenF1, and F1 25.
# Every source adapter must translate into this stable contract.
IDENTITY_COLUMNS: Final[list[str]] = [
    "session_id",
    "source",
    "track_id",
    "driver_id",
    "timestamp_s",
    "lap_number",
]

STATE_COLUMNS: Final[list[str]] = [
    "speed_mps",
    "acceleration_mps2",
    "track_progress_sin",
    "track_progress_cos",
    "tyre_age_laps",
]

ACTION_COLUMNS: Final[list[str]] = [
    "throttle",
    "brake",
    "gear_norm",
    "drs",
    "steering_proxy",
]

CONTEXT_COLUMNS: Final[list[str]] = [
    "curvature",
    "air_temp_c",
    "track_temp_c",
    "rainfall",
    "wind_speed_mps",
    "grip_level",
]

AUX_COLUMNS: Final[list[str]] = [
    "lap_distance_m",
    "x_m",
    "y_m",
    "rpm",
    "gear",
    "compound_id",
    "is_pit",
    "safety_car",
]

REQUIRED_COLUMNS: Final[list[str]] = (
    IDENTITY_COLUMNS + STATE_COLUMNS + ACTION_COLUMNS + CONTEXT_COLUMNS + AUX_COLUMNS
)

MODEL_INPUT_COLUMNS: Final[list[str]] = STATE_COLUMNS + ACTION_COLUMNS + CONTEXT_COLUMNS
TARGET_COLUMNS: Final[list[str]] = STATE_COLUMNS


@dataclass(frozen=True)
class ContractReport:
    rows: int
    sessions: int
    drivers: int
    tracks: int
    null_cells: int
    duplicate_frames: int
    out_of_range_cells: int
    passed: bool

    def to_dict(self) -> dict[str, int | bool]:
        return self.__dict__.copy()


def assert_canonical_frame(frame: pd.DataFrame) -> None:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Canonical frame is missing columns: {missing}")
