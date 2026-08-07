# `labs/03_force_model/solution.py`

**Role:** Educational executable used to practise one isolated engineering contract.

Run it, inspect intermediate evidence, introduce a failure and add a regression test.

## Line-by-line guide

### Line 1
```python
from education.core import CarState, step_car
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 2
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 3
```python
state = CarState(0.0, 0.0, 40.0)
```
Creates or updates `state`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 4
```python
for i in range(5):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 5
```python
    state = step_car(state, throttle=0.7, brake=0.0, dt=0.1)
```
Creates or updates `state`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 6
```python
    print(i, state)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.
