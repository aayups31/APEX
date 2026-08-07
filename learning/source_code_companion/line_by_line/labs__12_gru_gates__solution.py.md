# `labs/12_gru_gates/solution.py`

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
torch.manual_seed(2); cell=torch.nn.GRUCell(2,4); h=torch.zeros(1,4)
```
Fixes a random seed to make the experiment easier to reproduce and compare.

### Line 4
```python
for x in [torch.tensor([[1.,0.]]),torch.tensor([[0.,1.]]),torch.tensor([[0.,1.]])]:
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 5
```python
    h=cell(x,h); print(h.detach().numpy().round(3))
```
Creates or updates `h`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.
