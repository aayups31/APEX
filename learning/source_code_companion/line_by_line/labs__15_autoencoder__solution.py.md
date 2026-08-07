# `labs/15_autoencoder/solution.py`

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
from torch import nn
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 3
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 4
```python
torch.manual_seed(3); x=torch.randn(256,12)
```
Fixes a random seed to make the experiment easier to reproduce and compare.

### Line 5
```python
enc=nn.Linear(12,3); dec=nn.Linear(3,12); opt=torch.optim.Adam(list(enc.parameters())+list(dec.parameters()),lr=0.03)
```
Creates or updates `enc`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 6
```python
for _ in range(80):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 7
```python
    opt.zero_grad(); z=torch.tanh(enc(x)); recon=dec(z); loss=((recon-x)**2).mean(); loss.backward(); opt.step()
```
Clears gradients left from the previous optimization step so they are not accumulated unintentionally.

### Line 8
```python
print("latent",z.shape,"loss",float(loss))
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.
