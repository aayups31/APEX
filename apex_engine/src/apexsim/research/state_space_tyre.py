"""Interpretable latent tyre-degradation filtering from public lap timing.

Inspired by Cappello & Hoegh (2025). This starter implementation is a robust
one-dimensional Kalman filter. It separates an observed fuel-mass contribution
from a latent tyre-pace state and resets the latent state at pit stops.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class StateSpaceTyreParameters:
    compound_drift_s_per_lap: dict[str, float]
    process_variance: float = 0.04
    observation_variance: float = 0.25
    reset_variance: float = 0.20
    fuel_time_s_per_kg: float = 0.030
    innovation_clip_sigma: float = 4.0

    @classmethod
    def defaults(cls) -> StateSpaceTyreParameters:
        return cls({"SOFT": 0.080, "MEDIUM": 0.055, "HARD": 0.038, "INTERMEDIATE": 0.070, "WET": 0.060})


@dataclass(frozen=True)
class TyreStateEstimate:
    mean_s: float
    variance: float
    lower_95_s: float
    upper_95_s: float
    innovation_s: float


class LatentTyreDegradationFilter:
    def __init__(self, parameters: StateSpaceTyreParameters | None = None) -> None:
        self.p = parameters or StateSpaceTyreParameters.defaults()

    def filter(
        self,
        lap_times_s: Sequence[float],
        fuel_mass_kg: Sequence[float],
        compounds: Sequence[str],
        pit_reset: Sequence[bool] | None = None,
        baseline_lap_time_s: float | None = None,
    ) -> pd.DataFrame:
        lap_times = np.asarray(lap_times_s, dtype=float)
        fuel = np.asarray(fuel_mass_kg, dtype=float)
        compounds_arr = np.asarray([str(c).upper() for c in compounds], dtype=object)
        if not (len(lap_times) == len(fuel) == len(compounds_arr)):
            raise ValueError("All input sequences must have equal length")
        if len(lap_times) == 0:
            return pd.DataFrame()
        reset = np.zeros(len(lap_times), dtype=bool) if pit_reset is None else np.asarray(pit_reset, dtype=bool)
        if len(reset) != len(lap_times):
            raise ValueError("pit_reset length mismatch")

        # Robust baseline from the quickest fuel-corrected laps.
        corrected = lap_times - self.p.fuel_time_s_per_kg * fuel
        baseline = float(baseline_lap_time_s) if baseline_lap_time_s is not None else float(np.nanpercentile(corrected, 10))
        mean = 0.0
        variance = self.p.reset_variance
        rows = []
        for i, (observed, mass, compound) in enumerate(zip(lap_times, fuel, compounds_arr, strict=True)):
            if reset[i]:
                mean = 0.0
                variance = self.p.reset_variance
            drift = self.p.compound_drift_s_per_lap.get(str(compound), np.mean(list(self.p.compound_drift_s_per_lap.values())))
            predicted_mean = mean + drift
            predicted_variance = variance + self.p.process_variance
            observation = observed - baseline - self.p.fuel_time_s_per_kg * mass
            innovation = observation - predicted_mean
            sigma = np.sqrt(predicted_variance + self.p.observation_variance)
            innovation = float(np.clip(innovation, -self.p.innovation_clip_sigma * sigma, self.p.innovation_clip_sigma * sigma))
            kalman_gain = predicted_variance / (predicted_variance + self.p.observation_variance)
            mean = predicted_mean + kalman_gain * innovation
            variance = (1.0 - kalman_gain) * predicted_variance
            std = np.sqrt(max(variance, 0.0))
            rows.append(
                {
                    "lap_index": i,
                    "compound": str(compound),
                    "latent_tyre_pace_s": mean,
                    "variance": variance,
                    "lower_95_s": mean - 1.96 * std,
                    "upper_95_s": mean + 1.96 * std,
                    "innovation_s": innovation,
                    "baseline_lap_time_s": baseline,
                    "fuel_effect_s": self.p.fuel_time_s_per_kg * mass,
                    "pit_reset": bool(reset[i]),
                }
            )
        return pd.DataFrame(rows)
