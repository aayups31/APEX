# `apex_engine/src/apexsim/data/validate.py`

**Role:** Implements schema, range, time and consistency quality gates.

The earliest cheap check should catch a defect before it reaches windows, normalization or training.

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
import numpy as np
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 4
```python
import pandas as pd
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 5
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 6
```python
from apexsim.contracts import ContractReport, REQUIRED_COLUMNS, assert_canonical_frame
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
def validate_canonical_frame(frame: pd.DataFrame, strict: bool = True) -> ContractReport:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 10
```python
    assert_canonical_frame(frame)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 11
```python
    null_cells = int(frame[REQUIRED_COLUMNS].isna().sum().sum())
```
Creates or updates `null_cells`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 12
```python
    duplicate_frames = int(
```
Creates or updates `duplicate_frames`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 13
```python
        frame.duplicated(subset=["session_id", "driver_id", "timestamp_s"]).sum()
```
Creates or updates `frame.duplicated(subset`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 14
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 15
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 16
```python
    violations = np.zeros(len(frame), dtype=bool)
```
Creates or updates `violations`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 17
```python
    range_checks = {
```
Creates or updates `range_checks`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 18
```python
        "speed_mps": (0.0, 120.0),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 19
```python
        "throttle": (0.0, 1.0),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 20
```python
        "brake": (0.0, 1.0),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 21
```python
        "gear_norm": (0.0, 1.0),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 22
```python
        "drs": (0.0, 1.0),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 23
```python
        "steering_proxy": (-1.0, 1.0),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 24
```python
        "rainfall": (0.0, 1.0),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 25
```python
        "grip_level": (0.2, 1.5),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 26
```python
    }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 27
```python
    for column, (minimum, maximum) in range_checks.items():
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 28
```python
        values = pd.to_numeric(frame[column], errors="coerce")
```
Creates or updates `values`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 29
```python
        violations |= values.lt(minimum).to_numpy() | values.gt(maximum).to_numpy()
```
Creates or updates `violations |`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 30
```python
    out_of_range_cells = int(violations.sum())
```
Creates or updates `out_of_range_cells`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 31
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 32
```python
    passed = null_cells == 0 and duplicate_frames == 0 and out_of_range_cells == 0
```
Provides an intentionally empty block; verify that this is a deliberate extension point.

### Line 33
```python
    report = ContractReport(
```
Creates or updates `report`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 34
```python
        rows=len(frame),
```
Creates or updates `rows`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 35
```python
        sessions=int(frame.session_id.nunique()),
```
Creates or updates `sessions`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 36
```python
        drivers=int(frame.driver_id.nunique()),
```
Creates or updates `drivers`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 37
```python
        tracks=int(frame.track_id.nunique()),
```
Creates or updates `tracks`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 38
```python
        null_cells=null_cells,
```
Creates or updates `null_cells`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 39
```python
        duplicate_frames=duplicate_frames,
```
Creates or updates `duplicate_frames`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 40
```python
        out_of_range_cells=out_of_range_cells,
```
Creates or updates `out_of_range_cells`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 41
```python
        passed=passed,
```
Provides an intentionally empty block; verify that this is a deliberate extension point.

### Line 42
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 43
```python
    if strict and not passed:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 44
```python
        raise ValueError(f"Canonical data contract failed: {report.to_dict()}")
```
Stops execution because an invariant or supported-condition check failed.

### Line 45
```python
    return report
```
Returns the result to the caller; this is the function output boundary that tests should assert.
