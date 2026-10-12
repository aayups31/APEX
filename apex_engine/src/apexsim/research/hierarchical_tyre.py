"""Conditional Bayesian compound/track/driver drift hierarchy, Gaussian latent pace.

Q/R are training-only empirical-Bayes inputs. Group variances have proper IG
priors and are sampled; predictions for unseen groups retain prior uncertainty.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

import numpy as np
from scipy.special import logsumexp

from apexsim.research.tyre_pace import PaceParameters, drift_likelihood, validate_segments


@dataclass(frozen=True)
class HierarchySettings:
    seeds: tuple[int, ...] = (11, 23)
    warmup: int = 1500
    draws: int = 1500


def split_rhat(chains: np.ndarray) -> np.ndarray:
    """Classic split-chain R-hat, recorded alongside all chains and parameter limits."""
    chains = np.asarray(chains, dtype=float)
    if chains.ndim != 3 or chains.shape[0] < 2 or chains.shape[1] < 4 or not np.isfinite(chains).all():
        raise ValueError("R-hat requires at least two finite chains")
    half = chains.shape[1] // 2
    split = np.concatenate((chains[:, :half], chains[:, -half:]), axis=0)
    w = np.mean(np.var(split, axis=1, ddof=1), axis=0)
    b = half * np.var(np.mean(split, axis=1), axis=0, ddof=1)
    return np.sqrt(((half - 1) / half * w + b / half) / np.maximum(w, 1e-15))


class HierarchicalTyreModel:
    def __init__(self, noise: PaceParameters, settings: HierarchySettings | None = None):
        self.noise, self.settings = noise, settings or HierarchySettings()
        s = self.settings
        if (len(s.seeds) < 2 or len(set(s.seeds)) != len(s.seeds) or s.warmup < 0 or s.draws < 4
                or any(type(v) is not int for v in (*s.seeds, s.warmup, s.draws))):
            raise ValueError("Invalid hierarchical sampler budgets/seeds")
        self.levels = None
        self.chains = self.variance_chains = None

    def fit(self, segments: list[dict]) -> dict:
        validate_segments(segments)
        families = ("compound", "track_id", "driver")
        self.levels = {family: sorted({s[family] for s in segments}) for family in families}
        groups, indices, labels = [], {}, ["population"]
        for family in families:
            group = []
            for level in self.levels[family]:
                indices[family, level] = len(labels)
                group.append(len(labels))
                labels.append(f"{family}:{level}")
            groups.append(np.array(group))
        x = np.zeros((len(segments), len(labels)))
        likelihood = np.array([drift_likelihood(np.array([r["corrected_s"] for r in s["rows"]]),
                                               self.noise.process_variance, self.noise.observation_variance)[:2]
                               for s in segments])
        y, v = likelihood[:, 0], likelihood[:, 1]
        x[:, 0] = 1.
        for i, segment in enumerate(segments):
            for family in families:
                x[i, indices[family, segment[family]]] = 1.
        weighted = x.T / v
        gram, natural = weighted @ x, weighted @ y
        priors_scale = np.array([.01, .0025, .0025])
        chains, variances = [], []
        for seed in self.settings.seeds:
            rng = np.random.default_rng(seed)
            tau = priors_scale / 2
            samples, variance_samples = [], []
            for iteration in range(self.settings.warmup + self.settings.draws):
                diagonal = np.empty(len(labels))
                diagonal[0] = 1 / .2**2
                for group, variance in zip(groups, tau, strict=True):
                    diagonal[group] = 1 / variance
                precision = gram + np.diag(diagonal)
                rhs = natural.copy()
                rhs[0] += .05 / .2**2
                chol = np.linalg.cholesky(precision)
                mean = np.linalg.solve(chol.T, np.linalg.solve(chol, rhs))
                theta = mean + np.linalg.solve(chol.T, rng.normal(size=len(labels)))
                for j, group in enumerate(groups):
                    shape = 3 + len(group) / 2
                    scale = priors_scale[j] + .5 * np.sum(theta[group]**2)
                    tau[j] = scale / rng.gamma(shape)
                if iteration >= self.settings.warmup:
                    samples.append(theta)
                    variance_samples.append(tau.copy())
            chains.append(samples)
            variances.append(variance_samples)
        self.chains, self.variance_chains = np.array(chains), np.array(variances)
        self.indices, self.labels = indices, labels
        self.training_events = sorted({s["event_id"] for s in segments})
        # Supported predictive drifts are identifiable even when additive contrasts are weak.
        supported = self.chains @ x.T
        rhat = split_rhat(np.concatenate((self.chains[:, :, :1], supported), axis=2))
        hyper_rhat = split_rhat(self.variance_chains)
        if not np.isfinite(self.chains).all() or not np.isfinite(self.variance_chains).all() or np.any(self.variance_chains <= 0):
            raise ValueError("Nonfinite hierarchical posterior")
        flat = self.chains.reshape(-1, len(labels))
        return {"training_events": self.training_events, "levels": self.levels, "training_segments": len(segments),
                "settings": {"seeds": list(self.settings.seeds), "warmup": self.settings.warmup, "draws": self.settings.draws},
                "max_supported_split_rhat": float(np.max(rhat)), "group_variance_split_rhat": hyper_rhat.tolist(),
                "parameter_summary": {label: {"mean": float(flat[:, i].mean()),
                                               "lower_95": float(np.quantile(flat[:, i], .025)),
                                               "upper_95": float(np.quantile(flat[:, i], .975))} for i, label in enumerate(labels)},
                "noise_boundary": "Q/R plug-in from training-only Gaussian state likelihood; parameter credible intervals not calibrated",
                "priors": {"population_mean": .05, "population_sd": .2, "group_IG_shape": 3,
                           "group_IG_scale": dict(zip(families, priors_scale.tolist(), strict=True))}}

    def drift_draws(self, segment: dict) -> np.ndarray:
        if self.chains is None:
            raise RuntimeError("Fit hierarchy before prediction")
        flat = self.chains.reshape(-1, self.chains.shape[-1])
        tau = self.variance_chains.reshape(-1, 3)
        result = flat[:, 0].copy()
        for j, family in enumerate(("compound", "track_id", "driver")):
            level = segment[family]
            if (family, level) in self.indices:
                result += flat[:, self.indices[family, level]]
            else:
                key = int.from_bytes(sha256(f"{family}:{level}".encode()).digest()[:8], "little")
                result += np.random.default_rng(key).normal(size=len(result)) * np.sqrt(tau[:, j])
        return result

    def forecast(self, segments: list[dict]) -> list[dict]:
        validate_segments(segments)
        if self.chains is None:
            raise RuntimeError("Fit hierarchy before prediction")
        output = []
        q, r = self.noise.process_variance, self.noise.observation_variance
        for segment in segments:
            values = np.array([row["corrected_s"] for row in segment["rows"]])
            drift = self.drift_draws(segment)
            state, variance = np.full(len(drift), values[0]), r
            for origin in range(len(values) - 1):
                for horizon in (1, 3, 5):
                    if origin + horizon >= len(values):
                        continue
                    means = state + horizon * drift
                    predictive_noise = variance + horizon * q + r
                    key = int.from_bytes(sha256(f"{segment['segment_id']}:{origin}:{horizon}".encode()).digest()[:8], "little")
                    draws = means + np.random.default_rng(key).normal(size=len(means)) * np.sqrt(predictive_noise)
                    actual = values[origin + horizon]
                    mean = float(means.mean())
                    total_variance = float(predictive_noise + means.var())
                    output.append({"event_id": segment["event_id"], "track_id": segment["track_id"], "driver": segment["driver"],
                                   "compound": segment["compound"], "segment_id": segment["segment_id"],
                                   "origin_lap": segment["rows"][origin]["lap"], "target_lap": segment["rows"][origin + horizon]["lap"],
                                   "horizon": horizon, "observed_corrected_s": float(actual), "predicted_corrected_s": mean,
                                   "predictive_variance_s2": total_variance, "raw_lower_90_s": float(np.quantile(draws, .05)),
                                   "raw_upper_90_s": float(np.quantile(draws, .95)), "posterior_predictive_pit": float(np.mean(draws <= actual)),
                                   "posterior_mixture_nll": float(-logsumexp(-.5 * (np.log(2 * np.pi * predictive_noise) +
                                                                                  (actual - means)**2 / predictive_noise)) + np.log(len(means))),
                                   "unseen_groups": [f for f in self.levels if segment[f] not in self.levels[f]], "method": "hierarchical"})
                p = variance + q
                gain = p / (p + r)
                state = state + drift + gain * (values[origin + 1] - state - drift)
                variance = (1 - gain) * p
        return output


def calibration_scales(rows: list[dict]) -> dict[int, float]:
    """Validation-only finite-sample standardized absolute error order statistic."""
    result = {}
    for horizon in (1, 3, 5):
        scores = sorted(abs(r["observed_corrected_s"] - r["predicted_corrected_s"]) /
                        np.sqrt(r["predictive_variance_s2"]) for r in rows if r["horizon"] == horizon)
        if not scores or not np.isfinite(scores).all():
            raise ValueError("Missing or nonfinite predictive calibration scores")
        index = min(len(scores) - 1, int(np.ceil((len(scores) + 1) * .90)) - 1)
        result[horizon] = float(scores[index])
    if min(result.values()) <= 0:
        raise ValueError("Predictive calibration scales must be positive")
    return result


def apply_calibration(rows: list[dict], scales: dict[int, float]) -> list[dict]:
    result = []
    for row in rows:
        half = scales[row["horizon"]] * np.sqrt(row["predictive_variance_s2"])
        result.append({**row, "calibrated_lower_90_s": float(row["predicted_corrected_s"] - half),
                       "calibrated_upper_90_s": float(row["predicted_corrected_s"] + half)})
    return result
