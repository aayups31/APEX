"""R041 multi-output tyre pace proxy using pre-race nomination metadata."""

from __future__ import annotations

from datetime import date, datetime, timezone
from statistics import median

import numpy as np
from sklearn.linear_model import Ridge

from apexsim.research.compound_bounded import training_weights
from apexsim.research.compound_trajectory import trajectory_features

ORDER = ("HARD", "MEDIUM", "SOFT")
SEASONS = (2023, 2024, 2025)


def inventory(sources: list[dict], expected: set[str]) -> dict:
    """Index the unique as-announced identities for the exact study cohort."""
    result = {}
    for source in sources:
        issued = date.fromisoformat(source["issued"])
        if not source["url"].startswith("https://press.pirelli.com/"):
            raise ValueError("Missing Pirelli source")
        for event, values in source["events"].items():
            if event in result:
                raise ValueError("Duplicate nomination")
            if (
                len(values) != 3
                or any(type(v) is not int or not 1 <= v <= 6 for v in values)
                or sorted(set(values)) != values
            ):
                raise ValueError("Invalid ordered compound nomination")
            result[event] = issued, dict(zip(ORDER, values, strict=True))
    if set(result) != expected:
        raise ValueError("Nomination event coverage mismatch")
    return result


def features(row: dict, allocations: dict, include_allocation: bool) -> list[float]:
    """Only forecast-time laps, calendar season and known nominations enter."""
    forecast = datetime.fromtimestamp(row["forecast_at_s"], tz=timezone.utc).date()
    issued, compounds = allocations[str(row["session"])]
    if issued >= forecast or forecast.year not in SEASONS:
        raise ValueError("Unsupported season or nomination not known before forecast day")
    center = median(row["current_prefix_s"])
    x = trajectory_features(row)
    x.extend(t - center for t in row["current_prefix_s"] + row["reference_target_s"])
    x.extend(float(row["compounds"][0] == c) for c in ORDER)
    years = [float(forecast.year == year) for year in SEASONS]
    x.extend(years)
    if include_allocation:
        identity = [float(compounds[c] == n) for c in row["compounds"] for n in range(1, 7)]
        x.extend(identity)
        x.extend(year * v for year in years for v in identity)
    return x


def fit(rows: list[dict], x: np.ndarray) -> dict:
    """Fit three target-lap offsets using training rows only."""
    weights = training_weights(rows)
    offsets = np.array([np.asarray(r["current_target_s"]) - median(r["current_prefix_s"]) for r in rows])
    # Centered squares avoid a negative roundoff variance on constant flags.
    center = np.average(x, axis=0, weights=weights)
    centered = x - center
    scale = np.sqrt(np.average(centered**2, axis=0, weights=weights))
    scale[np.ptp(x, axis=0) == 0] = 1.0
    model = Ridge(alpha=10.0, solver="svd").fit(centered / scale, offsets, sample_weight=weights)
    return {
        "center": center.tolist(),
        "scale": scale.tolist(),
        "coefficients": model.coef_.tolist(),
        "intercept": model.intercept_.tolist(),
    }


def forecast_laps(model: dict, x: list[float], prefix: list[float]) -> tuple[list[float], int]:
    """Restore a portable checkpoint and bound each projected pace change."""
    z = (np.asarray(x) - model["center"]) / model["scale"]
    offsets = np.asarray(model["coefficients"]) @ z + model["intercept"]
    changes = offsets + median(prefix) - np.asarray(prefix)
    if changes.shape != (3,) or not np.isfinite(changes).all():
        raise ValueError("Invalid allocation forecast")
    laps = np.asarray(prefix) + np.clip(changes, -2.0, 2.0)
    if min(laps) <= 0:
        raise ValueError("Nonpositive allocation pace")
    return laps.tolist(), int(np.count_nonzero(abs(changes) > 2.0))
