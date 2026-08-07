# `projects/03_lap_physics/main.py`

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
def run(n=600):
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 4
```python
    progress=np.linspace(0,1,n,endpoint=False); curvature=0.02+0.12*(np.sin(6*np.pi*progress)**2)
```
Creates or updates `progress`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 5
```python
    target=np.clip(90/(1+10*curvature),20,90); speed=np.empty(n); speed[0]=30
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 6
```python
    for i in range(1,n): speed[i]=speed[i-1]+0.08*np.clip(target[i]-speed[i-1],-8,3)
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 7
```python
    print('speed range',float(speed.min()),float(speed.max()))
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 8
```python
    return progress,curvature,speed
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 9
```python
if __name__=='__main__': run()
```
Branches only when this condition is true; verify both the true and false paths in tests.
