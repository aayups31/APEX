# `projects/02_telemetry_quality/main.py`

**Role:** Educational executable used to practise one isolated engineering contract.

Run it, inspect intermediate evidence, introduce a failure and add a regression test.

## Line-by-line guide

### Line 1
```python
import pandas as pd
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 2
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 3
```python
REQUIRED={'time_s','speed_mps','throttle','brake'}
```
Creates or updates `REQUIRED`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 4
```python
def validate(df):
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 5
```python
    errors=[]
```
Creates or updates `errors`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 6
```python
    if not REQUIRED.issubset(df): errors.append('missing columns')
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 7
```python
    if not df.time_s.is_monotonic_increasing: errors.append('time not monotonic')
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 8
```python
    if (df.speed_mps<0).any(): errors.append('negative speed')
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 9
```python
    if not df.throttle.between(0,1).all(): errors.append('throttle range')
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 10
```python
    return errors
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 11
```python
def run():
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 12
```python
    df=pd.DataFrame({'time_s':[0,0.1,0.2],'speed_mps':[0,3,4],'throttle':[0,1,0.5],'brake':[0,0,0]})
```
Creates or updates `df`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 13
```python
    assert validate(df)==[]; print('quality passed')
```
Checks an invariant immediately so invalid evidence cannot propagate farther.

### Line 14
```python
if __name__=='__main__': run()
```
Branches only when this condition is true; verify both the true and false paths in tests.
