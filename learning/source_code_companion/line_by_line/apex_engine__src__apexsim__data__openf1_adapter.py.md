# `apex_engine/src/apexsim/data/openf1_adapter.py`

**Role:** Retrieves and aligns OpenF1 endpoint streams.

Every as-of join needs a direction, tolerance and freshness interpretation; nearest data is not automatically simultaneous data.

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
import requests
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 8
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 9
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 10
```python
BASE_URL = "https://api.openf1.org/v1"
```
Creates or updates `BASE_URL`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 11
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 12
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 13
```python
def _get(endpoint: str, params: dict[str, int | str], timeout: int = 60) -> list[dict]:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 14
```python
    response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=timeout)
```
Creates or updates `response`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 15
```python
    response.raise_for_status()
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 16
```python
    payload = response.json()
```
Creates or updates `payload`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 17
```python
    if not isinstance(payload, list):
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 18
```python
        raise ValueError(f"Expected a list from OpenF1 {endpoint}, got {type(payload).__name__}")
```
Stops execution because an invariant or supported-condition check failed.

### Line 19
```python
    return payload
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 20
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 21
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 22
```python
def ingest_openf1_session(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 23
```python
    session_key: int,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 24
```python
    driver_number: int,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 25
```python
    output_path: str | Path,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 26
```python
    sample_hz: int = 4,
```
Creates or updates `sample_hz: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 27
```python
) -> pd.DataFrame:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 28
```python
    """Translate OpenF1 car/location/weather streams into the canonical frame.
```
Begins or ends documentation describing the module, class or function contract.

### Line 29
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 30
```python
    Historical OpenF1 data is rich but the endpoints are sampled independently. We therefore align
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 31
```python
    streams on time instead of assuming row N in one endpoint matches row N in another.
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 32
```python
    """
```
Begins or ends documentation describing the module, class or function contract.

### Line 33
```python
    car = pd.DataFrame(_get("car_data", {"session_key": session_key, "driver_number": driver_number}))
```
Creates or updates `car`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 34
```python
    location = pd.DataFrame(_get("location", {"session_key": session_key, "driver_number": driver_number}))
```
Creates or updates `location`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 35
```python
    laps = pd.DataFrame(_get("laps", {"session_key": session_key, "driver_number": driver_number}))
```
Creates or updates `laps`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 36
```python
    weather = pd.DataFrame(_get("weather", {"session_key": session_key}))
```
Creates or updates `weather`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 37
```python
    if car.empty or location.empty:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 38
```python
        raise RuntimeError("OpenF1 returned no car or location data for the request.")
```
Stops execution because an invariant or supported-condition check failed.

### Line 39
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 40
```python
    for frame in (car, location, weather):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 41
```python
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
```
Creates or updates `frame["date"]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 42
```python
    car = car.sort_values("date")
```
Creates or updates `car`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 43
```python
    location = location.sort_values("date")
```
Creates or updates `location`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 44
```python
    weather = weather.sort_values("date")
```
Creates or updates `weather`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 45
```python
    merged = pd.merge_asof(car, location, on="date", direction="nearest", tolerance=pd.Timedelta("1s"))
```
Aligns asynchronous time streams by nearby timestamps; direction, tolerance and sort order are part of the scientific contract.

### Line 46
```python
    merged = pd.merge_asof(merged, weather, on="date", direction="nearest", tolerance=pd.Timedelta("20s"), suffixes=("", "_weather"))
```
Aligns asynchronous time streams by nearby timestamps; direction, tolerance and sort order are part of the scientific contract.

### Line 47
```python
    merged = merged.dropna(subset=["speed", "x", "y"])
```
Creates or updates `merged`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 48
```python
    start = merged.date.min()
```
Creates or updates `start`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 49
```python
    merged["timestamp_s"] = (merged.date - start).dt.total_seconds()
