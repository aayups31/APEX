# `apex_engine/src/apexsim/data/synthetic.py`

**Role:** Creates a controlled causal telemetry world for offline learning and tests.

Synthetic data is used to verify contracts and interventions, not to justify real-world accuracy claims.

## Line-by-line guide

### Line 1
```python
from __future__ import annotations
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 2
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 3
```python
import math
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 4
```python
from pathlib import Path
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 5
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 6
```python
import numpy as np
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 7
```python
import pandas as pd
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 8
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 9
```python
from apexsim.config import ProjectConfig
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 10
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 11
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 12
```python
def _track_geometry(track_length_m: float, points: int, phase: float) -> pd.DataFrame:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 13
```python
    distance = np.linspace(0.0, track_length_m, points, endpoint=False)
```
Creates or updates `distance`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 14
```python
    theta = 2.0 * np.pi * distance / track_length_m
```
Creates or updates `theta`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 15
```python
    # A closed, non-circular educational track. It is not an F1 circuit replica.
```
Documents an assumption, intent or constraint that should remain aligned with the implementation.

### Line 16
```python
    radius = 780.0 + 135.0 * np.sin(3 * theta + phase) + 70.0 * np.sin(7 * theta)
```
Creates or updates `radius`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 17
```python
    x = radius * np.cos(theta) + 90.0 * np.sin(2 * theta)
```
Creates or updates `x`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 18
```python
    y = 0.78 * radius * np.sin(theta) + 65.0 * np.sin(5 * theta + phase)
```
Creates or updates `y`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 19
```python
    dx = np.gradient(x, distance)
```
Creates or updates `dx`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 20
```python
    dy = np.gradient(y, distance)
```
Creates or updates `dy`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 21
```python
    heading = np.unwrap(np.arctan2(dy, dx))
```
Creates or updates `heading`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 22
```python
    curvature = np.abs(np.gradient(heading, distance))
```
Creates or updates `curvature`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 23
```python
    curvature /= max(float(np.quantile(curvature, 0.99)), 1e-6)
```
Creates or updates `curvature /`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 24
```python
    curvature = np.clip(curvature, 0.0, 1.5)
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 25
```python
    return pd.DataFrame(
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 26
```python
        {
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 27
```python
            "lap_distance_m": distance,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 28
```python
            "x_m": x,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 29
```python
            "y_m": y,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 30
```python
            "curvature": curvature,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 31
```python
            "heading": heading,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 32
```python
        }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 33
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 34
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 35
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 36
```python
def _gear_from_speed(speed_mps: float) -> int:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 37
```python
    # Simple gear map for a teaching simulator.
```
Documents an assumption, intent or constraint that should remain aligned with the implementation.

### Line 38
```python
    kmh = speed_mps * 3.6
```
Creates or updates `kmh`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 39
```python
    thresholds = [0, 70, 105, 140, 180, 220, 260, 300]
```
Creates or updates `thresholds`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 40
```python
    return int(np.clip(np.searchsorted(thresholds, kmh, side="right"), 1, 8))
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 41
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 42
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 43
```python
def generate_synthetic_sessions(config: ProjectConfig, output_path: str | Path) -> pd.DataFrame:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 44
```python
    """Generate causal F1-like telemetry with actions, weather, tyre wear, and track geometry.
```
Begins or ends documentation describing the module, class or function contract.

### Line 45
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 46
```python
    The generator gives us a controlled world where the hidden rules are known. This is invaluable
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 47
```python
    for testing whether the pipeline and models recover cause-and-effect rather than dataset leakage.
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 48
```python
    """
```
Begins or ends documentation describing the module, class or function contract.

### Line 49
```python
    rng = np.random.default_rng(config.seed)
```
Creates or updates `rng`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 50
```python
    hz = config.data.sample_hz
```
Creates or updates `hz`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 51
```python
    dt = 1.0 / hz
```
Creates or updates `dt`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 52
```python
    frames_per_session = int(config.data.session_seconds * hz)
```
Creates or updates `frames_per_session`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 53
```python
    output_frames: list[pd.DataFrame] = []
```
Creates or updates `output_frames: list[pd.DataFrame]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 54
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 55
```python
    for session_idx in range(config.data.sessions):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 56
```python
        track_id = f"synthetic_track_{session_idx % 3}"
```
Creates or updates `track_id`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 57
```python
        session_id = f"SYN_{session_idx:03d}"
```
Creates or updates `session_id`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 58
```python
        driver_id = f"DRV_{session_idx % 5:02d}"
