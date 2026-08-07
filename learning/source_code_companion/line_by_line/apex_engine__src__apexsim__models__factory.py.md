# `apex_engine/src/apexsim/models/factory.py`

**Role:** Creates the configured model behind one common interface.

The factory isolates model selection so pipeline and evaluation logic do not fork by architecture.

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
from torch import nn
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 4
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 5
```python
from apexsim.config import ModelConfig
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 6
```python
from apexsim.models.gru_world_model import GRUWorldModel
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 7
```python
from apexsim.models.rssm import RSSMWorldModel
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 8
```python
from apexsim.models.ssm_world_model import SSMWorldModel
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 9
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 10
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 11
```python
def build_model(config: ModelConfig, input_dim: int, state_dim: int) -> nn.Module:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 12
```python
    if config.kind == "gru":
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 13
```python
        return GRUWorldModel(input_dim, state_dim, config.hidden_dim, config.layers, config.dropout)
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 14
```python
    if config.kind == "ssm":
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 15
```python
        return SSMWorldModel(input_dim, state_dim, config.hidden_dim, config.layers)
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 16
```python
    if config.kind == "rssm":
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 17
```python
        return RSSMWorldModel(input_dim, state_dim, config.hidden_dim, config.latent_dim)
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 18
```python
    raise ValueError(f"Model kind {config.kind!r} is not a neural world model")
```
Stops execution because an invariant or supported-condition check failed.
