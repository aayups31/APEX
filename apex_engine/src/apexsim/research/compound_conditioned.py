"""R041 causal event-conditioned pace proxy; not a physical wear estimator."""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

import numpy as np

from apexsim.research.compound_reference import COMPOUNDS, predict_reference


def feature_vector(row: dict, level: int = 3) -> list[float]:
    """Use compound, known reference change, current prefix slope and contrast."""
    if level not in (0, 1, 2, 3) or row["compounds"][1] not in COMPOUNDS:
        raise ValueError("Unsupported conditioned feature domain")
    prefix = row["current_prefix_s"]
    ref = row["reference_target_s"]
    if len(prefix) != 3 or len(ref) != 3 or not np.isfinite([*prefix, *ref, row["prefix_s"]]).all():
        raise ValueError("Invalid conditioned forecast prefix")
    values = [float(row["compounds"][1] == compound) for compound in COMPOUNDS]
    if level >= 1:
        values.append(float(np.median(ref)-np.median(prefix)-row["prefix_s"]))
    if level >= 2:
        values.append(4.5*(prefix[2]-prefix[0]))
    if level >= 3:
        values.append(row["prefix_s"])
    return values


def window_key(row: dict) -> tuple:
    """Identify a later-stint age window across different reference pairs."""
    return row["session"], row["driver"], row["stints"][1], tuple(row["ages"])


def fit_conditioned(rows: Sequence[dict], *, alpha: float = 10., level: int = 3) -> dict:
    """Fit weighted ridge to seconds of future current-stint pace change."""
    if not rows or not np.isfinite(alpha) or alpha <= 0:
        raise ValueError("Invalid conditioned calibration support or penalty")
    counts = Counter(window_key(r) for r in rows)
    weights = np.asarray([1/counts[window_key(r)] for r in rows])
    x = np.asarray([feature_vector(r, level) for r in rows])
    y = np.asarray([float(np.median(r["current_target_s"])-np.median(r["current_prefix_s"])) for r in rows])
    if not np.isfinite(y).all():
        raise ValueError("Nonfinite conditioned calibration target")
    coefficients = np.linalg.solve(x.T@(weights[:, None]*x)+alpha*np.eye(x.shape[1]), x.T@(weights*y))
    residuals = abs(y-x@coefficients)
    radii = {}
    for compound in COMPOUNDS:
        indices = [i for i, r in enumerate(rows) if r["compounds"][1] == compound]
        support = len({window_key(rows[i]) for i in indices})
        if support < 3:
            raise ValueError(f"Insufficient conditioned compound support: {compound}")
        ordered = sorted(indices, key=lambda i: residuals[i])
        total, cumulative = sum(weights[indices]), 0.
        for i in ordered:
            cumulative += weights[i]
            if cumulative >= .9*total:
                radii[compound] = {"radius_s": float(residuals[i]), "windows": support}
                break
    return {"alpha": alpha, "feature_level": level, "coefficients": coefficients.tolist(), "support": radii}


def predict_conditioned(model: dict, row: dict) -> dict:
    """Consume only forecast-time fields; current target labels are ignored."""
    compound = row["compounds"][1]
    values = np.asarray(feature_vector(row, model["feature_level"]))
    coefficients = np.asarray(model["coefficients"])
    if values.shape != coefficients.shape or not np.isfinite(coefficients).all():
        raise ValueError("Invalid conditioned forecast coefficients")
    drift = {compound: {"delta_s": float(values@coefficients),
                        "radius_s": model["support"][compound]["radius_s"]}}
    return predict_reference(drift, compound, row["reference_target_s"], row["current_prefix_s"],
                             reference_end_s=row["reference_end_s"], forecast_at_s=row["forecast_at_s"])
