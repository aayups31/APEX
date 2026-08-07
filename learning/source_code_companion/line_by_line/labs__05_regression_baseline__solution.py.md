# `labs/05_regression_baseline/solution.py`

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
from sklearn.linear_model import Ridge
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 3
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 4
```python
rng=np.random.default_rng(4)
```
Creates or updates `rng`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 5
```python
speed=rng.uniform(20,80,1000)
```
Creates or updates `speed`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 6
```python
throttle=rng.uniform(0,1,1000)
```
Creates or updates `throttle`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 7
```python
brake=rng.uniform(0,1,1000)
```
Creates or updates `brake`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 8
```python
y=speed + 0.7*throttle - 1.1*brake - 0.0008*speed**2 + rng.normal(0,0.05,1000)
```
Creates or updates `y`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 9
```python
X=np.column_stack([speed,throttle,brake])
```
Creates a new axis by stacking aligned values; document what the new axis represents.

### Line 10
```python
model=Ridge(alpha=1.0).fit(X[:800],y[:800])
```
Learns parameters or preprocessing statistics from the supplied training evidence only.

### Line 11
```python
print("coefficients:", model.coef_)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 12
```python
print("test MAE:", np.mean(np.abs(model.predict(X[800:])-y[800:])))
```
Runs model inference using learned parameters without fitting on the requested examples.
