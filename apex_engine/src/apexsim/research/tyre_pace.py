"""Causal Gaussian tyre-pace state fit; no whole-sequence baseline or clipping."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import log, pi

import numpy as np
from scipy.optimize import minimize

from apexsim.data.benchmark_guard import assert_development_event

DRY = ("SOFT", "MEDIUM", "HARD")


def validate_segments(segments: list[dict]) -> None:
    if not segments or len({s["segment_id"] for s in segments}) != len(segments):
        raise ValueError("Tyre segments must be nonempty and uniquely identified")
    for key in {(s["season"], s["round_number"], s["event_id"]) for s in segments}:
        assert_development_event(key[0], key[1], event_id=key[2])
    for segment in segments:
        rows = segment["rows"]
        if (segment["compound"] not in DRY or len(rows) < 2
                or not np.isfinite([r["corrected_s"] for r in rows]).all()
                or any(rows[i + 1]["lap"] != rows[i]["lap"] + 1 for i in range(len(rows) - 1))):
            raise ValueError("Tyre segments require finite contiguous dry-compound observations")


@dataclass(frozen=True)
class PaceParameters:
    drift: tuple[float, float, float]
    process_variance: float
    observation_variance: float

    def __post_init__(self):
        if (len(self.drift) != 3 or not np.isfinite([*self.drift, self.process_variance, self.observation_variance]).all()
                or min(self.process_variance, self.observation_variance) <= 0):
            raise ValueError("Pace parameters must be finite with positive variances")


def filter_prefix(values: np.ndarray, drift: float, q: float, r: float) -> tuple[float, float]:
    """Posterior after supplied observed prefix; initial flat-intercept posterior N(y0,R)."""
    values = np.asarray(values, dtype=float)
    if not len(values) or not np.isfinite(values).all() or not np.isfinite([drift, q, r]).all() or min(q, r) <= 0:
        raise ValueError("Invalid pace observations or variances")
    mean, variance = values[0], r
    for observed in values[1:]:
        predicted, p = mean + drift, variance + q
        gain = p / (p + r)
        mean, variance = predicted + gain * (observed - predicted), (1 - gain) * p
    return float(mean), float(variance)


def drift_likelihood(values: np.ndarray, q: float, r: float) -> tuple[float, float, float]:
    """Exact marginal Gaussian likelihood quadratic in drift, integrating the pace state."""
    values = np.asarray(values, dtype=float)
    filter_prefix(values[:1], 0., q, r)
    if len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("Drift likelihood needs at least two finite observations")
    intercept, slope, variance = values[0], 0., r
    precision, natural, constant = 0., 0., 0.
    for observed in values[1:]:
        h, p = slope + 1, variance + q
        innovation, s = observed - intercept, p + r
        precision += h * h / s
        natural += h * innovation / s
        constant += log(2 * pi * s) + innovation * innovation / s
        gain = p / s
        intercept += gain * innovation
        slope, variance = (1 - gain) * h, (1 - gain) * p
    return float(natural / precision), float(1 / precision), float(constant)


def marginal_nll(segments: list[dict], params: PaceParameters) -> float:
    total = 0.
    for segment in segments:
        values = np.array([r["corrected_s"] for r in segment["rows"]])
        center, variance, constant = drift_likelihood(values, params.process_variance, params.observation_variance)
        drift = params.drift[DRY.index(segment["compound"])]
        total += .5 * (constant + (drift * drift - 2 * drift * center) / variance)
    return float(total)


def fit_pace(segments: list[dict]) -> tuple[PaceParameters, dict]:
    """Training-only constrained marginal likelihood with three fixed starts."""
    validate_segments(segments)
    def decode(x):
        return PaceParameters(tuple(float(v) for v in x[:3]), float(np.exp(x[3])), float(np.exp(x[4])))
    attempts = []
    best = None
    for q, r in ((.01, .25), (.05, 1.), (.001, .1)):
        result = minimize(lambda x: marginal_nll(segments, decode(x)), [ .05, .05, .05, log(q), log(r)],
                          method="L-BFGS-B", bounds=[(0., .5)] * 3 + [(log(1e-5), log(4.))] * 2,
                          options={"maxiter": 200, "ftol": 1e-8})
        attempts.append({"success": bool(result.success), "nll": float(result.fun), "message": str(result.message), "iterations": int(result.nit)})
        if result.success and np.isfinite(result.fun) and (best is None or result.fun < best.fun):
            best = result
    if best is None:
        raise ValueError("No successful finite tyre-pace likelihood fit")
    parameters = decode(best.x)
    return parameters, {"parameters": asdict(parameters), "attempts": attempts,
                        "selected_training_nll": float(best.fun), "training_segments": len(segments),
                        "training_events": sorted({s["event_id"] for s in segments}),
                        "unsupported_compounds_retaining_prior_005": [c for c in DRY if not any(s["compound"] == c for s in segments)]}


def forecast_rows(segments: list[dict], params: PaceParameters, method: str = "state_space") -> list[dict]:
    """Evaluate identical origins/horizons before observing each target."""
    if method not in ("state_space", "persistence", "last_three_trend"):
        raise ValueError("Unknown tyre-pace baseline")
    validate_segments(segments)
    output = []
    for segment in segments:
        values = np.array([r["corrected_s"] for r in segment["rows"]])
        drift = params.drift[DRY.index(segment["compound"])]
        for origin in range(len(values) - 1):
            prefix = values[:origin + 1]
            mean, variance = filter_prefix(prefix, drift, params.process_variance, params.observation_variance)
            for horizon in (1, 3, 5):
                if origin + horizon >= len(values):
                    continue
                prediction = mean + horizon * drift
                if method == "persistence":
                    prediction = values[origin]
                elif method == "last_three_trend":
                    recent = prefix[-3:]
                    slope = float(np.polyfit(np.arange(len(recent)), recent, 1)[0]) if len(recent) > 1 else 0.
                    prediction = values[origin] + horizon * slope
                predictive_variance = variance + horizon * params.process_variance + params.observation_variance
                output.append({"event_id": segment["event_id"], "track_id": segment["track_id"], "driver": segment["driver"],
                               "compound": segment["compound"], "segment_id": segment["segment_id"],
                               "origin_lap": segment["rows"][origin]["lap"], "target_lap": segment["rows"][origin + horizon]["lap"],
                               "horizon": horizon, "observed_corrected_s": float(values[origin + horizon]),
                               "predicted_corrected_s": float(prediction), "predictive_variance_s2": float(predictive_variance),
                               "latent_pace_relative_to_anchor_s": float(mean - values[0]), "method": method})
    return output