```
Creates or updates `driver_id`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 59
```python
        source = "synthetic"
```
Creates or updates `source`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 60
```python
        phase = (session_idx % 3) * 0.7
```
Creates or updates `phase`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 61
```python
        geometry = _track_geometry(config.data.track_length_m, 2048, phase)
```
Creates or updates `geometry`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 62
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 63
```python
        driver_aggression = 0.93 + 0.14 * rng.random()
```
Creates or updates `driver_aggression`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 64
```python
        driver_smoothness = 0.85 + 0.14 * rng.random()
```
Creates or updates `driver_smoothness`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 65
```python
        wet_session = rng.random() < 0.28
```
Creates or updates `wet_session`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 66
```python
        rainfall_base = rng.uniform(0.18, 0.65) if wet_session else rng.uniform(0.0, 0.035)
```
Creates or updates `rainfall_base`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 67
```python
        air_temp = rng.uniform(18.0, 31.0)
```
Creates or updates `air_temp`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 68
```python
        track_temp = air_temp + rng.uniform(4.0, 18.0)
```
Creates or updates `track_temp`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 69
```python
        wind = rng.uniform(0.5, 7.0)
```
Creates or updates `wind`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 70
```python
        grip = rng.uniform(0.92, 1.06) * (1.0 - 0.35 * rainfall_base)
```
Creates or updates `grip`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 71
```python
        compound_id = int(rng.integers(0, 3))
```
Creates or updates `compound_id`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 72
```python
        tyre_deg_rate = [0.000035, 0.000022, 0.000015][compound_id]
```
Creates or updates `tyre_deg_rate`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 73
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 74
```python
        speed = rng.uniform(45.0, 60.0)
```
Creates or updates `speed`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 75
```python
        distance_total = 0.0
```
Creates or updates `distance_total`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 76
```python
        previous_speed = speed
```
Creates or updates `previous_speed`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 77
```python
        previous_heading = 0.0
```
Creates or updates `previous_heading`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 78
```python
        records: list[dict[str, float | int | str]] = []
```
Creates or updates `records: list[dict[str, float | int | str]]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 79
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 80
```python
        for frame_idx in range(frames_per_session):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 81
```python
            timestamp = frame_idx * dt
```
Creates or updates `timestamp`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 82
```python
            progress = (distance_total % config.data.track_length_m) / config.data.track_length_m
```
Creates or updates `progress`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 83
```python
            geo_idx = min(int(progress * len(geometry)), len(geometry) - 1)
```
Creates or updates `geo_idx`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 84
```python
            point = geometry.iloc[geo_idx]
```
Creates or updates `point`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 85
```python
            curvature = float(point.curvature)
```
Creates or updates `curvature`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 86
```python
            tyre_age_laps = distance_total / config.data.track_length_m
```
Creates or updates `tyre_age_laps`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 87
```python
            lap_number = int(tyre_age_laps) + 1
```
Creates or updates `lap_number`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 88
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 89
```python
            # Slowly changing rain lets the model learn weather-conditioned dynamics.
```
Documents an assumption, intent or constraint that should remain aligned with the implementation.

### Line 90
```python
            rainfall = float(np.clip(rainfall_base + 0.08 * math.sin(timestamp / 38.0 + phase), 0.0, 1.0))
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 91
```python
            effective_grip = float(np.clip(grip - tyre_deg_rate * distance_total - 0.3 * rainfall, 0.45, 1.1))
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 92
```python
            max_corner_speed = 92.0 * effective_grip / (1.0 + 4.8 * curvature)
```
Creates or updates `max_corner_speed`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 93
```python
            straight_speed = 93.0 * driver_aggression
```
Creates or updates `straight_speed`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 94
```python
            target_speed = min(straight_speed, max_corner_speed)
```
Creates or updates `target_speed`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 95
```python
            error = target_speed - speed
```
Creates or updates `error`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 96
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 97
```python
            throttle = float(np.clip(0.5 + 0.045 * error, 0.0, 1.0))
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 98
```python
            brake = float(np.clip(-0.06 * error - 0.12, 0.0, 1.0))
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 99
```python
            # Smooth drivers avoid violent simultaneous input changes.
```
Documents an assumption, intent or constraint that should remain aligned with the implementation.

### Line 100
```python
            control_noise = rng.normal(0.0, 0.025 * (1.1 - driver_smoothness))
```
Creates or updates `control_noise`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 101
```python
            throttle = float(np.clip(throttle + control_noise, 0.0, 1.0))
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 102
```python
            brake = float(np.clip(brake - control_noise, 0.0, 1.0))
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 103
```python
            drs = int(curvature < 0.07 and throttle > 0.82 and rainfall < 0.12)
