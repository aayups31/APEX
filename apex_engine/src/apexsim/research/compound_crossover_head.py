"""R041 event decision scores alongside causal completed-reference pace forecasts."""
from __future__ import annotations

from collections import Counter
from math import exp

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from apexsim.research.compound_conditioned import feature_vector, window_key


def crossover(start: float, end: float) -> bool:
    """Sustained sign reversal outside the fixed 0.15 second margins."""
    return start*end < 0 and min(abs(start), abs(end)) > .15


def event_features(row: dict) -> list[float]:
    """Ten forecast-time covariates; no future current-stint label is consumed."""
    start = row["prefix_s"]
    reference = float(np.median(row["reference_target_s"])-np.median(row["current_prefix_s"]))
    return [*feature_vector(row), abs(start), start*reference,
            float(crossover(start, reference)), abs(row["pairwise_prefix_s"])]


def fit_event(rows: list[dict], c: float = .1) -> dict:
    """Fit an event head with duplicated label definitions and window weights."""
    counts = Counter(window_key(r) for r in rows)
    x = np.asarray([event_features(r) for r in rows for _ in range(2)])
    y = [int(crossover(r[p], r[t])) for r in rows for p, t in
         (("prefix_s", "actual_s"), ("pairwise_prefix_s", "pairwise_actual_s"))]
    weights = [.5/counts[window_key(r)] for r in rows for _ in range(2)]
    scaler = StandardScaler().fit(x)
    classifier = LogisticRegression(C=c, class_weight="balanced", max_iter=1000)
    classifier.fit(scaler.transform(x), y, sample_weight=weights)
    return {"c": c, "threshold": .5, "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(),
            "coefficients": classifier.coef_[0].tolist(), "intercept": float(classifier.intercept_[0])}


def predict_event(model: dict, row: dict) -> dict:
    """Return an uncalibrated balanced decision score; reject future reference data."""
    if (not np.isfinite([row["reference_end_s"], row["forecast_at_s"]]).all()
            or row["reference_end_s"] > row["forecast_at_s"]):
        raise ValueError("Event reference unavailable at forecast time")
    features = event_features(row)
    if not (len(features) == len(model["mean"]) == len(model["scale"]) == len(model["coefficients"])):
        raise ValueError("Invalid event-head feature dimensions")
    values = [*features, *model["mean"], *model["scale"], *model["coefficients"], model["intercept"], model["threshold"]]
    if not np.isfinite(values).all() or min(model["scale"]) <= 0 or not 0 <= model["threshold"] <= 1:
        raise ValueError("Invalid event-head parameters")
    logit = model["intercept"]+sum((x-m)/s*b for x, m, s, b in
                                    zip(features, model["mean"], model["scale"], model["coefficients"], strict=True))
    score = 1/(1+exp(-logit)) if logit >= 0 else exp(logit)/(1+exp(logit))
    return {"crossover_score": score, "predicted_crossover": score >= model["threshold"]}
