from __future__ import annotations

import math

import numpy as np

from apexsim.sim_core.track import TrackMap
from apexsim.sim_core.tyres import effective_tyre_grip, update_tyre
from apexsim.sim_core.types import (
    CarParameters,
    CarState,
    Control,
    DriverParameters,
    EnvironmentState,
    FlagState,
    StepDiagnostics,
)


class VehicleDynamics:
    """Semi-empirical point-mass race-car dynamics.

    The purpose is not to pretend public data can reproduce a confidential team
    simulator. It supplies a causal, inspectable prior whose parameters can be
    calibrated and whose residual error can be learned by APEX's world model.
    """

    air_density_kgpm3 = 1.225
    gravity_mps2 = 9.81

    def speed_limit_for_curvature(
        self,
        state: CarState,
        car: CarParameters,
        track: TrackMap,
        environment: EnvironmentState,
    ) -> float:
        curvature = max(abs(track.lookahead_curvature(state.s_m, 100.0, 6)), 1e-6)
        grip = effective_tyre_grip(
            state.tyre_compound,
            state.tyre_temp_c,
            state.tyre_health,
            environment,
        )
        # Solve v^2*kappa <= mu*(g + downforce/m). A few fixed-point iterations are enough.
        mass = max(car.dry_mass_kg + state.fuel_kg, 1.0)
        speed = math.sqrt(max(grip * self.gravity_mps2 / curvature, 1.0))
        for _ in range(4):
            downforce = 0.5 * self.air_density_kgpm3 * car.downforce_area_m2 * speed**2
            lateral_limit = grip * (self.gravity_mps2 + downforce / mass)
            speed = math.sqrt(max(lateral_limit / curvature, 1.0))
        return float(np.clip(speed, 8.0, 110.0))

    def step(
        self,
        state: CarState,
        control: Control,
        car: CarParameters,
        driver: DriverParameters,
        track: TrackMap,
        environment: EnvironmentState,
        dt_s: float,
        gap_ahead_m: float | None = None,
        drs_eligible: bool = False,
    ) -> tuple[CarState, StepDiagnostics]:
        control = control.clipped()
        if state.retired or state.finished:
            diagnostics = StepDiagnostics(
                acceleration_mps2=0.0,
                longitudinal_force_n=0.0,
                traction_limit_n=0.0,
                drag_n=0.0,
                rolling_resistance_n=0.0,
                downforce_n=0.0,
                lateral_acceleration_mps2=0.0,
                effective_grip=0.0,
                tyre_wear_delta=0.0,
                fuel_burn_kg=0.0,
                battery_delta_mj=0.0,
                speed_limit_mps=0.0,
                dirty_air_factor=1.0,
                drs_active=False,
            )
            return state.clone(time_s=state.time_s + dt_s), diagnostics

        mass = max(car.dry_mass_kg + state.fuel_kg, 1.0)
        speed = max(state.speed_mps, 0.0)
        track_sample = track.sample(state.s_m)
        curvature = abs(track_sample.curvature_1pm)
        slope = track.gradient(state.s_m)

        dirty_air_factor = 1.0
        if gap_ahead_m is not None and 0.0 < gap_ahead_m < 80.0:
            dirty_air_factor = 1.0 - car.dirty_air_downforce_loss_max * math.exp(-gap_ahead_m / 24.0)
        drs_active = bool(control.drs and drs_eligible and track_sample.drs_allowed and environment.flag == FlagState.GREEN)
        drag_area = car.drag_area_m2 * (1.0 - car.drs_drag_reduction if drs_active else 1.0)
        downforce = 0.5 * self.air_density_kgpm3 * car.downforce_area_m2 * speed**2 * dirty_air_factor
        normal_force = mass * self.gravity_mps2 + downforce
        grip = effective_tyre_grip(
            state.tyre_compound,
            state.tyre_temp_c,
            state.tyre_health,
            environment,
        )
        lateral_accel = speed**2 * curvature
        lateral_force = mass * lateral_accel
        total_friction = max(grip * normal_force, 1.0)
        lateral_fraction = float(np.clip(abs(lateral_force) / total_friction, 0.0, 0.995))
        longitudinal_fraction = math.sqrt(max(1.0 - lateral_fraction**2, 0.01))
        traction_limit = total_friction * longitudinal_fraction

        power_w = car.max_power_kw * 1000.0 * car.drivetrain_efficiency
        engine_force = min(power_w / max(speed, 8.0), traction_limit)
        battery_available = max(state.battery_mj, 0.0)
        ers_power_w = car.ers_max_deploy_kw * 1000.0 * control.ers_deploy if battery_available > 0.01 else 0.0
        ers_force = min(ers_power_w / max(speed, 8.0), max(traction_limit - engine_force, 0.0))
        drive_force = control.throttle * min(engine_force + ers_force, traction_limit)
        brake_force = control.brake * min(car.max_brake_force_n, traction_limit)
        drag = 0.5 * self.air_density_kgpm3 * drag_area * speed**2
        rolling = car.rolling_resistance_coeff * mass * self.gravity_mps2
        grade_force = mass * self.gravity_mps2 * slope
        net_force = drive_force - brake_force - drag - rolling - grade_force
        acceleration = net_force / mass

        if environment.flag == FlagState.RED:
            acceleration = min(acceleration, -8.0 if speed > 0.5 else 0.0)
        new_speed = max(0.0, speed + acceleration * dt_s)
        speed_limit = self.speed_limit_for_curvature(state, car, track, environment)
        # This soft limiter protects numerical stability while preserving overspeed penalties.
        if new_speed > speed_limit:
            new_speed = max(speed_limit, new_speed - (new_speed - speed_limit) * min(1.0, 2.8 * dt_s))
        average_speed = 0.5 * (speed + new_speed)
        distance = max(average_speed * dt_s, 0.0)

        tyre = update_tyre(
            state.tyre_compound,
            state.tyre_temp_c,
            state.tyre_health,
            distance,
            new_speed,
            lateral_accel,
            control.brake,
            control.throttle,
            environment,
            driver.tyre_management,
        )
        fuel_burn = min(
            state.fuel_kg,
            car.fuel_burn_kg_per_km * (distance / 1000.0) * (0.35 + 0.65 * control.throttle),
        )
        deployment_mj = ers_power_w * dt_s / 1_000_000.0
        harvest_power_w = car.ers_max_harvest_kw * 1000.0 * control.brake * 0.55
        harvest_mj = harvest_power_w * dt_s / 1_000_000.0
        battery_delta = harvest_mj - deployment_mj
        battery = float(np.clip(state.battery_mj + battery_delta, 0.0, car.ers_capacity_mj))

        raw_s = state.s_m + distance
        completed_lap = raw_s >= track.length_m
        lap = state.lap + int(completed_lap)
        wrapped_s = raw_s % track.length_m
        total_distance = state.total_distance_m + distance
        tyre_age = state.tyre_age_laps + distance / track.length_m
        last_lap_time = state.last_lap_time_s
        lap_start = state.current_lap_start_s
        if completed_lap:
            last_lap_time = state.time_s + dt_s - state.current_lap_start_s
            lap_start = state.time_s + dt_s

        reliability = car.reliability_per_hour ** (dt_s / 3600.0)
        random_failure = np.random.default_rng(driver.seed + int(state.time_s * 5) + state.lap * 1009).random() > reliability
        retired = bool(state.retired or random_failure or state.damage >= 1.0)

        next_state = state.clone(
            time_s=state.time_s + dt_s,
            lap=lap,
            s_m=wrapped_s,
            speed_mps=new_speed,
            fuel_kg=max(0.0, state.fuel_kg - fuel_burn),
            battery_mj=battery,
            tyre_age_laps=tyre_age,
            tyre_health=tyre.health,
            tyre_temp_c=tyre.temperature_c,
            total_distance_m=total_distance,
            last_lap_time_s=last_lap_time,
            current_lap_start_s=lap_start,
            retired=retired,
        )
        diagnostics = StepDiagnostics(
            acceleration_mps2=float(acceleration),
            longitudinal_force_n=float(net_force),
            traction_limit_n=float(traction_limit),
            drag_n=float(drag),
            rolling_resistance_n=float(rolling),
            downforce_n=float(downforce),
            lateral_acceleration_mps2=float(lateral_accel),
            effective_grip=float(grip),
            tyre_wear_delta=float(tyre.wear_delta),
            fuel_burn_kg=float(fuel_burn),
            battery_delta_mj=float(battery_delta),
            speed_limit_mps=float(speed_limit),
            dirty_air_factor=float(dirty_air_factor),
            drs_active=drs_active,
        )
        return next_state, diagnostics
