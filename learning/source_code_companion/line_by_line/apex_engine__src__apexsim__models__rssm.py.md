# `apex_engine/src/apexsim/models/rssm.py`

**Role:** Implements deterministic memory plus stochastic prior/posterior latent state.

Training may use observations through the posterior; imagination must proceed through the prior without future evidence.

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
from torch.distributions import Normal, kl_divergence
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 6
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 7
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 8
```python
class RSSMWorldModel(nn.Module):
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 9
```python
    """Compact Dreamer-style recurrent state-space model for telemetry.
```
Begins or ends documentation describing the module, class or function contract.

### Line 10
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 11
```python
    h_t is deterministic memory. z_t is a stochastic latent state. The posterior sees the observed
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 12
```python
    state during training; the prior is used for imagination when future observations are unavailable.
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 13
```python
    """
```
Begins or ends documentation describing the module, class or function contract.

### Line 14
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 15
```python
    def __init__(self, input_dim: int, state_dim: int, hidden_dim: int = 64, latent_dim: int = 12) -> None:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 16
```python
        super().__init__()
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 17
```python
        self.input_dim = input_dim
```
Creates or updates `self.input_dim`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 18
```python
        self.state_dim = state_dim
```
Creates or updates `self.state_dim`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 19
```python
        self.hidden_dim = hidden_dim
```
Creates or updates `self.hidden_dim`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 20
```python
        self.latent_dim = latent_dim
```
Creates or updates `self.latent_dim`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 21
```python
        self.action_context_dim = input_dim - state_dim
```
Creates or updates `self.action_context_dim`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 22
```python
        self.gru = nn.GRUCell(latent_dim + self.action_context_dim, hidden_dim)
```
Creates or updates `self.gru`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 23
```python
        self.prior = nn.Linear(hidden_dim, 2 * latent_dim)
```
Creates or updates `self.prior`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 24
```python
        self.posterior = nn.Linear(hidden_dim + state_dim, 2 * latent_dim)
```
Creates or updates `self.posterior`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 25
```python
        self.decoder = nn.Sequential(
```
Creates or updates `self.decoder`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 26
```python
            nn.Linear(hidden_dim + latent_dim, hidden_dim),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 27
```python
            nn.SiLU(),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 28
```python
            nn.Linear(hidden_dim, state_dim),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 29
```python
        )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 30
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 31
```python
    @staticmethod
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 32
```python
    def _distribution(parameters: torch.Tensor) -> Normal:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 33
```python
        mean, raw_std = parameters.chunk(2, dim=-1)
```
Creates or updates `mean, raw_std`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 34
```python
        std = torch.nn.functional.softplus(raw_std) + 0.1
```
Creates or updates `std`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 35
```python
        return Normal(mean, std)
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 36
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 37
```python
    def forward(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 38
```python
        self,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 39
```python
        history: torch.Tensor,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 40
```python
        future_inputs: torch.Tensor,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 41
```python
        future_targets: torch.Tensor | None = None,
```
Creates or updates `future_targets: torch.Tensor | None`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 42
```python
    ) -> tuple[torch.Tensor, torch.Tensor]:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 43
```python
        batch = history.shape[0]
```
Creates or updates `batch`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 44
```python
        h = history.new_zeros((batch, self.hidden_dim))
```
Creates or updates `h`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 45
```python
        z = history.new_zeros((batch, self.latent_dim))
```
Creates or updates `z`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 46
```python
        # Observe history to initialize belief state.
```
Documents an assumption, intent or constraint that should remain aligned with the implementation.

### Line 47
```python
        for step in range(history.shape[1]):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 48
```python
            state = history[:, step, : self.state_dim]
```
Creates or updates `state`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 49
```python
            action_context = history[:, step, self.state_dim :]
```
Creates or updates `action_context`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 50
```python
            h = self.gru(torch.cat([z, action_context], dim=-1), h)
```
Concatenates tensors or arrays; verify that every non-concatenated axis has identical meaning and size.

### Line 51
```python
            posterior = self._distribution(self.posterior(torch.cat([h, state], dim=-1)))
```
Concatenates tensors or arrays; verify that every non-concatenated axis has identical meaning and size.

### Line 52
```python
            z = posterior.rsample()
```
Creates or updates `z`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 53
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 54
```python
        outputs = []
```
Creates or updates `outputs`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 55
```python
        kl_terms = []
```
Creates or updates `kl_terms`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 56
```python
        previous_state = history[:, -1, : self.state_dim]
```
Creates or updates `previous_state`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 57
```python
        for step in range(future_inputs.shape[1]):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 58
```python
            action_context = future_inputs[:, step, self.state_dim :]
```
Creates or updates `action_context`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 59
```python
            h = self.gru(torch.cat([z, action_context], dim=-1), h)
```
Concatenates tensors or arrays; verify that every non-concatenated axis has identical meaning and size.

### Line 60
```python
            prior = self._distribution(self.prior(h))
```
Creates or updates `prior`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 61
```python
            if future_targets is not None:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 62
```python
                posterior = self._distribution(
```
Creates or updates `posterior`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 63
```python
                    self.posterior(torch.cat([h, future_targets[:, step]], dim=-1))
```
Concatenates tensors or arrays; verify that every non-concatenated axis has identical meaning and size.

### Line 64
```python
                )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 65
```python
                z = posterior.rsample()
```
Creates or updates `z`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 66
```python
                kl_terms.append(kl_divergence(posterior, prior).sum(dim=-1))
```
Creates or updates `kl_terms.append(kl_divergence(posterior, prior).sum(dim`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 67
```python
            else:
```
Handles all remaining cases; inspect whether this fallback is intentionally broad.

### Line 68
```python
                z = prior.rsample()
```
Creates or updates `z`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 69
```python
            previous_state = self.decoder(torch.cat([h, z], dim=-1))
```
Concatenates tensors or arrays; verify that every non-concatenated axis has identical meaning and size.

### Line 70
```python
            outputs.append(previous_state)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 71
```python
        prediction = torch.stack(outputs, dim=1)
```
Creates a new axis by stacking aligned values; document what the new axis represents.

### Line 72
```python
        kl = torch.stack(kl_terms, dim=1).mean() if kl_terms else prediction.new_tensor(0.0)
```
Creates a new axis by stacking aligned values; document what the new axis represents.

### Line 73
```python
        return prediction, kl
```
Returns the result to the caller; this is the function output boundary that tests should assert.
