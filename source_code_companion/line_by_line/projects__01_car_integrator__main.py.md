# `projects/01_car_integrator/main.py`

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
def run():
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 4
```python
    state=CarState(0,0,0)
```
Creates or updates `state`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 5
```python
    trace=[]
```
Creates or updates `trace`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 6
```python
    for i in range(100):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 7
```python
        state=step_car(state,0.8 if i<60 else 0.0,0.0 if i<60 else 0.5,0.1)
```
Creates or updates `state`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 8
```python
        trace.append(state)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 9
```python
    assert trace[-1].speed_mps >= 0
```
Checks an invariant immediately so invalid evidence cannot propagate farther.

### Line 10
```python
    print(trace[-1])
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 11
```python
if __name__=='__main__': run()
```
Branches only when this condition is true; verify both the true and false paths in tests.
