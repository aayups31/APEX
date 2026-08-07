# `apex_engine/src/apexsim/contracts.py`

**Role:** Defines the canonical telemetry language used by every data source and model.

Treat field order, unit and availability time as part of the API. A model checkpoint is compatible only with the exact contract and preprocessing version it was trained against.

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
from dataclasses import dataclass
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 4
```python
from typing import Final
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 5
```python

```
Separates logical blocks so the surrounding control flow remains readable.

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
# Canonical columns are deliberately independent of FastF1, OpenF1, and F1 25.
```
Documents an assumption, intent or constraint that should remain aligned with the implementation.

### Line 9
```python
# Every source adapter must translate into this stable contract.
```
Documents an assumption, intent or constraint that should remain aligned with the implementation.

### Line 10
```python
IDENTITY_COLUMNS: Final[list[str]] = [
```
Creates or updates `IDENTITY_COLUMNS: Final[list[str]]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 11
```python
    "session_id",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 12
```python
    "source",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 13
```python
    "track_id",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 14
```python
    "driver_id",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 15
```python
    "timestamp_s",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 16
```python
    "lap_number",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 17
```python
]
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 18
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 19
```python
STATE_COLUMNS: Final[list[str]] = [
```
Creates or updates `STATE_COLUMNS: Final[list[str]]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 20
```python
    "speed_mps",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 21
```python
    "acceleration_mps2",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 22
```python
    "track_progress_sin",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 23
```python
    "track_progress_cos",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 24
```python
    "tyre_age_laps",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 25
```python
]
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 26
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 27
```python
ACTION_COLUMNS: Final[list[str]] = [
```
Creates or updates `ACTION_COLUMNS: Final[list[str]]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 28
```python
    "throttle",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 29
```python
    "brake",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 30
```python
    "gear_norm",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 31
```python
    "drs",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 32
```python
    "steering_proxy",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 33
```python
]
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 34
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 35
```python
CONTEXT_COLUMNS: Final[list[str]] = [
```
Creates or updates `CONTEXT_COLUMNS: Final[list[str]]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 36
```python
    "curvature",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 37
```python
    "air_temp_c",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 38
```python
    "track_temp_c",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 39
```python
    "rainfall",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 40
```python
    "wind_speed_mps",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 41
```python
    "grip_level",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 42
```python
]
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 43
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 44
```python
AUX_COLUMNS: Final[list[str]] = [
```
Creates or updates `AUX_COLUMNS: Final[list[str]]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 45
```python
    "lap_distance_m",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 46
```python
    "x_m",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 47
```python
    "y_m",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 48
```python
    "rpm",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 49
```python
    "gear",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 50
```python
    "compound_id",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 51
```python
    "is_pit",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 52
```python
    "safety_car",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 53
```python
]
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 54
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 55
```python
REQUIRED_COLUMNS: Final[list[str]] = (
```
Creates or updates `REQUIRED_COLUMNS: Final[list[str]]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 56
```python
    IDENTITY_COLUMNS + STATE_COLUMNS + ACTION_COLUMNS + CONTEXT_COLUMNS + AUX_COLUMNS
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 57
```python
)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 58
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 59
```python
MODEL_INPUT_COLUMNS: Final[list[str]] = STATE_COLUMNS + ACTION_COLUMNS + CONTEXT_COLUMNS
```
Creates or updates `MODEL_INPUT_COLUMNS: Final[list[str]]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 60
```python
TARGET_COLUMNS: Final[list[str]] = STATE_COLUMNS
```
Creates or updates `TARGET_COLUMNS: Final[list[str]]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 61
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 62
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 63
```python
@dataclass(frozen=True)
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 64
```python
class ContractReport:
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 65
```python
    rows: int
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 66
```python
    sessions: int
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 67
```python
    drivers: int
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 68
```python
    tracks: int
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 69
```python
    null_cells: int
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 70
```python
    duplicate_frames: int
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 71
```python
    out_of_range_cells: int
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 72
```python
    passed: bool
```
Provides an intentionally empty block; verify that this is a deliberate extension point.

### Line 73
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 74
```python
    def to_dict(self) -> dict[str, int | bool]:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 75
```python
        return self.__dict__.copy()
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 76
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 77
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 78
```python
def assert_canonical_frame(frame: pd.DataFrame) -> None:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 79
```python
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
```
Creates or updates `missing`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 80
```python
    if missing:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 81
```python
        raise ValueError(f"Canonical frame is missing columns: {missing}")
```
Stops execution because an invariant or supported-condition check failed.
