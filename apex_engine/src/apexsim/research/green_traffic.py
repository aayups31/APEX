"""Offline signed-gap and corroborated-pass forecasts for R050."""

from collections import Counter
from dataclasses import dataclass
from math import isfinite

import numpy as np

FEATURES = ("gap_s", "pace_delta_s")


def _cell(gap_s, pace_delta_s, prior_drs, use_drs):
    band = (int(gap_s > 1), int(pace_delta_s < 0))
    return (*band, int(prior_drs)) if use_drs and prior_drs is not None else band


@dataclass(frozen=True)
class TrafficForecast:
    signed_gap_s: float
    corroborated_pass_probability: float


@dataclass(frozen=True)
class GreenTrafficReplay:
    """Predict a clean adjacent pair's next signed gap from completed laps."""

    gap_coefficients: tuple[float, float, float]
    pooled_pass_probability: float
    pass_cells: dict[tuple[int, ...], float]
    use_prior_drs: bool

    def forecast(self, gap_s, pace_delta_s, prior_drs=None):
        if not isfinite(gap_s) or not 0 < gap_s <= 2 or not isfinite(pace_delta_s):
            raise ValueError("Traffic replay requires a measured starting gap in (0, 2] s and finite pace")
        if prior_drs is not None and not isinstance(prior_drs, bool):
            raise ValueError("Prior DRS must be a measured boolean or unavailable")
        intercept, gap_weight, pace_weight = self.gap_coefficients
        band = _cell(gap_s, pace_delta_s, None, False)
        cell = _cell(gap_s, pace_delta_s, prior_drs, self.use_prior_drs)
        return TrafficForecast(
            gap_s + intercept + gap_weight * gap_s + pace_weight * pace_delta_s,
            self.pass_cells.get(cell, self.pass_cells.get(band, self.pooled_pass_probability)),
        )

    def to_dict(self):
        return {
            "gap_coefficients": list(self.gap_coefficients),
            "pooled_pass_probability": self.pooled_pass_probability,
            "pass_cells": {"".join(map(str, cell)): p for cell, p in sorted(self.pass_cells.items())},
            "use_prior_drs": self.use_prior_drs,
        }

    @classmethod
    def from_dict(cls, model):
        coefficients = tuple(model["gap_coefficients"])
        pooled = model["pooled_pass_probability"]
        prior_drs = model["use_prior_drs"]
        cells = model["pass_cells"]
        valid_keys = {"00", "01", "10", "11"}
        if prior_drs:
            valid_keys |= {f"{key}{drs}" for key in tuple(valid_keys) for drs in (0, 1)}
        if (
            len(coefficients) != 3
            or not all(isfinite(x) for x in coefficients)
            or not isinstance(prior_drs, bool)
            or not 0 < pooled < 1
            or not cells.keys() <= valid_keys
            or not all(0 < p < 1 for p in cells.values())
        ):
            raise ValueError("Invalid green traffic calibration")
        return cls(coefficients, pooled, {tuple(map(int, key)): p for key, p in cells.items()}, prior_drs)


def fit_green_traffic(rows, *, use_prior_drs=False):
    """Fit fixed-ridge gap correction and Jeffreys-smoothed pass frequencies."""
    if not rows:
        raise ValueError("Traffic replay requires observed transitions")
    x = np.array([[1, *(row[k] for k in FEATURES)] for row in rows])
    y = np.array([row["next_gap_s"] - row["gap_s"] for row in rows])
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Nonfinite traffic replay sample")
    # Fixed penalty in seconds, with a free intercept.
    fit = np.linalg.solve(x.T @ x + np.diag((0.0, 10.0, 10.0)), x.T @ y)
    totals, passes = Counter(), Counter()
    for row in rows:
        band = _cell(row["gap_s"], row["pace_delta_s"], None, False)
        cell = _cell(row["gap_s"], row["pace_delta_s"], row["prior_drs"], use_prior_drs)
        for key in {band, cell}:
            totals[key] += 1
            passes[key] += row["pass"]
    return GreenTrafficReplay(
        tuple(map(float, fit)),
        (sum(row["pass"] for row in rows) + 0.5) / (len(rows) + 1),
        {cell: (passes[cell] + 0.5) / (n + 1) for cell, n in totals.items() if n >= 25},
        use_prior_drs,
    )
