# `apex_engine/src/apexsim/models/ssm_world_model.py`

**Role:** Implements an educational stable selective state-space challenger.

It demonstrates content-dependent memory but does not claim full optimized Mamba fidelity.

## Line-by-line guide

### Line 1
```python
from __future__ import annotations
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 2
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 3
```python
import torch
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 4
```python
from torch import nn
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 5
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 6
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 7
```python
class SelectiveSSMCell(nn.Module):
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 8
```python
    """Small educational selective state-space cell.
```
Begins or ends documentation describing the module, class or function contract.

### Line 9
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 10
```python
    This is intentionally not a full Mamba kernel. It demonstrates the central idea: a persistent
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 11
```python
    state with input-dependent write/forget gates and stable diagonal decay.
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 12
```python
    """
```
Begins or ends documentation describing the module, class or function contract.

### Line 13
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 14
```python
    def __init__(self, input_dim: int, hidden_dim: int) -> None:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 15
```python
        super().__init__()
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 16
```python
        self.logit_decay = nn.Parameter(torch.zeros(hidden_dim))
```
Creates or updates `self.logit_decay`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 17
```python
        self.input_projection = nn.Linear(input_dim, hidden_dim)
```
Creates or updates `self.input_projection`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 18
```python
        self.gate_projection = nn.Linear(input_dim, hidden_dim)
```
Creates or updates `self.gate_projection`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 19
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 20
```python
    def forward(self, x: torch.Tensor, state: torch.Tensor) -> torch.Tensor:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 21
```python
        decay = torch.sigmoid(self.logit_decay).unsqueeze(0)
```
Maps logits to values between zero and one; interpret them as probabilities only after calibration evidence.

### Line 22
```python
        candidate = torch.tanh(self.input_projection(x))
```
Creates or updates `candidate`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 23
```python
        gate = torch.sigmoid(self.gate_projection(x))
```
Maps logits to values between zero and one; interpret them as probabilities only after calibration evidence.

### Line 24
```python
        return decay * state + (1.0 - decay) * gate * candidate
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 25
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 26
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 27
```python
class SSMWorldModel(nn.Module):
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 28
```python
    def __init__(self, input_dim: int, state_dim: int, hidden_dim: int = 64, layers: int = 2) -> None:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 29
```python
        super().__init__()
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 30
```python
        self.state_dim = state_dim
```
Creates or updates `self.state_dim`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 31
```python
        self.cells = nn.ModuleList(
```
Creates or updates `self.cells`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 32
```python
            [SelectiveSSMCell(input_dim if i == 0 else hidden_dim, hidden_dim) for i in range(layers)]
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 33
```python
        )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 34
```python
        self.decoder = nn.Sequential(nn.LayerNorm(hidden_dim), nn.Linear(hidden_dim, state_dim))
```
Creates or updates `self.decoder`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 35
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 36
```python
    def _step(self, x: torch.Tensor, states: list[torch.Tensor]) -> tuple[torch.Tensor, list[torch.Tensor]]:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 37
```python
        updated: list[torch.Tensor] = []
```
Creates or updates `updated: list[torch.Tensor]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 38
```python
        value = x
```
Creates or updates `value`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 39
```python
        for cell, state in zip(self.cells, states):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 40
```python
            state = cell(value, state)
```
Creates or updates `state`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 41
```python
            updated.append(state)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 42
```python
            value = state
```
Creates or updates `value`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 43
```python
        return self.decoder(value), updated
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 44
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 45
```python
    def forward(self, history: torch.Tensor, future_inputs: torch.Tensor) -> torch.Tensor:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 46
```python
        batch = history.shape[0]
```
Creates or updates `batch`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 47
```python
        hidden_dim = self.cells[0].logit_decay.shape[0]
```
Creates or updates `hidden_dim`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 48
```python
        states = [history.new_zeros((batch, hidden_dim)) for _ in self.cells]
```
Creates or updates `states`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 49
```python
        for step in range(history.shape[1]):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 50
```python
            _, states = self._step(history[:, step], states)
```
Creates or updates `_, states`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 51
```python
        previous_state = history[:, -1, : self.state_dim]
```
Creates or updates `previous_state`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 52
```python
        outputs = []
```
Creates or updates `outputs`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 53
```python
        for step in range(future_inputs.shape[1]):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 54
```python
            x = future_inputs[:, step].clone()
```
Creates or updates `x`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 55
```python
            x[:, : self.state_dim] = previous_state
```
Creates or updates `x[:, : self.state_dim]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 56
```python
            previous_state, states = self._step(x, states)
```
Creates or updates `previous_state, states`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 57
```python
            outputs.append(previous_state)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 58
```python
        return torch.stack(outputs, dim=1)
```
Returns the result to the caller; this is the function output boundary that tests should assert.
