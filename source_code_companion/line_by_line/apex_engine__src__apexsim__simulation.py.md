# `apex_engine/src/apexsim/simulation.py`

**Role:** Applies bounded counterfactual interventions and runs imagined futures.

Actions and context can be changed only within explicit support; the scenario engine must preserve the model contract and communicate extrapolation.

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

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 5
```python
import numpy as np
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 6
```python
import torch
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 7
```python
from torch import nn
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 8
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 9
```python
from apexsim.contracts import ACTION_COLUMNS, CONTEXT_COLUMNS, MODEL_INPUT_COLUMNS, STATE_COLUMNS
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 10
```python
from apexsim.data.features import Standardizer
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 11
```python
from apexsim.models.rssm import RSSMWorldModel
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 12
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 13
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 14
```python
@dataclass(frozen=True)
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 15
```python
class Scenario:
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 16
```python
    throttle_scale: float = 1.0
```
Creates or updates `throttle_scale: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 17
```python
    brake_scale: float = 1.0
```
Creates or updates `brake_scale: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 18
```python
    grip_multiplier: float = 1.0
```
Creates or updates `grip_multiplier: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 19
```python
    rain_delta: float = 0.0
```
Creates or updates `rain_delta: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 20
```python
    tyre_degradation_multiplier: float = 1.0
```
Creates or updates `tyre_degradation_multiplier: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 21
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 22
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 23
```python
def apply_scenario(future_inputs_raw: np.ndarray, scenario: Scenario) -> np.ndarray:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 24
```python
    modified = future_inputs_raw.copy()
```
Creates or updates `modified`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 25
```python
    index = {name: i for i, name in enumerate(MODEL_INPUT_COLUMNS)}
```
Creates or updates `index`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 26
```python
    modified[:, index["throttle"]] = np.clip(
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 27
```python
        modified[:, index["throttle"]] * scenario.throttle_scale, 0.0, 1.0
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 28
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 29
```python
    modified[:, index["brake"]] = np.clip(
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 30
```python
        modified[:, index["brake"]] * scenario.brake_scale, 0.0, 1.0
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 31
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 32
```python
    modified[:, index["grip_level"]] = np.clip(
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 33
```python
        modified[:, index["grip_level"]] * scenario.grip_multiplier, 0.2, 1.5
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 34
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 35
```python
    modified[:, index["rainfall"]] = np.clip(
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 36
```python
        modified[:, index["rainfall"]] + scenario.rain_delta, 0.0, 1.0
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 37
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 38
```python
    tyre_index = index["tyre_age_laps"]
```
Creates or updates `tyre_index`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 39
```python
    base_age = modified[0, tyre_index]
```
Creates or updates `base_age`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 40
```python
    modified[:, tyre_index] = base_age + (
```
Creates or updates `modified[:, tyre_index]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 41
```python
        modified[:, tyre_index] - base_age
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 42
```python
    ) * scenario.tyre_degradation_multiplier
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 43
```python
    return modified
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 44
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 45
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 46
```python
def rollout(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 47
```python
    model: nn.Module,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 48
```python
    history_raw: np.ndarray,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 49
```python
    future_inputs_raw: np.ndarray,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 50
```python
    standardizer: Standardizer,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 51
```python
    scenario: Scenario,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 52
```python
    device: str = "cpu",
```
Creates or updates `device: str`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 53
```python
) -> np.ndarray:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 54
```python
    model.eval().to(device)
```
Enables deterministic evaluation behaviour for layers that differ between training and inference.

### Line 55
```python
    future_modified = apply_scenario(future_inputs_raw, scenario)
```
Creates or updates `future_modified`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 56
```python
    history = torch.from_numpy(
```
Creates or updates `history`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 57
```python
        standardizer.transform_inputs(history_raw).astype(np.float32)[None, ...]
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 58
```python
    ).to(device)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 59
```python
    future = torch.from_numpy(
```
Creates or updates `future`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 60
```python
        standardizer.transform_inputs(future_modified).astype(np.float32)[None, ...]
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 61
```python
    ).to(device)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 62
```python
    with torch.no_grad():
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 63
```python
        if isinstance(model, RSSMWorldModel):
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 64
```python
            prediction_z, _ = model(history, future, future_targets=None)
```
Creates or updates `prediction_z, _`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 65
```python
        else:
```
Handles all remaining cases; inspect whether this fallback is intentionally broad.

### Line 66
```python
            prediction_z = model(history, future)
```
Creates or updates `prediction_z`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 67
```python
    return standardizer.inverse_targets(prediction_z.cpu().numpy()[0])
```
Returns the result to the caller; this is the function output boundary that tests should assert.
