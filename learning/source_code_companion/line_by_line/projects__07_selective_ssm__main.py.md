# `projects/07_selective_ssm/main.py`

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
class SelectiveCell(nn.Module):
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 5
```python
    def __init__(self,d):
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 6
```python
        super().__init__(); self.decay=nn.Linear(d,d); self.write=nn.Linear(d,d)
```
Creates or updates `super().__init__(); self.decay`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 7
```python
    def forward(self,x,h):
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 8
```python
        a=torch.sigmoid(self.decay(x))*0.99
```
Maps logits to values between zero and one; interpret them as probabilities only after calibration evidence.

### Line 9
```python
        b=torch.tanh(self.write(x))
```
Creates or updates `b`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 10
```python
        return a*h+(1-a)*b
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 11
```python
cell=SelectiveCell(3); h=torch.zeros(1,3)
```
Creates or updates `cell`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 12
```python
for x in torch.eye(3): h=cell(x[None],h); print(h.detach().numpy().round(3))
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.
