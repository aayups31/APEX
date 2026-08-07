# `labs/01_units_and_shapes/solution.py`

**Role:** Educational executable used to practise one isolated engineering contract.

Run it, inspect intermediate evidence, introduce a failure and add a regression test.

## Line-by-line guide

### Line 1
```python
import numpy as np
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 2
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 3
```python
speed_kmh = np.array([0.0, 72.0, 144.0])
```
Creates or updates `speed_kmh`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 4
```python
speed_mps = speed_kmh / 3.6
```
Creates or updates `speed_mps`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 5
```python
telemetry = np.stack([speed_mps, np.array([0.0, 0.5, 1.0])], axis=1)
```
Creates a new axis by stacking aligned values; document what the new axis represents.

### Line 6
```python
print("speed_mps:", speed_mps)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 7
```python
print("telemetry shape [time, features]:", telemetry.shape)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 8
```python
assert telemetry.shape == (3, 2)
```
Checks an invariant immediately so invalid evidence cannot propagate farther.
