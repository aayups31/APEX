# `projects/08_rssm_imagination/main.py`

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
cell=nn.GRUCell(5,8); prior=nn.Linear(8,4); posterior=nn.Linear(8+3,4)
```
Creates or updates `cell`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 5
```python
h=torch.zeros(2,8); prev_z=torch.zeros(2,2); action=torch.randn(2,3); obs_embed=torch.randn(2,3)
```
Creates or updates `h`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 6
```python
h=cell(torch.cat([prev_z,action],-1),h)
```
Concatenates tensors or arrays; verify that every non-concatenated axis has identical meaning and size.

### Line 7
```python
prior_stats=prior(h); post_stats=posterior(torch.cat([h,obs_embed],-1))
```
Concatenates tensors or arrays; verify that every non-concatenated axis has identical meaning and size.

### Line 8
```python
print("h",h.shape,"prior",prior_stats.shape,"posterior",post_stats.shape)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.
