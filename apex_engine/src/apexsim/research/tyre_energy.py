"""Physics-guided tyre-energy proxies and data contracts.

Todd et al. (2025) forecast four wheel-specific tyre energies from telemetry.
Their true targets are computed from proprietary wheel-force/slip models. APEX
therefore exposes two target levels:

* ``measured``: future game/DIL/team telemetry supplies wheel force and slip;
* ``proxy``: this transparent load-transfer and sliding-power approximation.

Proxy outputs are useful for software verification and controlled experiments,
but must never be presented as the paper's proprietary ground truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd

WHEEL_NAMES = ("front_left", "front_right", "rear_left", "rear_right")


@dataclass(frozen=True)
class TyreEnergyInputs:
    speed_mps: float
    longitudinal_accel_mps2: float
    lateral_accel_mps2: float
    steering_rad: float
    throttle: float
    brake: float
    dt_s: float
    mass_kg: float = 900.0
    wheelbase_m: float = 3.60
    track_width_m: float = 2.00
    cg_height_m: float = 0.32
    front_weight_fraction: float = 0.46
    aero_load_n: float = 0.0
    front_aero_fraction: float = 0.46
    driven_rear_fraction: float = 1.0
    brake_front_fraction: float = 0.58


@dataclass(frozen=True)
class WheelTyreEnergy:
    front_left_kj: float
    front_right_kj: float
    rear_left_kj: float
    rear_right_kj: float

    def as_array(self) -> np.ndarray:
        return np.asarray(
            [self.front_left_kj, self.front_right_kj, self.rear_left_kj, self.rear_right_kj],
            dtype=np.float64,
        )

    def as_dict(self) -> dict[str, float]:
        return dict(zip(WHEEL_NAMES, self.as_array().tolist(), strict=True))


def _normal_loads(x: TyreEnergyInputs) -> np.ndarray:
    g = 9.81
    total_static = x.mass_kg * g + max(x.aero_load_n, 0.0)
    front_total = x.front_weight_fraction * x.mass_kg * g + x.front_aero_fraction * max(x.aero_load_n, 0.0)
    rear_total = total_static - front_total

    longitudinal_transfer = x.mass_kg * x.longitudinal_accel_mps2 * x.cg_height_m / max(x.wheelbase_m, 1e-6)
    front_total -= longitudinal_transfer
    rear_total += longitudinal_transfer

    lateral_transfer_total = x.mass_kg * x.lateral_accel_mps2 * x.cg_height_m / max(x.track_width_m, 1e-6)
    front_transfer = x.front_weight_fraction * lateral_transfer_total
    rear_transfer = (1.0 - x.front_weight_fraction) * lateral_transfer_total

    # Positive lateral acceleration loads the left wheels in this convention.
    loads = np.asarray(
        [
            0.5 * front_total + 0.5 * front_transfer,
            0.5 * front_total - 0.5 * front_transfer,
            0.5 * rear_total + 0.5 * rear_transfer,
            0.5 * rear_total - 0.5 * rear_transfer,
        ],
        dtype=np.float64,
    )
    return np.clip(loads, 50.0, None)


def estimate_wheel_tyre_energy(inputs: TyreEnergyInputs) -> WheelTyreEnergy:
    """Estimate per-wheel sliding energy over one sample in kilojoules.

    The proxy is deterministic, non-negative, load-sensitive and directionally
    responsive. It is intentionally compact enough to identify from controlled
    game experiments later.
    """
    x = inputs
    if x.dt_s <= 0:
        raise ValueError("dt_s must be positive")
    if x.mass_kg <= 0:
        raise ValueError("mass_kg must be positive")

    throttle = float(np.clip(x.throttle, 0.0, 1.0))
    brake = float(np.clip(x.brake, 0.0, 1.0))
    loads = _normal_loads(x)
    load_share = loads / loads.sum()

    total_longitudinal_force = x.mass_kg * x.longitudinal_accel_mps2
    if brake > throttle:
        axle_distribution = np.asarray(
            [x.brake_front_fraction / 2, x.brake_front_fraction / 2,
             (1 - x.brake_front_fraction) / 2, (1 - x.brake_front_fraction) / 2]
        )
    else:
        rear = float(np.clip(x.driven_rear_fraction, 0.0, 1.0))
        axle_distribution = np.asarray([(1 - rear) / 2, (1 - rear) / 2, rear / 2, rear / 2])
    fx = total_longitudinal_force * axle_distribution

    total_lateral_force = x.mass_kg * x.lateral_accel_mps2
    fy = total_lateral_force * load_share

    speed = max(abs(x.speed_mps), 0.0)
    control_mismatch = abs(throttle - brake)
    longitudinal_slip_speed = speed * (0.002 + 0.018 * brake**1.5 + 0.010 * throttle**1.5 + 0.004 * control_mismatch)
    steer_demand = abs(x.steering_rad) * speed
    lateral_slip_base = 0.010 * speed + 0.11 * steer_demand + 0.015 * abs(x.lateral_accel_mps2) * speed / 9.81
    # Front tyres receive more steering-induced slip; outside tyres receive more load-related slip.
    lateral_slip = np.asarray([1.25, 1.25, 0.78, 0.78]) * lateral_slip_base
    load_nonlinearity = np.power(loads / max(loads.mean(), 1e-9), 0.18)

    sliding_power_w = (np.abs(fx) * longitudinal_slip_speed + np.abs(fy) * lateral_slip) * load_nonlinearity
    energies_kj = np.clip(sliding_power_w * x.dt_s / 1000.0, 0.0, None)
    return WheelTyreEnergy(*map(float, energies_kj))


def augment_with_proxy_tyre_energy(
    frame: pd.DataFrame,
    column_map: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Add four proxy target columns to a telemetry frame.

    Required canonical meanings are speed, longitudinal/lateral acceleration,
    steering, throttle, brake and sample duration. ``column_map`` maps those
    canonical names to actual frame columns.
    """
    mapping = {
        "speed_mps": "speed_mps",
        "longitudinal_accel_mps2": "acceleration_mps2",
        "lateral_accel_mps2": "lateral_acceleration_mps2",
        "steering_rad": "steering",
        "throttle": "throttle",
        "brake": "brake",
        "dt_s": "dt_s",
        "mass_kg": "mass_kg",
        "aero_load_n": "downforce_n",
    }
    if column_map:
        mapping.update(column_map)
    required = [mapping[k] for k in (
        "speed_mps", "longitudinal_accel_mps2", "lateral_accel_mps2",
        "steering_rad", "throttle", "brake", "dt_s",
    )]
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError(f"Missing telemetry columns for tyre-energy proxy: {missing}")

    out = frame.copy()
    rows = []
    for row in out.itertuples(index=False):
        data = row._asdict()
        estimate = estimate_wheel_tyre_energy(
            TyreEnergyInputs(
                speed_mps=float(data[mapping["speed_mps"]]),
                longitudinal_accel_mps2=float(data[mapping["longitudinal_accel_mps2"]]),
                lateral_accel_mps2=float(data[mapping["lateral_accel_mps2"]]),
                steering_rad=float(data[mapping["steering_rad"]]),
                throttle=float(data[mapping["throttle"]]),
                brake=float(data[mapping["brake"]]),
                dt_s=float(data[mapping["dt_s"]]),
                mass_kg=float(data.get(mapping["mass_kg"], 900.0)),
                aero_load_n=float(data.get(mapping["aero_load_n"], 0.0)),
            )
        )
        rows.append(estimate.as_array())
    values = np.vstack(rows) if rows else np.empty((0, 4))
    for idx, name in enumerate(WHEEL_NAMES):
        out[f"tyre_energy_{name}_kj"] = values[:, idx]
    out["tyre_energy_target_quality"] = "PROXY_NOT_MEASURED"
    return out
