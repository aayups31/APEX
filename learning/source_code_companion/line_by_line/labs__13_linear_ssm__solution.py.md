# `labs/13_linear_ssm/solution.py`

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
A=np.array([[0.95,0.0],[0.1,0.85]]); B=np.array([[0.2],[0.05]]); x=np.zeros(2)
```
Creates or updates `A`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 3
```python
for u in [1,1,0,0,0]:
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 4
```python
    x=A@x+B[:,0]*u; print(x.round(3))
```
Creates or updates `x`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.
