# `apex_engine/src/apexsim/models/gru_world_model.py`

**Role:** Implements deterministic recurrent history encoding and autoregressive rollout.

At each future step, known controls/context enter the transition while predicted state replaces the unknown future state.

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
class GRUWorldModel(nn.Module):
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 8
```python
    """Deterministic sequence model that predicts future telemetry states.
```
Begins or ends documentation describing the module, class or function contract.

### Line 9
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 10
```python
    The history encoder compresses the observed past into a hidden state. During rollout, the model
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 11
```python
    consumes the planned future actions/context and its own previous predicted state.
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
    def __init__(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 15
```python
        self,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 16
```python
        input_dim: int,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 17
```python
        state_dim: int,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 18
```python
        hidden_dim: int = 64,
```
Creates or updates `hidden_dim: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 19
```python
        layers: int = 1,
```
Creates or updates `layers: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 20
```python
        dropout: float = 0.0,
```
Creates or updates `dropout: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 21
```python
    ) -> None:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 22
```python
        super().__init__()
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 23
```python
        self.state_dim = state_dim
```
Creates or updates `self.state_dim`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 24
```python
        self.input_dim = input_dim
```
Creates or updates `self.input_dim`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 25
```python
        self.encoder = nn.GRU(
```
Creates or updates `self.encoder`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 26
```python
            input_dim,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 27
```python
            hidden_dim,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 28
```python
            num_layers=layers,
```
Creates or updates `num_layers`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 29
```python
            batch_first=True,
```
Creates or updates `batch_first`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 30
```python
            dropout=dropout if layers > 1 else 0.0,
```
Creates or updates `dropout`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 31
```python
        )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 32
```python
        self.transition = nn.GRUCell(input_dim, hidden_dim)
```
Creates or updates `self.transition`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 33
```python
        self.decoder = nn.Sequential(
```
Creates or updates `self.decoder`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 34
```python
            nn.Linear(hidden_dim, hidden_dim),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 35
```python
            nn.SiLU(),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 36
```python
            nn.Linear(hidden_dim, state_dim),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 37
```python
        )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 38
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 39
```python
    def forward(self, history: torch.Tensor, future_inputs: torch.Tensor) -> torch.Tensor:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 40
```python
        _, hidden = self.encoder(history)
```
Creates or updates `_, hidden`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 41
```python
        hidden_t = hidden[-1]
```
Creates or updates `hidden_t`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 42
```python
        predictions = []
```
Creates or updates `predictions`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 43
```python
        future_t = future_inputs.clone()
```
Creates or updates `future_t`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 44
```python
        previous_state = history[:, -1, : self.state_dim]
```
Creates or updates `previous_state`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 45
```python
        for step in range(future_t.shape[1]):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 46
```python
            step_input = future_t[:, step].clone()
```
Creates or updates `step_input`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 47
```python
            step_input[:, : self.state_dim] = previous_state
```
Creates or updates `step_input[:, : self.state_dim]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 48
```python
            hidden_t = self.transition(step_input, hidden_t)
```
Creates or updates `hidden_t`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 49
```python
            previous_state = self.decoder(hidden_t)
```
Creates or updates `previous_state`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 50
```python
            predictions.append(previous_state)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 51
```python
        return torch.stack(predictions, dim=1)
```
Returns the result to the caller; this is the function output boundary that tests should assert.
