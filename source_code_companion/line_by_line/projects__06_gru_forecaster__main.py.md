# `projects/06_gru_forecaster/main.py`

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
class GRUForecaster(nn.Module):
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 5
```python
    def __init__(self,f=6,h=32,o=2):
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 6
```python
        super().__init__(); self.gru=nn.GRU(f,h,batch_first=True); self.head=nn.Linear(h,o)
```
Creates or updates `super().__init__(); self.gru`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 7
```python
    def forward(self,x): return self.head(self.gru(x)[0][:,-1])
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 8
```python
if __name__=='__main__': print(GRUForecaster()(torch.randn(8,20,6)).shape)
```
Branches only when this condition is true; verify both the true and false paths in tests.
