"""R041 effective pace forecasts against a completed historical stint.

This research interface consumes known reference laps and a current prefix only.
Signed pace drift and training residual radii do not identify physical wear.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

import numpy as np

COMPOUNDS = ("SOFT", "MEDIUM", "HARD")


def fit_drift(windows: Iterable[dict]) -> dict:
    """Fit seconds of nine-lap change, counting each current window once."""
    unique = {}
    for row in windows:
        key = (row["session"], row["driver"], row["stints"][1], tuple(row["ages"]))
        value = (row["compounds"][1], tuple(row["current_prefix_s"]), tuple(row["current_target_s"]))
        if key in unique and unique[key] != value:
            raise ValueError("Conflicting duplicate current-stint window")
        unique[key] = value
    result = {}
    for compound in COMPOUNDS:
        changes = [float(np.median(end)-np.median(start))
                   for name, start, end in unique.values() if name == compound]
        if len(changes) < 3 or not np.isfinite(changes).all():
            raise ValueError(f"Insufficient finite development support: {compound}")
        delta = float(np.median(changes))
        radius = float(np.quantile(np.abs(np.asarray(changes)-delta), .9, method="higher"))
        result[compound] = {"delta_s": delta, "radius_s": radius, "windows": len(changes)}
    return result


def predict_reference(
    drift: Mapping[str, dict], compound: str, reference_target_s: Sequence[float],
    current_prefix_s: Sequence[float], *, reference_end_s: float, forecast_at_s: float,
) -> dict:
    """Forecast contrast in seconds; reject reference information from the future."""
    if (not np.isfinite([reference_end_s, forecast_at_s]).all()
            or reference_end_s > forecast_at_s):
        raise ValueError("Reference laps unavailable at forecast time")
    if compound not in drift:
        raise ValueError("Unsupported current compound")
    if (len(reference_target_s) != 3 or len(current_prefix_s) != 3
            or not np.isfinite([*reference_target_s, *current_prefix_s]).all()):
        raise ValueError("Expected three finite reference and prefix lap times")
    delta, radius = drift[compound]["delta_s"], drift[compound]["radius_s"]
    if not np.isfinite([delta, radius]).all() or radius < 0:
        raise ValueError("Invalid calibrated drift or uncertainty radius")
    persistence = float(np.median(reference_target_s)-np.median(current_prefix_s))
    prediction = persistence-delta
    return {"predicted_s": prediction, "reference_persistence_s": persistence,
            "lower_s": prediction-radius, "upper_s": prediction+radius}
