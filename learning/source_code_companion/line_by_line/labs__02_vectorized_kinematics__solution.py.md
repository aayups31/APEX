# `labs/02_vectorized_kinematics/solution.py`

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
dt = 0.2
```
Creates or updates `dt`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 4
```python
time = np.arange(0, 5, dt)
```
Creates or updates `time`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 5
```python
speed = 20 + 4*np.sin(time)
```
Creates or updates `speed`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 6
```python
accel = np.gradient(speed, dt)
```
Creates or updates `accel`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 7
```python
reconstructed = speed[0] + np.cumsum(accel)*dt
```
Creates or updates `reconstructed`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 8
```python
print("first accelerations:", accel[:5].round(3))
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 9
```python
print("max reconstruction error:", float(np.max(np.abs(reconstructed-speed))))
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.
