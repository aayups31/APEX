"""Validated processed lap observations from pinned TracingInsights JSON exports."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np


def utc_seconds(value: str) -> float:
    """Interpret the publisher's timezone-naive dates as UTC."""
    stamp = datetime.fromisoformat(value)
    return stamp.replace(tzinfo=timezone.utc).timestamp() if stamp.tzinfo is None else stamp.timestamp()


def export_samples(document: dict, expected_key: str) -> np.ndarray:
    """Convert processed arrays to seconds, m/s and fractions with explicit binary DRS."""
    fields = document["tel"]
    if fields["dataKey"] != expected_key:
        raise ValueError("Export event/driver/lap identity mismatch")
    arrays = [np.asarray(fields[k], dtype=float) for k in ("time", "speed", "throttle", "brake", "drs")]
    if any(a.ndim != 1 for a in arrays) or len({len(a) for a in arrays}) != 1 or len(arrays[0]) < 2:
        raise ValueError("Export arrays have inconsistent lengths")
    time, speed, throttle, brake, drs = arrays
    if not np.isfinite(time).all() or np.any(np.diff(time) <= 0) or time[0] < 0:
        raise ValueError("Export time is invalid or unordered")
    if not np.isin(drs, [0, 1]).all():
        raise ValueError("Unknown exported DRS representation")
    finite_brake = brake[np.isfinite(brake)]
    if not np.isin(finite_brake, [0, 1, 100]).all() or (1 in finite_brake and 100 in finite_brake):
        raise ValueError("Unknown exported brake representation")
    if 100 in finite_brake:
        brake = brake / 100
    return np.column_stack((time, speed / 3.6, throttle / 100, brake, np.where(drs == 1, 12, 0)))


def associate_lap(
    metadata: dict,
    lap: int,
    driver: int,
    compound: str,
    stint: int,
    age: float,
    start_s: float,
    duration_s: float,
    cutoff_s: float,
) -> dict:
    """Bind a known source lap to frozen APEX identity and clock tolerances."""
    positions = [i for i, n in enumerate(metadata["lap"]) if n == lap]
    if len(positions) != 1:
        raise ValueError("Missing or duplicate exported lap")
    i = positions[0]
    if (int(metadata["dNum"][i]), metadata["compound"][i], metadata["stint"][i], metadata["life"][i]) != (
        driver,
        compound,
        stint,
        age,
    ):
        raise ValueError("Exported lap driver/stint/compound/age mismatch")
    start = utc_seconds(metadata["lSD"][i])
    duration = float(metadata["time"][i])
    clock_error, duration_error = start - start_s, duration - duration_s
    if not np.isfinite([start, duration]).all() or duration <= 2:
        raise ValueError("Invalid exported lap timing")
    if abs(clock_error) > 0.5 or abs(duration_error) > 0.05:
        raise ValueError("Exported lap clock/duration mismatch")
    if max(start + duration, start_s + duration_s) > cutoff_s - 30:
        raise ValueError("Exported lap lacks forecast timing buffer")
    return {"clock_error_s": clock_error, "duration_error_s": duration_error, "duration_s": duration}


def processed_features(groups: list[list[dict]]) -> list[float]:
    """Encode two buffered laps in each of three groups using 23 driving inputs."""
    if len(groups) != 3 or any(len(g) != 2 for g in groups):
        raise ValueError("Processed inputs require three groups of two laps")
    for group in groups:
        for lap in group:
            v = lap["means"]
            if not np.isfinite(lap["coverage"]) or not 0 <= lap["coverage"] <= 1 + 1e-12:
                raise ValueError("Invalid processed coverage")
            if (
                len(v) != 5
                or not np.isfinite(v).all()
                or not 0 <= v[0] <= 120
                or any(not 0 <= a <= 1 for a in v[1:])
            ):
                raise ValueError("Invalid processed channel summary")
    flags = [all(p["coverage"] >= 0.9 for p in g) for g in groups]
    means = [np.mean([p["means"] for p in g], axis=0) for g in groups]
    own = means[0] if flags[0] else np.zeros(5)
    trend = np.subtract(groups[0][-1]["means"], groups[0][0]["means"]) if flags[0] else np.zeros(5)
    differences = [own - means[j] if flags[0] and flags[j] else np.zeros(5) for j in (1, 2)]
    return [
        *own.tolist(),
        *trend.tolist(),
        *differences[0].tolist(),
        *differences[1].tolist(),
        *[float(f) for f in flags],
    ]
