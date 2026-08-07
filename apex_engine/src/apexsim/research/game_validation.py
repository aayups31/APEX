"""Contracts for validating paper-derived models against future F1 game telemetry.

This module deliberately contains no game-specific packet parser.  It defines the
stable, source-independent evidence table that a future F1 25/26 UDP adapter must
produce.  Paper replications and the APEX engine are compared only after both are
aligned to this contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


GAME_REQUIRED_COLUMNS = (
    "session_id",
    "lap",
    "time_s",
    "distance_m",
    "speed_mps",
    "throttle",
    "brake",
    "steering",
    "gear",
    "engine_rpm",
    "fuel_kg",
    "ers_store_mj",
    "ers_deploy_mj_s",
    "tyre_compound",
    "tyre_age_laps",
    "tyre_temp_fl_c",
    "tyre_temp_fr_c",
    "tyre_temp_rl_c",
    "tyre_temp_rr_c",
    "surface_type",
    "track_state",
    "in_pit",
)


@dataclass(frozen=True)
class GameEvidenceReport:
    rows: int
    sessions: int
    laps: int
    passed: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class AlignedComparison:
    frame: pd.DataFrame
    coverage: float
    median_time_error_s: float


def validate_game_evidence(frame: pd.DataFrame, *, strict: bool = True) -> GameEvidenceReport:
    """Validate the future game-derived canonical evidence table.

    Strict mode enforces ranges needed for scientific comparison.  It does not
    assert that game telemetry equals real-car telemetry; game evidence remains a
    controlled simulator-domain validation source.
    """
    errors: list[str] = []
    warnings: list[str] = []
    missing = [column for column in GAME_REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        errors.append(f"missing columns: {missing}")
        return GameEvidenceReport(len(frame), 0, 0, False, tuple(errors), tuple(warnings))

    if frame.empty:
        errors.append("evidence table is empty")
        return GameEvidenceReport(0, 0, 0, False, tuple(errors), tuple(warnings))

    numeric = [
        "lap", "time_s", "distance_m", "speed_mps", "throttle", "brake", "steering",
        "gear", "engine_rpm", "fuel_kg", "ers_store_mj", "ers_deploy_mj_s",
        "tyre_age_laps", "tyre_temp_fl_c", "tyre_temp_fr_c", "tyre_temp_rl_c", "tyre_temp_rr_c",
    ]
    for column in numeric:
        if not np.isfinite(pd.to_numeric(frame[column], errors="coerce")).all():
            errors.append(f"{column} contains missing or non-finite values")

    bounds = {
        "speed_mps": (0.0, 120.0),
        "throttle": (0.0, 1.0),
        "brake": (0.0, 1.0),
        "steering": (-1.0, 1.0),
        "gear": (0.0, 8.0),
        "fuel_kg": (0.0, 120.0),
        "ers_store_mj": (0.0, 20.0),
        "tyre_age_laps": (0.0, 100.0),
    }
    for column, (lower, upper) in bounds.items():
        values = pd.to_numeric(frame[column], errors="coerce")
        bad = ((values < lower) | (values > upper)).sum()
        if bad:
            message = f"{column}: {int(bad)} rows outside [{lower}, {upper}]"
            (errors if strict else warnings).append(message)

    ordered = frame.sort_values(["session_id", "lap", "time_s"])
    for (session_id, lap), group in ordered.groupby(["session_id", "lap"], sort=False):
        if (np.diff(group["time_s"].to_numpy(dtype=float)) <= 0).any():
            errors.append(f"non-increasing time in session={session_id}, lap={lap}")
        if (np.diff(group["distance_m"].to_numpy(dtype=float)) < -5.0).any():
            warnings.append(f"distance resets or reverses in session={session_id}, lap={lap}")

    sample_periods = ordered.groupby(["session_id", "lap"])["time_s"].apply(
        lambda x: float(np.median(np.diff(x))) if len(x) > 1 else np.nan
    )
    finite_periods = sample_periods[np.isfinite(sample_periods)]
    if len(finite_periods) and finite_periods.max() / max(finite_periods.min(), 1e-9) > 1.25:
        warnings.append("sampling period varies by more than 25%; resample before model comparison")

    return GameEvidenceReport(
        rows=len(frame),
        sessions=int(frame["session_id"].nunique()),
        laps=int(frame[["session_id", "lap"]].drop_duplicates().shape[0]),
        passed=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def align_engine_and_game(
    game: pd.DataFrame,
    engine: pd.DataFrame,
    *,
    value_columns: Iterable[str],
    tolerance_s: float = 0.06,
) -> AlignedComparison:
    """Nearest-time alignment without interpolating across lap boundaries."""
    keys = ["session_id", "lap"]
    values = list(value_columns)
    required_game = set(keys + ["time_s"] + values)
    required_engine = set(keys + ["time_s"] + values)
    if missing := sorted(required_game - set(game.columns)):
        raise ValueError(f"game table missing {missing}")
    if missing := sorted(required_engine - set(engine.columns)):
        raise ValueError(f"engine table missing {missing}")

    pieces: list[pd.DataFrame] = []
    for group_key, game_group in game.groupby(keys, sort=False):
        mask = np.ones(len(engine), dtype=bool)
        for column, value in zip(keys, group_key, strict=True):
            mask &= engine[column].to_numpy() == value
        engine_group = engine.loc[mask]
        if engine_group.empty:
            continue
        left = game_group.sort_values("time_s").copy()
        right = engine_group.sort_values("time_s").copy()
        right = right.rename(columns={column: f"engine_{column}" for column in values})
        right = right.rename(columns={"time_s": "engine_time_s"})
        merged = pd.merge_asof(
            left,
            right[["engine_time_s"] + [f"engine_{column}" for column in values]],
            left_on="time_s",
            right_on="engine_time_s",
            direction="nearest",
            tolerance=tolerance_s,
        )
        pieces.append(merged)

    if not pieces:
        return AlignedComparison(pd.DataFrame(), 0.0, float("nan"))
    aligned = pd.concat(pieces, ignore_index=True)
    valid = aligned["engine_time_s"].notna()
    coverage = float(valid.mean())
    median_time_error = float(np.median(np.abs(aligned.loc[valid, "time_s"] - aligned.loc[valid, "engine_time_s"]))) if valid.any() else float("nan")
    return AlignedComparison(aligned, coverage, median_time_error)


def comparison_metrics(aligned: pd.DataFrame, value_columns: Iterable[str]) -> dict[str, float]:
    """Matched RMSE/MAE metrics for an aligned evidence frame."""
    metrics: dict[str, float] = {}
    for column in value_columns:
        predicted = f"engine_{column}"
        valid = aligned[[column, predicted]].dropna()
        if valid.empty:
            metrics[f"{column}_mae"] = float("nan")
            metrics[f"{column}_rmse"] = float("nan")
            continue
        error = valid[predicted].to_numpy(dtype=float) - valid[column].to_numpy(dtype=float)
        metrics[f"{column}_mae"] = float(np.mean(np.abs(error)))
        metrics[f"{column}_rmse"] = float(np.sqrt(np.mean(np.square(error))))
    return metrics
