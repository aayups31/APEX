"""Causal trajectory features and fixed R041 v11 pace-proxy estimators."""
from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise
from math import isfinite
from statistics import median

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from apexsim.research.compound_adaptive import COMPOUNDS, number, predict_adaptive
from apexsim.research.compound_bounded import training_weights
from apexsim.research.compound_conditioned import feature_vector
from apexsim.research.compound_readiness import crossing


def robust_line(samples: Sequence[dict]) -> tuple[float, float]:
    """Median pair slope (seconds/age-lap) and median absolute residual (s)."""
    if len(samples) < 2:
        raise ValueError("Trajectory line needs two observed laps")
    x = [number(p["age"], "history age") for p in samples]
    y = [number(p["pace_s"], "history pace") for p in samples]
    if any(b <= a for a, b in pairwise(x)):
        raise ValueError("Trajectory ages must increase")
    slopes = [(y[j]-y[i])/(x[j]-x[i]) for i in range(len(x)) for j in range(i+1, len(x))]
    slope = median(slopes)
    intercept = median(v-slope*a for a, v in zip(x, y, strict=True))
    dispersion = median(abs(v-(intercept+slope*a)) for a, v in zip(x, y, strict=True))
    if not all(isfinite(v) for v in (*slopes, slope, intercept, dispersion)):
        raise ValueError("Nonfinite trajectory line arithmetic")
    return slope, dispersion


def validate_history(row: dict) -> None:
    """Require consecutive observed inputs ending at the ORIGINAL forecast age."""
    predict_adaptive(row, shrinkage=0.)
    cutoff = row["forecast_at_s"]
    for key, limit in (("current_history", 12), ("reference_history", 12)):
        samples = row[key]
        if not 3 <= len(samples) <= limit or (key == "reference_history" and len(samples) != 12):
            raise ValueError("Invalid trajectory history length")
        ages, times = [], []
        for sample in samples:
            age = number(sample["age"], "history age")
            time = number(sample["end_s"], "history clock")
            pace = number(sample["pace_s"], "history pace")
            if age <= 0 or age % 1 or pace <= 0 or time > cutoff:
                raise ValueError("Invalid or future trajectory observation")
            ages.append(age)
            times.append(time)
        if any(b != a+1 for a, b in pairwise(ages)):
            raise ValueError("Trajectory history bridges a quality gap")
        if any(b <= a for a, b in pairwise(times)):
            raise ValueError("Trajectory observation clocks must increase")
        if key == "current_history":
            if ages[-3:] != row["ages"][:3] or times[-1] != cutoff:
                raise ValueError("Trajectory changed the forecast age or clock")
            if [p["pace_s"] for p in samples[-3:]] != row["current_prefix_s"]:
                raise ValueError("Trajectory current prefix mismatch")
        elif ages != row["ages"] or [p["pace_s"] for p in samples[-3:]] != row["reference_target_s"]:
            raise ValueError("Trajectory completed reference mismatch")
        elif times[-1] != row["reference_end_s"]:
            raise ValueError("Trajectory completed reference clock mismatch")


def trajectory_features(row: dict, group: str = "full") -> list[float]:
    """Return input-only features; no target, session or driver identifier enters."""
    if group not in ("pace", "history", "full"):
        raise ValueError("Unknown trajectory feature group")
    validate_history(row)
    features = feature_vector(row)
    if group != "pace":
        current = row["current_history"]
        slopes = [9*robust_line(current[-n:])[0] for n in (3, 6, 12)]
        features += [row["ages"][0], len(current), *slopes, robust_line(current)[1],
                     median(row["current_prefix_s"])-median(p["pace_s"] for p in current)]
    if group == "full":
        reference = row["reference_history"]
        slope, dispersion = robust_line(reference)
        features += [9*slope, dispersion,
                     median(p["pace_s"] for p in reference[-3:])-median(p["pace_s"] for p in reference[:3])]
    if not all(isfinite(v) for v in features):
        raise ValueError("Nonfinite trajectory feature arithmetic")
    return features


def fit_trajectory(rows: Sequence[dict], *, group: str = "full", family: str = "boost") -> dict:
    """Fixed train-only model; equal events and unique current-target weighting."""
    if family not in ("boost", "ridge"):
        raise ValueError("Unknown trajectory estimator")
    weights = training_weights(rows)
    features = np.asarray([trajectory_features(r, group) for r in rows])
    target = np.asarray([median(r["current_target_s"])-median(r["current_prefix_s"]) for r in rows])
    if not np.isfinite(target).all():
        raise ValueError("Nonfinite trajectory training change")
    scaler = StandardScaler().fit(features, sample_weight=weights)
    scaled = scaler.transform(features)
    model = (GradientBoostingRegressor(loss="absolute_error", n_estimators=128, max_depth=2,
                                      min_samples_leaf=16, learning_rate=.03, subsample=1., random_state=41)
             if family == "boost" else Ridge(alpha=10.))
    model.fit(scaled, target, sample_weight=weights)
    return {"estimator": model, "scaler": scaler, "group": group, "family": family,
            "support": {c: len({r["session"] for r in rows if r["compounds"][1] == c}) for c in COMPOUNDS},
            "bound_s": 2., "training_events": sorted({str(r["session"]) for r in rows})}


def predict_trajectory(model: dict, row: dict) -> dict:
    """Bound the correction and derive crossover from that same point forecast."""
    x = trajectory_features(row, model["group"])
    reference = predict_adaptive(row, shrinkage=0.)["reference_persistence_s"]
    bound = number(model["bound_s"], "trajectory correction bound")
    if bound < 0:
        raise ValueError("Negative trajectory correction bound")
    raw = -float(model["estimator"].predict(model["scaler"].transform([x]))[0])
    if not isfinite(raw):
        raise ValueError("Nonfinite trajectory model prediction")
    fallback = model["support"][row["compounds"][1]] < 3
    correction = 0. if fallback else min(bound, max(-bound, raw))
    prediction = number(reference+correction, "trajectory prediction")
    return {"predicted_s": prediction, "reference_persistence_s": reference,
            "raw_correction_s": raw, "applied_correction_s": correction,
            "correction_bounded": not fallback and abs(raw) > bound, "fallback": fallback,
            "fallback_reasons": ["FEWER_THAN_THREE_COMPOUND_EVENTS"] if fallback else [],
            "predicted_crossover": all(crossing(row[k], prediction) for k in ("prefix_s", "pairwise_prefix_s")),
            "history_laps": len(row["current_history"]), "truth": "FUEL_CORRECTED_PACE_PROXY_NOT_PHYSICAL_WEAR"}
