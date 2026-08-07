# `labs/06_autograd_drag/solution.py`

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
speed=torch.linspace(5,70,200)
```
Creates or updates `speed`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 4
```python
true_drag=0.002
```
Creates or updates `true_drag`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 5
```python
target=-true_drag*speed**2
```
Creates or updates `target`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 6
```python
drag=torch.tensor(0.01,requires_grad=True)
```
Creates or updates `drag`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 7
```python
opt=torch.optim.SGD([drag],lr=1e-7)
```
Creates or updates `opt`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 8
```python
for step in range(200):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 9
```python
    opt.zero_grad()
```
Clears gradients left from the previous optimization step so they are not accumulated unintentionally.

### Line 10
```python
    pred=-drag*speed**2
```
Creates or updates `pred`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 11
```python
    loss=((pred-target)**2).mean()
```
Creates or updates `loss`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 12
```python
    loss.backward(); opt.step()
```
Runs reverse-mode automatic differentiation to populate gradients for trainable parameters.

### Line 13
```python
print("learned drag:", drag.item(), "loss:", loss.item())
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.
