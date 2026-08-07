# `apex_engine/src/apexsim/data/features.py`

**Role:** Creates causal derived signals and feature arrays.

Every feature must be available at prediction time and have one stable unit/order definition.

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
import pandas as pd
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 7
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 8
```python
from apexsim.contracts import MODEL_INPUT_COLUMNS, TARGET_COLUMNS
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 9
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 10
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 11
```python
@dataclass
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 12
```python
class Standardizer:
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 13
```python
    input_mean: np.ndarray
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 14
```python
    input_std: np.ndarray
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 15
```python
    target_mean: np.ndarray
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 16
```python
    target_std: np.ndarray
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 17
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 18
```python
    @classmethod
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 19
```python
    def fit(cls, frame: pd.DataFrame) -> "Standardizer":
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 20
```python
        x = frame[MODEL_INPUT_COLUMNS].to_numpy(np.float32)
```
Creates or updates `x`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 21
```python
        y = frame[TARGET_COLUMNS].to_numpy(np.float32)
```
Creates or updates `y`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 22
```python
        x_std = x.std(axis=0)
```
Creates or updates `x_std`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 23
```python
        y_std = y.std(axis=0)
```
Creates or updates `y_std`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 24
```python
        return cls(
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 25
```python
            input_mean=x.mean(axis=0),
```
Creates or updates `input_mean`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 26
```python
            input_std=np.where(x_std < 1e-6, 1.0, x_std),
```
Creates or updates `input_std`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 27
```python
            target_mean=y.mean(axis=0),
```
Creates or updates `target_mean`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 28
```python
            target_std=np.where(y_std < 1e-6, 1.0, y_std),
```
Creates or updates `target_std`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 29
```python
        )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 30
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 31
```python
    def transform_inputs(self, values: np.ndarray) -> np.ndarray:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 32
```python
        return (values - self.input_mean) / self.input_std
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 33
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 34
```python
    def transform_targets(self, values: np.ndarray) -> np.ndarray:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 35
```python
        return (values - self.target_mean) / self.target_std
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 36
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 37
```python
    def inverse_targets(self, values: np.ndarray) -> np.ndarray:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 38
```python
        return values * self.target_std + self.target_mean
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 39
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 40
```python
    def to_dict(self) -> dict[str, list[float]]:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 41
```python
        return {
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 42
```python
            "input_mean": self.input_mean.tolist(),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 43
```python
            "input_std": self.input_std.tolist(),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 44
```python
            "target_mean": self.target_mean.tolist(),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 45
```python
            "target_std": self.target_std.tolist(),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 46
```python
        }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 47
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 48
```python
    @classmethod
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 49
```python
    def from_dict(cls, payload: dict[str, list[float]]) -> "Standardizer":
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 50
```python
        return cls(**{key: np.asarray(value, dtype=np.float32) for key, value in payload.items()})
```
Returns the result to the caller; this is the function output boundary that tests should assert.
