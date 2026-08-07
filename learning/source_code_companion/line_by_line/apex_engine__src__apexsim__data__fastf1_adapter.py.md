# `apex_engine/src/apexsim/data/fastf1_adapter.py`

**Role:** Converts FastF1 session objects into the canonical telemetry contract.

Source-specific names, rates and units end here; downstream model code must not depend on FastF1 internals.

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
from pathlib import Path
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 4
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 5
```python
import numpy as np
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 6
```python
import pandas as pd
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 7
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 8
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 9
```python
def ingest_fastf1_session(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 10
```python
    year: int,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 11
```python
    event: str,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 12
```python
    session_code: str,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 13
```python
    driver: str,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 14
```python
    output_path: str | Path,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 15
```python
    sample_hz: int = 5,
```
Creates or updates `sample_hz: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 16
```python
) -> pd.DataFrame:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 17
```python
    """Fetch a historical FastF1 session and translate it into APEX's canonical contract.
```
Begins or ends documentation describing the module, class or function contract.

### Line 18
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 19
```python
    FastF1 is an optional dependency because the complete project must remain runnable offline.
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 20
```python
    """
```
Begins or ends documentation describing the module, class or function contract.

### Line 21
```python
    try:
```
Begins an operation that may fail for an expected reason.

### Line 22
```python
        import fastf1
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 23
```python
    except ImportError as exc:
```
Handles a specific failure mode. The handler should preserve useful diagnostic evidence.

### Line 24
```python
        raise RuntimeError(
```
Stops execution because an invariant or supported-condition check failed.

### Line 25
```python
            "FastF1 is not installed. Install the project with the 'real-data' extra."
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 26
```python
        ) from exc
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 27
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 28
```python
    cache_dir = Path(".cache/fastf1")
```
Creates or updates `cache_dir`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 29
```python
    cache_dir.mkdir(parents=True, exist_ok=True)
```
Creates or updates `cache_dir.mkdir(parents`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 30
```python
    fastf1.Cache.enable_cache(str(cache_dir))
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 31
```python
    session = fastf1.get_session(year, event, session_code)
```
Creates or updates `session`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 32
```python
    session.load(telemetry=True, laps=True, weather=True, messages=False)
```
Creates or updates `session.load(telemetry`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 33
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 34
```python
    driver_laps = session.laps.pick_drivers(driver)
```
Creates or updates `driver_laps`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 35
```python
    rows: list[pd.DataFrame] = []
```
Creates or updates `rows: list[pd.DataFrame]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 36
```python
    weather = session.weather_data.copy()
```
Creates or updates `weather`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 37
```python
    if "Time" in weather:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 38
```python
        weather["timestamp_s"] = weather["Time"].dt.total_seconds()
```
Creates or updates `weather["timestamp_s"]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 39
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 40
```python
    for _, lap in driver_laps.iterlaps():
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 41
```python
        telemetry = lap.get_telemetry().copy()
```
Creates or updates `telemetry`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 42
```python
        if telemetry.empty:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 43
```python
            continue
```
Skips the remainder of the current iteration and advances to the next item.

### Line 44
```python
        telemetry["timestamp_s"] = telemetry["SessionTime"].dt.total_seconds()
```
Creates or updates `telemetry["timestamp_s"]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 45
```python
        start, end = telemetry.timestamp_s.min(), telemetry.timestamp_s.max()
```
Creates or updates `start, end`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 46
```python
        regular_time = np.arange(start, end, 1.0 / sample_hz)
```
Creates or updates `regular_time`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 47
```python
        telemetry = telemetry.set_index("timestamp_s").reindex(regular_time).interpolate().ffill().bfill()
```
Creates or updates `telemetry`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 48
```python
        telemetry.index.name = "timestamp_s"
```
Creates or updates `telemetry.index.name`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 49
```python
        telemetry = telemetry.reset_index()
```
Creates or updates `telemetry`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 50
```python
        telemetry["lap_number"] = int(lap.LapNumber)
```
Creates or updates `telemetry["lap_number"]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 51
```python
        telemetry["tyre_age_laps"] = float(lap.TyreLife or 0) + (
```
Creates or updates `telemetry["tyre_age_laps"]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 52
```python
            telemetry["Distance"] / max(float(telemetry["Distance"].max()), 1.0)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 53
```python
        )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 54
```python
        rows.append(telemetry)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 55
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 56
```python
    if not rows:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 57
```python
        raise RuntimeError("FastF1 returned no telemetry for the requested driver/session.")
```
Stops execution because an invariant or supported-condition check failed.

### Line 58
```python
    tele = pd.concat(rows, ignore_index=True).sort_values("timestamp_s")
```
Concatenates tensors or arrays; verify that every non-concatenated axis has identical meaning and size.

### Line 59
```python
    distance = tele["Distance"].fillna(method="ffill").fillna(0.0)
```
Creates or updates `distance`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 60
```python
    progress = (distance / max(float(distance.max()), 1.0)) % 1.0
```
Creates or updates `progress`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 61
```python
    speed_mps = tele["Speed"].astype(float) / 3.6
```
Creates or updates `speed_mps`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 62
```python
    dt = tele.timestamp_s.diff().replace(0, np.nan).fillna(1.0 / sample_hz)
```
Creates or updates `dt`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 63
```python
    acceleration = speed_mps.diff().fillna(0.0) / dt
```
Creates or updates `acceleration`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 64
```python
    x = tele.get("X", pd.Series(np.zeros(len(tele)))).astype(float)
```
Creates or updates `x`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 65
```python
    y = tele.get("Y", pd.Series(np.zeros(len(tele)))).astype(float)
```
Creates or updates `y`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 66
```python
    heading = np.unwrap(np.arctan2(np.gradient(y), np.gradient(x)))
```
Creates or updates `heading`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 67
```python
    steering = np.clip(np.gradient(heading) * sample_hz / 1.8, -1, 1)
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 68
```python
    curvature = np.clip(np.abs(np.gradient(heading)) * 5.0, 0, 1.5)
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 69
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 70
```python
    canonical = pd.DataFrame(
```
Creates or updates `canonical`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 71
```python
        {
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 72
```python
            "session_id": f"FF1_{year}_{event}_{session_code}",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 73
```python
            "source": "fastf1",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 74
```python
            "track_id": str(event),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 75
```python
            "driver_id": str(driver),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 76
```python
            "timestamp_s": tele.timestamp_s,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 77
```python
            "lap_number": tele.lap_number,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 78
```python
            "speed_mps": speed_mps,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 79
```python
            "acceleration_mps2": acceleration,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 80
```python
            "track_progress_sin": np.sin(2 * np.pi * progress),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 81
```python
            "track_progress_cos": np.cos(2 * np.pi * progress),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 82
```python
            "tyre_age_laps": tele.tyre_age_laps,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 83
```python
            "throttle": tele["Throttle"].astype(float) / 100.0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 84
```python
            "brake": tele["Brake"].astype(float),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 85
```python
            "gear_norm": tele["nGear"].astype(float).clip(0, 8) / 8.0,
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 86
```python
            "drs": (tele["DRS"].astype(float) > 9).astype(float),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 87
```python
            "steering_proxy": steering,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 88
```python
            "curvature": curvature,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 89
```python
            "air_temp_c": 25.0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 90
```python
            "track_temp_c": 35.0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 91
```python
            "rainfall": 0.0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 92
```python
            "wind_speed_mps": 2.0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 93
```python
            "grip_level": 1.0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 94
```python
            "lap_distance_m": distance,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 95
```python
            "x_m": x,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 96
```python
            "y_m": y,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 97
```python
            "rpm": tele["RPM"].astype(float),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 98
```python
            "gear": tele["nGear"].astype(int),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 99
```python
            "compound_id": 0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 100
```python
            "is_pit": 0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 101
```python
            "safety_car": 0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 102
```python
        }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 103
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 104
```python
    output = Path(output_path)
```
Creates or updates `output`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 105
```python
    output.parent.mkdir(parents=True, exist_ok=True)
```
Creates or updates `output.parent.mkdir(parents`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 106
```python
    canonical.to_csv(output, index=False)
```
Persists an artifact. The surrounding code should include run identity, schema and preprocessing lineage.

### Line 107
```python
    return canonical
```
Returns the result to the caller; this is the function output boundary that tests should assert.
