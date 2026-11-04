"""R041 bounded pace residuals with causal context and explicit fallback.

All outputs describe fuel-corrected pace proxies. Bounds constrain the learned
correction in seconds, not the forecast error or physical tyre wear.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from itertools import pairwise
from math import ceil

import numpy as np

from apexsim.research.compound_conditioned import feature_vector, window_key
from apexsim.research.compound_reference import COMPOUNDS, predict_reference

BASELINES = ("reference", "contrast", "midpoint")


def causal_weather(samples: Sequence[dict], cutoff_s: float, *, max_age_s: float = 120.,
                   history_s: float = 600.) -> dict:
    """Join observed Celsius samples backward only; stale/unknown is explicit.

    Samples use ``at_s`` (UTC seconds) and ``track_temperature_c``. The trend is
    a change, not a derivative: latest minus oldest known sample within history.
    """
    if not np.isfinite([cutoff_s, max_age_s, history_s]).all() or min(max_age_s, history_s) <= 0:
        raise ValueError("Invalid weather clock or join tolerance")
    past = []
    for sample in samples:
        time = sample["at_s"]
        if not np.isfinite(time):
            raise ValueError("Nonfinite weather timestamp")
        if time <= cutoff_s:
            past.append(sample)
    past.sort(key=lambda s: s["at_s"])
    if not past or cutoff_s-past[-1]["at_s"] > max_age_s:
        return {"weather_at_s": None, "track_temperature_c": None, "track_change_c": None}
    latest = past[-1]
    temperature = latest.get("track_temperature_c")
    if temperature is None or not np.isfinite(temperature):
        return {"weather_at_s": latest["at_s"], "track_temperature_c": None, "track_change_c": None}
    history = [s for s in past if s["at_s"] >= cutoff_s-history_s
               and s.get("track_temperature_c") is not None and np.isfinite(s["track_temperature_c"])]
    change = temperature-history[0]["track_temperature_c"] if len(history) >= 2 else None
    return {"weather_at_s": latest["at_s"], "track_temperature_c": float(temperature),
            "track_change_c": float(change) if change is not None else None}


def validate_inputs(row: dict) -> float:
    """Check the fixed horizon and real availability; return reference persistence."""
    ages = row["ages"]
    if (len(ages) != 12 or not np.isfinite(ages).all() or ages[0] <= 0
            or any(b-a != 1 for a, b in pairwise(ages))):
        raise ValueError("Expected twelve consecutive positive tyre ages")
    if (len(row["compounds"]) != 2 or any(c not in COMPOUNDS for c in row["compounds"])
            or row["compounds"][0] == row["compounds"][1]):
        raise ValueError("Expected distinct supported reference/current compounds")
    reference = predict_reference({row["compounds"][1]: {"delta_s": 0., "radius_s": 0.}},
                                  row["compounds"][1], row["reference_target_s"], row["current_prefix_s"],
                                  reference_end_s=row["reference_end_s"], forecast_at_s=row["forecast_at_s"])
    if min(*row["reference_target_s"], *row["current_prefix_s"]) <= 0:
        raise ValueError("Pace inputs must be positive seconds")
    if not np.isfinite([row["prefix_s"], row["pairwise_prefix_s"]]).all():
        raise ValueError("Nonfinite prefix contrast")
    return reference["reference_persistence_s"]


def bounded_features(row: dict, group: str = "pace") -> list[float]:
    """Expose forecast-time covariates only; unknown context has presence masks."""
    validate_inputs(row)
    if group not in ("pace", "context"):
        raise ValueError("Unsupported bounded feature group")
    values = feature_vector(row)
    if group == "context":
        ctx = row.get("context", {})
        cutoff = row["forecast_at_s"]
        time = ctx.get("weather_at_s")
        temperature, change = ctx.get("track_temperature_c"), ctx.get("track_change_c")
        if time is not None and (not np.isfinite(time) or time > cutoff or cutoff-time > 120.):
            raise ValueError("Weather context unavailable or stale at forecast time")
        if (temperature is not None or change is not None) and time is None:
            raise ValueError("Observed weather requires a contributing timestamp")
        windows = ctx.get("field_windows", [])
        seen = set()
        for item in windows:
            key = (item["driver"], item["stint"])
            if key in seen:
                raise ValueError("Duplicate contributing field window")
            seen.add(key)
            if (not np.isfinite([item["available_at_s"], item["change_s"]]).all()
                    or item["available_at_s"] > cutoff):
                raise ValueError("Field context unavailable at forecast time")
        age = row["ages"][0]
        values += [float(age), *[float(age*(row["compounds"][1] == c)) for c in COMPOUNDS],
                   float(temperature is not None), float(temperature) if temperature is not None else 0.,
                   float(change is not None), float(change) if change is not None else 0.,
                   float(bool(windows)), float(np.log1p(len(windows))),
                   float(np.median([w["change_s"] for w in windows])) if windows else 0.]
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite bounded model features")
    return values


def baseline_value(row: dict, baseline: str) -> float:
    """Return a declared causal persistence baseline, in seconds of contrast."""
    reference = validate_inputs(row)
    if baseline not in BASELINES:
        raise ValueError("Unknown persistence fallback")
    return {"reference": reference, "contrast": row["prefix_s"],
            "midpoint": .5*(reference+row["prefix_s"])}[baseline]


def training_weights(rows: Sequence[dict]) -> np.ndarray:
    """Equal event mass; divide repeated reference pairs by unique target count."""
    if not rows:
        raise ValueError("Empty bounded calibration data")
    unique, events = {}, defaultdict(set)
    for row in rows:
        key = window_key(row)
        target = row["current_target_s"]
        if len(target) != 3 or not np.isfinite(target).all() or min(target) <= 0:
            raise ValueError("Invalid bounded training target")
        signature = (row["compounds"][1], tuple(row["current_prefix_s"]), tuple(target), row["forecast_at_s"])
        if key in unique and unique[key] != signature:
            raise ValueError("Conflicting repeated current-stint target")
        unique[key] = signature
        events[row["session"]].add(key)
    counts = Counter(window_key(r) for r in rows)
    # Total mass equals unique current targets, invariant to repeated pairs.
    weights = np.asarray([1/(len(events[r["session"]])*counts[window_key(r)]) for r in rows])
    return weights*len(unique)/weights.sum()


def fit_bounded(rows: Sequence[dict], *, baseline: str = "reference", group: str = "pace",
                alpha: float = 10., bound_s: float = .25) -> dict:
    """Fit train-only scaled ridge to the midpoint of both contrast labels."""
    if not np.isfinite([alpha, bound_s]).all() or alpha <= 0 or bound_s < 0:
        raise ValueError("Invalid ridge penalty or residual bound")
    weights = training_weights(rows)
    x = np.asarray([bounded_features(r, group) for r in rows])
    baseline_values = np.asarray([baseline_value(r, baseline) for r in rows])
    y = np.asarray([.5*(r["actual_s"]+r["pairwise_actual_s"]) for r in rows])-baseline_values
    if not np.isfinite(y).all():
        raise ValueError("Nonfinite bounded contrast label")
    center = np.average(x, axis=0, weights=weights)
    scale = np.sqrt(np.average((x-center)**2, axis=0, weights=weights))
    scale[scale < 1e-12] = 1.
    z = np.column_stack([np.ones(len(rows)), (x-center)/scale])
    penalty = alpha*np.eye(z.shape[1])
    penalty[0, 0] = 0.
    coefficients = np.linalg.solve(z.T@(weights[:, None]*z)+penalty, z.T@(weights*y))
    support = {}
    for compound in COMPOUNDS:
        indices = [i for i, r in enumerate(rows) if r["compounds"][1] == compound]
        support[compound] = {"events": len({rows[i]["session"] for i in indices}),
                             "minimum": x[indices].min(axis=0).tolist() if indices else [],
                             "maximum": x[indices].max(axis=0).tolist() if indices else []}
    return {"baseline": baseline, "feature_group": group, "alpha": alpha, "bound_s": bound_s,
            "mean": center.tolist(), "scale": scale.tolist(), "coefficients": coefficients.tolist(),
            "support": support, "radius_s": None, "truth": "FUEL_CORRECTED_PACE_PROXY"}


def predict_bounded(model: dict, row: dict) -> dict:
    """Bound learned influence, recording support exits and fallback on every case."""
    x = np.asarray(bounded_features(row, model["feature_group"]))
    baseline = baseline_value(row, model["baseline"])
    center, scale, coefficients = (np.asarray(model[k]) for k in ("mean", "scale", "coefficients"))
    bound, radius = model["bound_s"], model["radius_s"]
    if (center.shape != x.shape or scale.shape != x.shape or coefficients.shape != (len(x)+1,)
            or not np.isfinite([*center, *scale, *coefficients, bound]).all() or min(scale) <= 0 or bound < 0
            or (radius is not None and (not np.isfinite(radius) or radius < 0))):
        raise ValueError("Invalid bounded model parameters")
    support = model["support"][row["compounds"][1]]
    reasons = []
    if support["events"] < 3:
        reasons.append("FEWER_THAN_THREE_COMPOUND_EVENTS")
    else:
        lo, hi = np.asarray(support["minimum"]), np.asarray(support["maximum"])
        if (lo.shape != x.shape or hi.shape != x.shape or not np.isfinite([*lo, *hi]).all()
                or np.any(lo > hi)):
            raise ValueError("Invalid bounded support ranges")
        if np.any(x < lo-1e-10) or np.any(x > hi+1e-10):
            reasons.append("OUTSIDE_TRAINING_FEATURE_RANGE")
    raw = float(coefficients[0]+((x-center)/scale)@coefficients[1:])
    correction = 0. if reasons else float(np.clip(raw, -bound, bound))
    prediction = baseline+correction
    return {"predicted_s": prediction, "baseline_s": baseline, "raw_correction_s": raw,
            "applied_correction_s": correction, "correction_bounded": not reasons and abs(raw) > bound,
            "fallback": bool(reasons), "fallback_reasons": reasons,
            "reference_persistence_s": validate_inputs(row),
            "lower_s": prediction-radius if radius is not None else None,
            "upper_s": prediction+radius if radius is not None else None}


def cross_event_radius(errors: Sequence[float], coverage: float = .9) -> float:
    """Finite-rank descriptive radius from held-out-event absolute errors.

    Cross-validation residuals are dependent; this is not a coverage guarantee.
    """
    values = np.asarray(errors)
    if not len(values) or not np.isfinite(values).all() or min(values) < 0 or not 0 < coverage < 1:
        raise ValueError("Invalid cross-event uncertainty errors or coverage")
    rank = min(len(values), ceil((len(values)+1)*coverage))
    return float(np.sort(values)[rank-1])
