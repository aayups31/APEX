"""Frozen descriptive scoring and segment-cluster coverage uncertainty."""
from __future__ import annotations

from math import pi

import numpy as np


def metrics(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("Tyre evaluation cannot be empty")
    actual = np.array([r["observed_corrected_s"] for r in rows])
    mean = np.array([r["predicted_corrected_s"] for r in rows])
    variance = np.array([r["predictive_variance_s2"] for r in rows])
    if not np.isfinite([actual, mean, variance]).all() or min(variance) <= 0:
        raise ValueError("Nonfinite predictions or nonpositive variance")
    error = actual - mean
    result = {"predictions": len(rows), "mae_s": float(np.mean(abs(error))), "rmse_s": float(np.sqrt(np.mean(error**2))),
              "moment_matched_gaussian_nll": float(np.mean(.5 * (np.log(2 * pi * variance) + error**2 / variance))),
              "gaussian_90_coverage": float(np.mean(abs(error) <= 1.6448536269514722 * np.sqrt(variance))),
              "gaussian_90_mean_width_s": float(np.mean(2 * 1.6448536269514722 * np.sqrt(variance)))}
    for prefix in ("raw", "calibrated"):
        if all(f"{prefix}_lower_90_s" in r for r in rows):
            lower = np.array([r[f"{prefix}_lower_90_s"] for r in rows])
            upper = np.array([r[f"{prefix}_upper_90_s"] for r in rows])
            result[f"{prefix}_90_coverage"] = float(np.mean((actual >= lower) & (actual <= upper)))
            result[f"{prefix}_90_mean_width_s"] = float(np.mean(upper - lower))
    if all("posterior_predictive_pit" in r for r in rows):
        values = np.array([r["posterior_predictive_pit"] for r in rows])
        result["pit_histogram_10_bins"] = np.histogram(values, np.linspace(0., 1., 11))[0].tolist()
        result["pit_mean"] = float(np.mean(values))
    if all("posterior_mixture_nll" in r for r in rows):
        result["posterior_mixture_nll"] = float(np.mean([r["posterior_mixture_nll"] for r in rows]))
    return result


def grouped_metrics(rows: list[dict], fields: tuple[str, ...]) -> list[dict]:
    keys = sorted({tuple(r[f] for f in fields) for r in rows})
    return [{**dict(zip(fields, key, strict=True)), **metrics([r for r in rows if tuple(r[f] for f in fields) == key])} for key in keys]


def coverage_bootstrap(rows: list[dict], resamples: int = 500, seed: int = 2021) -> dict:
    """Resample event/driver/segment clusters; correlated lap origins stay together."""
    clusters = {}
    for row in rows:
        key = row["event_id"], row["driver"], row["segment_id"]
        covered = row["calibrated_lower_90_s"] <= row["observed_corrected_s"] <= row["calibrated_upper_90_s"]
        total, n = clusters.get(key, (0, 0))
        clusters[key] = total + covered, n + 1
    if not clusters or type(resamples) is not int or resamples < 1:
        raise ValueError("Invalid coverage bootstrap")
    values = np.array(list(clusters.values()))
    rng, samples = np.random.default_rng(seed), []
    for _ in range(resamples):
        selected = values[rng.integers(0, len(values), len(values))]
        samples.append(float(selected[:, 0].sum() / selected[:, 1].sum()))
    return {"clusters": len(values), "resamples": resamples, "seed": seed,
            "lower_95": float(np.quantile(samples, .025)), "upper_95": float(np.quantile(samples, .975)),
            "scope": "segment-cluster bootstrap; not a multi-season generalization guarantee"}
