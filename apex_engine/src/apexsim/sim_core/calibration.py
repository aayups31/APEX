from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import HuberRegressor, LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

from apexsim.sim_core.types import CarParameters


@dataclass(frozen=True)
class LongitudinalCalibration:
    throttle_accel_gain: float
    brake_decel_gain: float
    drag_accel_coeff: float
    rolling_accel: float
    mae_mps2: float
    r2: float
    samples: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TyreDegradationCalibration:
    compound: str
    seconds_per_lap: float
    intercept_s: float
    r2: float
    samples: int

    def to_dict(self) -> dict:
        return asdict(self)


def fit_longitudinal_dynamics(frame: pd.DataFrame) -> LongitudinalCalibration:
    """Fit an interpretable acceleration prior from canonical telemetry.

    a = b0 + b1*throttle - b2*brake - b3*v^2

    This is not the final vehicle model. It is a diagnostic calibration that
    catches sign errors, unit errors and impossible parameter values before a
    neural residual model is introduced.
    """
    required = {"speed_mps", "acceleration_mps2", "throttle", "brake"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Telemetry missing calibration columns: {sorted(missing)}")
    clean = frame[list(required)].replace([np.inf, -np.inf], np.nan).dropna()
    clean = clean[clean.acceleration_mps2.abs() < 25.0]
    if len(clean) < 100:
        raise ValueError("At least 100 clean telemetry rows are required")
    x = np.column_stack(
        [
            clean.throttle.to_numpy(float),
            -clean.brake.to_numpy(float),
            -(clean.speed_mps.to_numpy(float) ** 2),
        ]
    )
    y = clean.acceleration_mps2.to_numpy(float)
    model = HuberRegressor(epsilon=1.5, max_iter=500).fit(x, y)
    pred = model.predict(x)
    return LongitudinalCalibration(
        throttle_accel_gain=float(model.coef_[0]),
        brake_decel_gain=float(model.coef_[1]),
        drag_accel_coeff=float(model.coef_[2]),
        rolling_accel=float(-model.intercept_),
        mae_mps2=float(mean_absolute_error(y, pred)),
        r2=float(r2_score(y, pred)),
        samples=len(clean),
    )


def fit_tyre_degradation(laps: pd.DataFrame) -> list[TyreDegradationCalibration]:
    required = {"compound", "tyre_age_laps", "lap_time_s"}
    missing = required - set(laps.columns)
    if missing:
        raise ValueError(f"Lap table missing degradation columns: {sorted(missing)}")
    results: list[TyreDegradationCalibration] = []
    for compound, group in laps.dropna(subset=list(required)).groupby("compound"):
        if len(group) < 6:
            continue
        x = group[["tyre_age_laps"]].to_numpy(float)
        y = group.lap_time_s.to_numpy(float)
        model = LinearRegression().fit(x, y)
        pred = model.predict(x)
        results.append(
            TyreDegradationCalibration(
                compound=str(compound),
                seconds_per_lap=float(model.coef_[0]),
                intercept_s=float(model.intercept_),
                r2=float(r2_score(y, pred)),
                samples=len(group),
            )
        )
    return results


def calibrated_car_parameters(
    base: CarParameters,
    calibration: LongitudinalCalibration,
) -> CarParameters:
    """Map fitted public-data coefficients into a conservative parameter update.

    This mapping is approximate by design. It supplies initial values for
    optimization, not a claim that public broadcast telemetry identifies every
    physical coefficient uniquely.
    """
    mass = base.dry_mass_kg + 70.0
    inferred_power_kw = max(300.0, min(900.0, calibration.throttle_accel_gain * mass * 70.0 / 1000.0))
    inferred_drag_area = max(
        0.35,
        min(2.0, abs(calibration.drag_accel_coeff) * mass * 2.0 / 1.225),
    )
    inferred_brakes = max(12_000.0, min(40_000.0, abs(calibration.brake_decel_gain) * mass))
    return CarParameters(
        **{
            **asdict(base),
            "max_power_kw": inferred_power_kw,
            "drag_area_m2": inferred_drag_area,
            "max_brake_force_n": inferred_brakes,
        }
    )
