from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from apexsim.config import ProjectConfig


def _track_geometry(track_length_m: float, points: int, phase: float) -> pd.DataFrame:
    distance = np.linspace(0.0, track_length_m, points, endpoint=False)
    theta = 2.0 * np.pi * distance / track_length_m
    # A closed, non-circular educational track. It is not an F1 circuit replica.
    radius = 780.0 + 135.0 * np.sin(3 * theta + phase) + 70.0 * np.sin(7 * theta)
    x = radius * np.cos(theta) + 90.0 * np.sin(2 * theta)
    y = 0.78 * radius * np.sin(theta) + 65.0 * np.sin(5 * theta + phase)
    dx = np.gradient(x, distance)
    dy = np.gradient(y, distance)
    heading = np.unwrap(np.arctan2(dy, dx))
    curvature = np.abs(np.gradient(heading, distance))
    curvature /= max(float(np.quantile(curvature, 0.99)), 1e-6)
    curvature = np.clip(curvature, 0.0, 1.5)
    return pd.DataFrame(
        {
            "lap_distance_m": distance,
            "x_m": x,
            "y_m": y,
            "curvature": curvature,
            "heading": heading,
        }
    )


def _gear_from_speed(speed_mps: float) -> int:
    # Simple gear map for a teaching simulator.
    kmh = speed_mps * 3.6
    thresholds = [0, 70, 105, 140, 180, 220, 260, 300]
    return int(np.clip(np.searchsorted(thresholds, kmh, side="right"), 1, 8))


def generate_synthetic_sessions(config: ProjectConfig, output_path: str | Path) -> pd.DataFrame:
    """Generate causal F1-like telemetry with actions, weather, tyre wear, and track geometry.

    The generator gives us a controlled world where the hidden rules are known. This is invaluable
    for testing whether the pipeline and models recover cause-and-effect rather than dataset leakage.
    """
    rng = np.random.default_rng(config.seed)
    hz = config.data.sample_hz
    dt = 1.0 / hz
    frames_per_session = int(config.data.session_seconds * hz)
    output_frames: list[pd.DataFrame] = []

    for session_idx in range(config.data.sessions):
        track_id = f"synthetic_track_{session_idx % 3}"
        session_id = f"SYN_{session_idx:03d}"
        driver_id = f"DRV_{session_idx % 5:02d}"
        source = "synthetic"
        phase = (session_idx % 3) * 0.7
        geometry = _track_geometry(config.data.track_length_m, 2048, phase)

        driver_aggression = 0.93 + 0.14 * rng.random()
        driver_smoothness = 0.85 + 0.14 * rng.random()
        wet_session = rng.random() < 0.28
        rainfall_base = rng.uniform(0.18, 0.65) if wet_session else rng.uniform(0.0, 0.035)
        air_temp = rng.uniform(18.0, 31.0)
        track_temp = air_temp + rng.uniform(4.0, 18.0)
        wind = rng.uniform(0.5, 7.0)
        grip = rng.uniform(0.92, 1.06) * (1.0 - 0.35 * rainfall_base)
        compound_id = int(rng.integers(0, 3))
        tyre_deg_rate = [0.000035, 0.000022, 0.000015][compound_id]

        speed = rng.uniform(45.0, 60.0)
        distance_total = 0.0
        previous_speed = speed
        previous_heading = 0.0
        records: list[dict[str, float | int | str]] = []

        for frame_idx in range(frames_per_session):
            timestamp = frame_idx * dt
            progress = (distance_total % config.data.track_length_m) / config.data.track_length_m
            geo_idx = min(int(progress * len(geometry)), len(geometry) - 1)
            point = geometry.iloc[geo_idx]
            curvature = float(point.curvature)
            tyre_age_laps = distance_total / config.data.track_length_m
            lap_number = int(tyre_age_laps) + 1

            # Slowly changing rain lets the model learn weather-conditioned dynamics.
            rainfall = float(np.clip(rainfall_base + 0.08 * math.sin(timestamp / 38.0 + phase), 0.0, 1.0))
            effective_grip = float(np.clip(grip - tyre_deg_rate * distance_total - 0.3 * rainfall, 0.45, 1.1))
            max_corner_speed = 92.0 * effective_grip / (1.0 + 4.8 * curvature)
            straight_speed = 93.0 * driver_aggression
            target_speed = min(straight_speed, max_corner_speed)
            error = target_speed - speed

            throttle = float(np.clip(0.5 + 0.045 * error, 0.0, 1.0))
            brake = float(np.clip(-0.06 * error - 0.12, 0.0, 1.0))
            # Smooth drivers avoid violent simultaneous input changes.
            control_noise = rng.normal(0.0, 0.025 * (1.1 - driver_smoothness))
            throttle = float(np.clip(throttle + control_noise, 0.0, 1.0))
            brake = float(np.clip(brake - control_noise, 0.0, 1.0))
            drs = int(curvature < 0.07 and throttle > 0.82 and rainfall < 0.12)

            engine_accel = 13.5 * throttle * (1.0 + 0.05 * drs)
            brake_accel = 21.5 * brake
            aero_drag = 0.00145 * speed * speed
            corner_drag = 7.0 * curvature * speed / 80.0
            wet_drag = 2.0 * rainfall
            stochastic_force = rng.normal(0.0, 0.20)
            acceleration = engine_accel - brake_accel - aero_drag - corner_drag - wet_drag + stochastic_force
            speed = float(np.clip(speed + acceleration * dt, 8.0, 101.0))
            distance_total += speed * dt

            heading = float(point.heading)
            heading_change = (heading - previous_heading + np.pi) % (2 * np.pi) - np.pi
            steering_proxy = float(np.clip(heading_change / max(dt, 1e-6) / 1.8, -1.0, 1.0))
            previous_heading = heading
            gear = _gear_from_speed(speed)
            rpm = float(np.clip(4500 + 1100 * gear + 65 * speed + rng.normal(0, 180), 4000, 15000))
            acceleration_measured = (speed - previous_speed) / dt
            previous_speed = speed

            records.append(
                {
                    "session_id": session_id,
                    "source": source,
                    "track_id": track_id,
                    "driver_id": driver_id,
                    "timestamp_s": timestamp,
                    "lap_number": lap_number,
                    "speed_mps": speed,
                    "acceleration_mps2": acceleration_measured,
                    "track_progress_sin": math.sin(2 * math.pi * progress),
                    "track_progress_cos": math.cos(2 * math.pi * progress),
                    "tyre_age_laps": tyre_age_laps,
                    "throttle": throttle,
                    "brake": brake,
                    "gear_norm": gear / 8.0,
                    "drs": float(drs),
                    "steering_proxy": steering_proxy,
                    "curvature": curvature,
                    "air_temp_c": air_temp,
                    "track_temp_c": track_temp,
                    "rainfall": rainfall,
                    "wind_speed_mps": wind,
                    "grip_level": effective_grip,
                    "lap_distance_m": distance_total % config.data.track_length_m,
                    "x_m": float(point.x_m),
                    "y_m": float(point.y_m),
                    "rpm": rpm,
                    "gear": gear,
                    "compound_id": compound_id,
                    "is_pit": 0,
                    "safety_car": 0,
                }
            )

        output_frames.append(pd.DataFrame.from_records(records))

    result = pd.concat(output_frames, ignore_index=True)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    return result
