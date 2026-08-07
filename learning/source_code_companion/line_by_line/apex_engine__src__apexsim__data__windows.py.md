# `apex_engine/src/apexsim/data/windows.py`

**Role:** Builds group-safe sequence windows and normalization artifacts.

An off-by-one or cross-session window can make a model appear excellent while invalidating the experiment.

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
import torch
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 8
```python
from torch.utils.data import Dataset
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 9
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 10
```python
from apexsim.contracts import MODEL_INPUT_COLUMNS, STATE_COLUMNS, TARGET_COLUMNS
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 11
```python
from apexsim.data.features import Standardizer
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
class WindowIndex:
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 16
```python
    session_id: str
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 17
```python
    start: int
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 18
```python
    stop: int
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 19
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 20
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 21
```python
def split_sessions(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 22
```python
    frame: pd.DataFrame,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 23
```python
    train_fraction: float,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 24
```python
    val_fraction: float,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 25
```python
    seed: int,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 26
```python
) -> dict[str, list[str]]:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 27
```python
    sessions = sorted(frame.session_id.unique().tolist())
```
Creates or updates `sessions`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 28
```python
    rng = np.random.default_rng(seed)
```
Creates or updates `rng`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 29
```python
    rng.shuffle(sessions)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 30
```python
    n = len(sessions)
```
Creates or updates `n`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 31
```python
    n_train = max(1, int(round(n * train_fraction)))
```
Creates or updates `n_train`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 32
```python
    n_val = max(1, int(round(n * val_fraction)))
```
Creates or updates `n_val`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 33
```python
    if n_train + n_val >= n:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 34
```python
        n_val = 1
```
Creates or updates `n_val`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 35
```python
        n_train = max(1, n - 2)
```
Creates or updates `n_train`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 36
```python
    return {
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 37
```python
        "train": sessions[:n_train],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 38
```python
        "val": sessions[n_train : n_train + n_val],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 39
```python
        "test": sessions[n_train + n_val :],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 40
```python
    }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

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
class TelemetryWindowDataset(Dataset):
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 44
```python
    """Returns histories and next-state sequences without crossing session boundaries."""
```
Begins or ends documentation describing the module, class or function contract.

### Line 45
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 46
```python
    def __init__(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 47
```python
        self,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 48
```python
        frame: pd.DataFrame,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 49
```python
        session_ids: list[str],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 50
```python
        sequence_length: int,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 51
```python
        prediction_horizon: int,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 52
```python
        standardizer: Standardizer,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 53
```python
        max_windows: int | None = None,
```
Creates or updates `max_windows: int | None`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 54
```python
    ) -> None:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 55
```python
        self.sequence_length = sequence_length
```
Creates or updates `self.sequence_length`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 56
```python
        self.prediction_horizon = prediction_horizon
```
Runs model inference using learned parameters without fitting on the requested examples.

### Line 57
```python
        self.standardizer = standardizer
```
Creates or updates `self.standardizer`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 58
```python
        self.sessions: dict[str, pd.DataFrame] = {}
```
Creates or updates `self.sessions: dict[str, pd.DataFrame]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 59
```python
        self.indices: list[WindowIndex] = []
```
Creates or updates `self.indices: list[WindowIndex]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 60
```python
        total = sequence_length + prediction_horizon
```
Creates or updates `total`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 61
```python
        for session_id in session_ids:
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 62
```python
            session = (
```
Creates or updates `session`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 63
```python
                frame[frame.session_id == session_id]
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 64
```python
                .sort_values("timestamp_s")
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 65
```python
                .reset_index(drop=True)
```
Creates or updates `.reset_index(drop`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 66
```python
            )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 67
```python
            self.sessions[session_id] = session
```
Creates or updates `self.sessions[session_id]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 68
```python
            for start in range(0, len(session) - total + 1):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 69
```python
                self.indices.append(WindowIndex(session_id, start, start + total))
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 70
```python
        if max_windows is not None and len(self.indices) > max_windows:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 71
```python
            positions = np.linspace(0, len(self.indices) - 1, max_windows).astype(int)
```
Creates or updates `positions`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 72
```python
            self.indices = [self.indices[i] for i in positions]
```
Creates or updates `self.indices`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 73
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 74
```python
    def __len__(self) -> int:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 75
```python
        return len(self.indices)
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 76
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 77
```python
    def __getitem__(self, index: int) -> dict[str, torch.Tensor | str]:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 78
```python
        item = self.indices[index]
```
Creates or updates `item`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 79
```python
        window = self.sessions[item.session_id].iloc[item.start : item.stop]
```
Creates or updates `window`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 80
```python
        history = window.iloc[: self.sequence_length]
```
Creates or updates `history`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 81
```python
        future = window.iloc[self.sequence_length :]
```
Creates or updates `future`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 82
```python
        x_history = history[MODEL_INPUT_COLUMNS].to_numpy(np.float32)
```
Creates or updates `x_history`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 83
```python
        x_future = future[MODEL_INPUT_COLUMNS].to_numpy(np.float32)
```
Creates or updates `x_future`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 84
```python
        y_future = future[TARGET_COLUMNS].to_numpy(np.float32)
```
Creates or updates `y_future`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 85
```python
        state_history = history[STATE_COLUMNS].to_numpy(np.float32)
```
Creates or updates `state_history`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 86
```python
        return {
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 87
```python
            "history": torch.from_numpy(self.standardizer.transform_inputs(x_history).astype(np.float32)),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 88
```python
            "future_inputs": torch.from_numpy(self.standardizer.transform_inputs(x_future).astype(np.float32)),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 89
```python
            "future_targets": torch.from_numpy(self.standardizer.transform_targets(y_future).astype(np.float32)),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 90
```python
            "state_history": torch.from_numpy(self.standardizer.transform_targets(state_history).astype(np.float32)),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 91
```python
            "session_id": item.session_id,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 92
```python
        }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.
