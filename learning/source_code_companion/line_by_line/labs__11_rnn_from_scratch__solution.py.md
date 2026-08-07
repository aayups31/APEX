# `labs/11_rnn_from_scratch/solution.py`

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
torch.manual_seed(0); W=torch.randn(3,2); U=torch.randn(3,3); b=torch.zeros(3); h=torch.zeros(3)
```
Fixes a random seed to make the experiment easier to reproduce and compare.

### Line 4
```python
sequence=torch.tensor([[1.,0.],[0.,1.],[1.,1.]])
```
Creates or updates `sequence`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 5
```python
for t,x in enumerate(sequence):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 6
```python
    h=torch.tanh(W@x+U@h+b); print(t,h.numpy().round(3))
```
Creates or updates `h`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.
