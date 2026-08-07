# `projects/09_latent_mpc/main.py`

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
rng=np.random.default_rng(0); horizon=6; mean=np.full(horizon,0.5); std=np.full(horizon,0.3)
```
Creates or updates `rng`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 4
```python
for it in range(5):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 5
```python
    actions=np.clip(rng.normal(mean,std,(500,horizon)),0,1)
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 6
```python
    speed=40+np.cumsum(2*actions-0.4,axis=1)
```
Creates or updates `speed`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 7
```python
    score=-(speed[:,-1]-48)**2-0.1*np.sum(np.diff(actions,axis=1)**2,axis=1)
```
Creates or updates `score`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 8
```python
    elite=actions[np.argsort(score)[-50:]]
```
Creates or updates `elite`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 9
```python
    mean,std=elite.mean(0),elite.std(0)+1e-3
```
Creates or updates `mean,std`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 10
```python
    print(it,mean.round(2),score.max().round(3))
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.
