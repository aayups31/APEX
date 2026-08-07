from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from apexsim.sim_core.types import EnvironmentState, TyreCompound


@dataclass(frozen=True)
class TyreSpec:
    dry_grip: float
    wet_grip: float
    optimum_temp_c: float
    temp_window_c: float
    warmup_rate: float
    cooling_rate: float
    base_wear_per_km: float
    cliff_health: float


TYRE_SPECS: dict[TyreCompound, TyreSpec] = {
    TyreCompound.SOFT: TyreSpec(1.08, 0.42, 98.0, 18.0, 0.95, 0.42, 0.0045, 0.30),
    TyreCompound.MEDIUM: TyreSpec(1.03, 0.44, 94.0, 20.0, 0.78, 0.40, 0.0031, 0.25),
    TyreCompound.HARD: TyreSpec(0.99, 0.46, 90.0, 23.0, 0.62, 0.38, 0.0022, 0.20),
    TyreCompound.INTERMEDIATE: TyreSpec(0.82, 0.96, 72.0, 18.0, 0.72, 0.55, 0.0030, 0.24),
    TyreCompound.WET: TyreSpec(0.68, 1.02, 62.0, 20.0, 0.58, 0.62, 0.0025, 0.20),
}


@dataclass(frozen=True)
class TyreUpdate:
    temperature_c: float
    health: float
    grip: float
    wear_delta: float


def effective_tyre_grip(
    compound: TyreCompound,
    temperature_c: float,
    health: float,
    environment: EnvironmentState,
) -> float:
    spec = TYRE_SPECS[compound]
    wetness = float(np.clip(max(environment.rain_intensity, environment.standing_water), 0.0, 1.0))
    base = (1.0 - wetness) * spec.dry_grip + wetness * spec.wet_grip
    temp_error = abs(temperature_c - spec.optimum_temp_c)
    temperature_factor = float(np.exp(-0.5 * (temp_error / spec.temp_window_c) ** 2))
    temperature_factor = 0.72 + 0.28 * temperature_factor
    health = float(np.clip(health, 0.02, 1.0))
    cliff = 1.0 if health >= spec.cliff_health else 0.72 + 0.28 * health / max(spec.cliff_health, 1e-6)
    return float(base * temperature_factor * (0.76 + 0.24 * health) * cliff * environment.surface_grip)


def update_tyre(
    compound: TyreCompound,
    temperature_c: float,
    health: float,
    distance_m: float,
    speed_mps: float,
    lateral_accel_mps2: float,
    brake: float,
    throttle: float,
    environment: EnvironmentState,
    tyre_management: float = 0.7,
) -> TyreUpdate:
    spec = TYRE_SPECS[compound]
    wetness = float(np.clip(max(environment.rain_intensity, environment.standing_water), 0.0, 1.0))
    work = (
        0.20 * abs(lateral_accel_mps2) / 9.81
        + 0.22 * brake
        + 0.12 * throttle
        + 0.08 * speed_mps / 90.0
    )
    target_temp = environment.track_temp_c + 43.0 + 32.0 * work
    if compound in {TyreCompound.INTERMEDIATE, TyreCompound.WET}:
        target_temp -= 14.0 * wetness
    heat_rate = spec.warmup_rate * (0.15 + work)
    cooling = spec.cooling_rate * (0.2 + wetness)
    dt_proxy = max(distance_m / max(speed_mps, 5.0), 0.0)
    new_temp = temperature_c + (target_temp - temperature_c) * min(heat_rate * dt_proxy * 0.06, 0.25)
    new_temp -= cooling * max(temperature_c - environment.air_temp_c, 0.0) * dt_proxy * 0.002

    management_factor = 1.18 - 0.35 * float(np.clip(tyre_management, 0.0, 1.0))
    abuse = 1.0 + 0.75 * brake**2 + 0.45 * throttle**2 + 0.60 * abs(lateral_accel_mps2) / 9.81
    mismatch = 1.0
    if wetness > 0.25 and compound in {TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD}:
        mismatch += 0.65 * wetness
    if wetness < 0.08 and compound in {TyreCompound.INTERMEDIATE, TyreCompound.WET}:
        mismatch += 0.8
    wear_delta = spec.base_wear_per_km * (distance_m / 1000.0) * abuse * management_factor * mismatch
    new_health = float(np.clip(health - wear_delta, 0.01, 1.0))
    grip = effective_tyre_grip(compound, new_temp, new_health, environment)
    return TyreUpdate(float(new_temp), new_health, grip, float(wear_delta))
