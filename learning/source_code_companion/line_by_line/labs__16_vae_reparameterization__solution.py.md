# `labs/16_vae_reparameterization/solution.py`

**Role:** Educational executable used to practise one isolated engineering contract.

Run it, inspect intermediate evidence, introduce a failure and add a regression test.

## Line-by-line guide

### Line 1
```python
import torch
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 2
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 3
```python
mu=torch.tensor([[0.2,-0.4]]); logvar=torch.tensor([[-1.0,0.5]])
```
Creates or updates `mu`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 4
```python
std=torch.exp(0.5*logvar); eps=torch.randn_like(std); z=mu+std*eps
```
Creates or updates `std`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 5
```python
kl=-0.5*torch.sum(1+logvar-mu.pow(2)-logvar.exp(),dim=1)
```
Creates or updates `kl`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 6
```python
print("mu",mu,"std",std,"sample",z,"KL",kl)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.
