# `labs/04_sampling_aliasing/solution.py`

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
for hz in [5, 12, 40]:
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 4
```python
    t=np.arange(0,2,1/hz)
```
Creates or updates `t`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 5
```python
    signal=np.sin(2*np.pi*8*t)
```
Creates or updates `signal`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 6
```python
    print(hz, "Hz samples:", np.round(signal[:8],3))
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.
