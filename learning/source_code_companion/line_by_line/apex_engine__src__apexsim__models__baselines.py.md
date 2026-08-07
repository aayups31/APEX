# `apex_engine/src/apexsim/models/baselines.py`

**Role:** Provides simple controls that expose leakage and unnecessary complexity.

A world model should not be promoted until it beats persistence and linear dynamics on the exact deployment protocol.

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
from sklearn.linear_model import Ridge
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 5
```python
from sklearn.multioutput import MultiOutputRegressor
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 6
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 7
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 8
```python
class PersistenceBaseline:
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 9
```python
    """Predict that the next state is identical to the current state."""
```
Begins or ends documentation describing the module, class or function contract.

### Line 10
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 11
```python
    def predict(self, current_state: np.ndarray, horizon: int) -> np.ndarray:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 12
```python
        return np.repeat(current_state[None, :], horizon, axis=0)
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 13
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 14
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 15
```python
class LinearTransitionBaseline:
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 16
```python
    """Ridge regression for one-step state transitions."""
```
Begins or ends documentation describing the module, class or function contract.

### Line 17
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 18
```python
    def __init__(self, alpha: float = 1.0) -> None:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 19
```python
        self.model = MultiOutputRegressor(Ridge(alpha=alpha))
```
Creates or updates `self.model`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 20
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 21
```python
    def fit(self, inputs: np.ndarray, next_states: np.ndarray) -> "LinearTransitionBaseline":
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 22
```python
        self.model.fit(inputs, next_states)
```
Learns parameters or preprocessing statistics from the supplied training evidence only.

### Line 23
```python
        return self
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 24
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 25
```python
    def predict(self, inputs: np.ndarray) -> np.ndarray:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 26
```python
        return self.model.predict(inputs)
```
Returns the result to the caller; this is the function output boundary that tests should assert.
