from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from apexsim.sim_core.track import TrackMap
from apexsim.sim_core.types import (
    CarParameters,
    CarState,
    Control,
    DriverParameters,
    EnvironmentState,
    TyreCompound,
)
from apexsim.sim_core.vehicle import VehicleDynamics


@dataclass(frozen=True)
class ReplayMetrics:
    speed_mae_mps: float
    speed_rmse_mps: float
    acceleration_mae_mps2: float
    final_distance_error_m: float
    samples: int

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def replay_controls(
    frame: pd.DataFrame,
    car: CarParameters | None = None,
    driver: DriverParameters | None = None,
    dt_s: float | None = None,
) -> tuple[pd.DataFrame, ReplayMetrics]:
    """Replay recorded public controls through the causal dynamics model.

    This is the first serious calibration test. A model that cannot reproduce a
    recorded lap under recorded controls is not ready for counterfactual claims.
    """
    required = {
        "timestamp_s",
        "lap_distance_m",
        "x_m",
        "y_m",
        "speed_mps",
        "acceleration_mps2",
        "throttle",
        "brake",
        "drs",
        "steering_proxy",
        "air_temp_c",
        "track_temp_c",
        "rainfall",
        "wind_speed_mps",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Canonical replay frame missing columns: {sorted(missing)}")
    clean = frame.sort_values("timestamp_s").dropna(subset=list(required)).copy()
    if len(clean) < 20:
        raise ValueError("Replay needs at least 20 telemetry rows")
    track = TrackMap.from_canonical_telemetry(clean, bins=min(1200, max(100, len(clean) // 2)))
    car = car or CarParameters()
    driver = driver or DriverParameters("replay_driver", consistency=1.0)
    if dt_s is None:
        dt_s = float(clean.timestamp_s.diff().dropna().median())
    first = clean.iloc[0]
    compound_name = str(first.get("compound", "MEDIUM")).upper()
    try:
        compound = TyreCompound(compound_name)
    except ValueError:
        compound = TyreCompound.MEDIUM
    state = CarState(
        car_id="replay",
        driver_id=driver.name,
        s_m=float(first.lap_distance_m),
        speed_mps=float(first.speed_mps),
        fuel_kg=car.fuel_capacity_kg * 0.75,
        battery_mj=car.ers_capacity_mj,
        tyre_compound=compound,
        tyre_age_laps=float(first.get("tyre_age_laps", 0.0)),
        total_distance_m=float(first.lap_distance_m),
    )
    dynamics = VehicleDynamics()
    rows = []
    for _, observed in clean.iloc[:-1].iterrows():
        environment = EnvironmentState(
            air_temp_c=float(observed.air_temp_c),
            track_temp_c=float(observed.track_temp_c),
            rain_intensity=float(observed.rainfall),
            wind_speed_mps=float(observed.wind_speed_mps),
            surface_grip=float(observed.get("grip_level", 1.0)),
        )
        control = Control(
            throttle=float(observed.throttle),
            brake=float(observed.brake),
            steering=float(observed.steering_proxy),
            ers_deploy=0.2 + 0.6 * float(observed.throttle),
            drs=bool(observed.drs),
        )
        state, diagnostics = dynamics.step(
            state,
            control,
            car,
            driver,
            track,
            environment,
            dt_s,
            gap_ahead_m=None,
            drs_eligible=True,
        )
        rows.append(
            {
                "timestamp_s": state.time_s,
                "sim_speed_mps": state.speed_mps,
                "sim_acceleration_mps2": diagnostics.acceleration_mps2,
                "sim_distance_m": state.total_distance_m,
            }
        )
    simulated = pd.DataFrame(rows)
    observed = clean.iloc[1 : 1 + len(simulated)].reset_index(drop=True)
    simulated["observed_speed_mps"] = observed.speed_mps
    simulated["observed_acceleration_mps2"] = observed.acceleration_mps2
    simulated["observed_distance_m"] = observed.lap_distance_m
    speed_error = simulated.sim_speed_mps - simulated.observed_speed_mps
    accel_error = simulated.sim_acceleration_mps2 - simulated.observed_acceleration_mps2
    metrics = ReplayMetrics(
        speed_mae_mps=float(np.mean(np.abs(speed_error))),
        speed_rmse_mps=float(np.sqrt(np.mean(speed_error**2))),
        acceleration_mae_mps2=float(np.mean(np.abs(accel_error))),
        final_distance_error_m=float(simulated.sim_distance_m.iloc[-1] - simulated.observed_distance_m.iloc[-1]),
        samples=len(simulated),
    )
    return simulated, metrics