```
Creates or updates `drs`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 104
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 105
```python
            engine_accel = 13.5 * throttle * (1.0 + 0.05 * drs)
```
Creates or updates `engine_accel`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 106
```python
            brake_accel = 21.5 * brake
```
Creates or updates `brake_accel`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 107
```python
            aero_drag = 0.00145 * speed * speed
```
Creates or updates `aero_drag`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 108
```python
            corner_drag = 7.0 * curvature * speed / 80.0
```
Creates or updates `corner_drag`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 109
```python
            wet_drag = 2.0 * rainfall
```
Creates or updates `wet_drag`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 110
```python
            stochastic_force = rng.normal(0.0, 0.20)
```
Creates or updates `stochastic_force`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 111
```python
            acceleration = engine_accel - brake_accel - aero_drag - corner_drag - wet_drag + stochastic_force
```
Creates or updates `acceleration`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 112
```python
            speed = float(np.clip(speed + acceleration * dt, 8.0, 101.0))
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 113
```python
            distance_total += speed * dt
```
Creates or updates `distance_total +`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 114
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 115
```python
            heading = float(point.heading)
```
Creates or updates `heading`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 116
```python
            heading_change = (heading - previous_heading + np.pi) % (2 * np.pi) - np.pi
```
Creates or updates `heading_change`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 117
```python
            steering_proxy = float(np.clip(heading_change / max(dt, 1e-6) / 1.8, -1.0, 1.0))
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 118
```python
            previous_heading = heading
```
Creates or updates `previous_heading`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 119
```python
            gear = _gear_from_speed(speed)
```
Creates or updates `gear`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 120
```python
            rpm = float(np.clip(4500 + 1100 * gear + 65 * speed + rng.normal(0, 180), 4000, 15000))
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 121
```python
            acceleration_measured = (speed - previous_speed) / dt
```
Creates or updates `acceleration_measured`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 122
```python
            previous_speed = speed
```
Creates or updates `previous_speed`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 123
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 124
```python
            records.append(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 125
```python
                {
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 126
```python
                    "session_id": session_id,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 127
```python
                    "source": source,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 128
```python
                    "track_id": track_id,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 129
```python
                    "driver_id": driver_id,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 130
```python
                    "timestamp_s": timestamp,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 131
```python
                    "lap_number": lap_number,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 132
```python
                    "speed_mps": speed,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 133
```python
                    "acceleration_mps2": acceleration_measured,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 134
```python
                    "track_progress_sin": math.sin(2 * math.pi * progress),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 135
```python
                    "track_progress_cos": math.cos(2 * math.pi * progress),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 136
```python
                    "tyre_age_laps": tyre_age_laps,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 137
```python
                    "throttle": throttle,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 138
```python
                    "brake": brake,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 139
```python
                    "gear_norm": gear / 8.0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 140
```python
                    "drs": float(drs),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 141
```python
                    "steering_proxy": steering_proxy,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 142
```python
                    "curvature": curvature,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 143
```python
                    "air_temp_c": air_temp,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 144
```python
                    "track_temp_c": track_temp,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 145
```python
                    "rainfall": rainfall,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 146
```python
                    "wind_speed_mps": wind,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 147
```python
                    "grip_level": effective_grip,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 148
```python
                    "lap_distance_m": distance_total % config.data.track_length_m,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 149
```python
                    "x_m": float(point.x_m),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 150
```python
                    "y_m": float(point.y_m),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 151
```python
                    "rpm": rpm,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 152
```python
                    "gear": gear,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 153
```python
                    "compound_id": compound_id,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 154
```python
                    "is_pit": 0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 155
```python
                    "safety_car": 0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 156
```python
                }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 157
```python
            )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 158
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 159
```python
        output_frames.append(pd.DataFrame.from_records(records))
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 160
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 161
```python
    result = pd.concat(output_frames, ignore_index=True)
```
Concatenates tensors or arrays; verify that every non-concatenated axis has identical meaning and size.

### Line 162
```python
    output = Path(output_path)
```
Creates or updates `output`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 163
```python
    output.parent.mkdir(parents=True, exist_ok=True)
```
Creates or updates `output.parent.mkdir(parents`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 164
```python
    result.to_csv(output, index=False)
```
Persists an artifact. The surrounding code should include run identity, schema and preprocessing lineage.

### Line 165
```python
    return result
```
Returns the result to the caller; this is the function output boundary that tests should assert.