```
Creates or updates `merged["timestamp_s"]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 50
```python
    regular_time = np.arange(0, merged.timestamp_s.max(), 1.0 / sample_hz)
```
Creates or updates `regular_time`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 51
```python
    numeric = merged.select_dtypes(include=[np.number]).copy()
```
Creates or updates `numeric`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 52
```python
    numeric.index = merged.timestamp_s
```
Creates or updates `numeric.index`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 53
```python
    numeric = numeric[~numeric.index.duplicated()].reindex(regular_time).interpolate().ffill().bfill()
```
Creates or updates `numeric`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 54
```python
    numeric.index.name = "timestamp_s"
```
Creates or updates `numeric.index.name`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 55
```python
    numeric = numeric.reset_index()
```
Creates or updates `numeric`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 56
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 57
```python
    speed_mps = numeric["speed"] / 3.6
```
Creates or updates `speed_mps`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 58
```python
    dt = numeric.timestamp_s.diff().replace(0, np.nan).fillna(1.0 / sample_hz)
```
Creates or updates `dt`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 59
```python
    accel = speed_mps.diff().fillna(0.0) / dt
```
Creates or updates `accel`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 60
```python
    x, y = numeric["x"], numeric["y"]
```
Creates or updates `x, y`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 61
```python
    heading = np.unwrap(np.arctan2(np.gradient(y), np.gradient(x)))
```
Creates or updates `heading`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 62
```python
    curvature = np.clip(np.abs(np.gradient(heading)) * 5.0, 0, 1.5)
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 63
```python
    distance = np.cumsum(speed_mps.to_numpy() / sample_hz)
```
Creates or updates `distance`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 64
```python
    track_length = max(float(np.quantile(distance, 0.99)), 1.0)
```
Creates or updates `track_length`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 65
```python
    progress = (distance / track_length) % 1.0
```
Creates or updates `progress`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 66
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 67
```python
    canonical = pd.DataFrame(
```
Creates or updates `canonical`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 68
```python
        {
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 69
```python
            "session_id": f"OF1_{session_key}",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 70
```python
            "source": "openf1",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 71
```python
            "track_id": f"session_{session_key}",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 72
```python
            "driver_id": str(driver_number),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 73
```python
            "timestamp_s": numeric.timestamp_s,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 74
```python
            "lap_number": (distance // track_length + 1).astype(int),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 75
```python
            "speed_mps": speed_mps,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 76
```python
            "acceleration_mps2": accel,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 77
```python
            "track_progress_sin": np.sin(2 * np.pi * progress),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 78
```python
            "track_progress_cos": np.cos(2 * np.pi * progress),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 79
```python
            "tyre_age_laps": distance / track_length,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 80
```python
            "throttle": numeric.get("throttle", pd.Series(np.zeros(len(numeric)))) / 100.0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 81
```python
            "brake": numeric.get("brake", pd.Series(np.zeros(len(numeric)))).clip(0, 1),
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 82
```python
            "gear_norm": numeric.get("n_gear", pd.Series(np.ones(len(numeric)))) / 8.0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 83
```python
            "drs": numeric.get("drs", pd.Series(np.zeros(len(numeric)))).clip(0, 1),
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 84
```python
            "steering_proxy": np.clip(np.gradient(heading) * sample_hz / 1.8, -1, 1),
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 85
```python
            "curvature": curvature,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 86
```python
            "air_temp_c": numeric.get("air_temperature", pd.Series(np.full(len(numeric), 25.0))),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 87
```python
            "track_temp_c": numeric.get("track_temperature", pd.Series(np.full(len(numeric), 35.0))),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 88
```python
            "rainfall": numeric.get("rainfall", pd.Series(np.zeros(len(numeric)))).clip(0, 1),
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 89
```python
            "wind_speed_mps": numeric.get("wind_speed", pd.Series(np.full(len(numeric), 2.0))),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 90
```python
            "grip_level": 1.0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 91
```python
            "lap_distance_m": distance % track_length,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 92
```python
            "x_m": x,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 93
```python
            "y_m": y,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 94
```python
            "rpm": numeric.get("rpm", pd.Series(np.full(len(numeric), 9000.0))),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 95
```python
            "gear": numeric.get("n_gear", pd.Series(np.ones(len(numeric)))).astype(int),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 96
```python
            "compound_id": 0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 97
```python
            "is_pit": 0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 98
```python
            "safety_car": 0,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 99
```python
        }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 100
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 101
```python
    output = Path(output_path)
```
Creates or updates `output`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 102
```python
    output.parent.mkdir(parents=True, exist_ok=True)
```
Creates or updates `output.parent.mkdir(parents`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 103
```python
    canonical.to_csv(output, index=False)
```
Persists an artifact. The surrounding code should include run identity, schema and preprocessing lineage.

### Line 104
```python
    return canonical
```
Returns the result to the caller; this is the function output boundary that tests should assert.
