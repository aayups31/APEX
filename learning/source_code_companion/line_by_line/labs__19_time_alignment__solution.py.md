# `labs/19_time_alignment/solution.py`

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
car=pd.DataFrame({'t':[0.0,0.2,0.4,0.6],'speed':[10,12,14,16]})
```
Creates or updates `car`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 4
```python
weather=pd.DataFrame({'t':[0.05,0.55],'rain':[0.0,0.3]})
```
Creates or updates `weather`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 5
```python
aligned=pd.merge_asof(car.sort_values('t'),weather.sort_values('t'),on='t',direction='backward',tolerance=0.3)
```
Aligns asynchronous time streams by nearby timestamps; direction, tolerance and sort order are part of the scientific contract.

### Line 6
```python
print(aligned)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.
