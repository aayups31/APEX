# `apex_engine/src/apexsim/plotting.py`

**Role:** Turns telemetry and rollout evidence into diagnostic figures.

Plots should expose alignment, horizon drift and intervention effects rather than merely decorate the UI.

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
import matplotlib.pyplot as plt
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
def save_track_map(frame: pd.DataFrame, output_path: str | Path) -> Path:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 10
```python
    path = Path(output_path)
```
Creates or updates `path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 11
```python
    path.parent.mkdir(parents=True, exist_ok=True)
```
Creates or updates `path.parent.mkdir(parents`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 12
```python
    fig, ax = plt.subplots(figsize=(6, 4.5))
```
Creates or updates `fig, ax`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 13
```python
    session = frame[frame.session_id == frame.session_id.iloc[0]]
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 14
```python
    ax.plot(session.x_m, session.y_m, linewidth=2)
```
Creates or updates `ax.plot(session.x_m, session.y_m, linewidth`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 15
```python
    ax.scatter(session.x_m.iloc[0], session.y_m.iloc[0], s=50, label="Start")
```
Creates or updates `ax.scatter(session.x_m.iloc[0], session.y_m.iloc[0], s`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 16
```python
    ax.set_title("Synthetic track geometry")
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 17
```python
    ax.set_xlabel("x (m)")
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 18
```python
    ax.set_ylabel("y (m)")
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 19
```python
    ax.set_aspect("equal", adjustable="box")
```
Creates or updates `ax.set_aspect("equal", adjustable`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 20
```python
    ax.legend()
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 21
```python
    fig.tight_layout()
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 22
```python
    fig.savefig(path, dpi=160)
```
Creates or updates `fig.savefig(path, dpi`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 23
```python
    plt.close(fig)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 24
```python
    return path
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 25
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 26
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 27
```python
def save_training_curve(history: list[dict], output_path: str | Path) -> Path:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 28
```python
    path = Path(output_path)
```
Creates or updates `path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 29
```python
    path.parent.mkdir(parents=True, exist_ok=True)
```
Creates or updates `path.parent.mkdir(parents`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 30
```python
    frame = pd.DataFrame(history)
```
Creates or updates `frame`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 31
```python
    fig, ax = plt.subplots(figsize=(6, 4))
```
Creates or updates `fig, ax`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 32
```python
    ax.plot(frame.epoch, frame.train_loss, marker="o", label="Train")
```
Creates or updates `ax.plot(frame.epoch, frame.train_loss, marker`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 33
```python
    ax.plot(frame.epoch, frame.val_loss, marker="o", label="Validation")
```
Creates or updates `ax.plot(frame.epoch, frame.val_loss, marker`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 34
```python
    ax.set_xlabel("Epoch")
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 35
```python
    ax.set_ylabel("Loss")
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 36
```python
    ax.set_title("World-model training")
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 37
```python
    ax.legend()
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 38
```python
    fig.tight_layout()
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 39
```python
    fig.savefig(path, dpi=160)
```
Creates or updates `fig.savefig(path, dpi`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 40
```python
    plt.close(fig)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 41
```python
    return path
```
Returns the result to the caller; this is the function output boundary that tests should assert.
