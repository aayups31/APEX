# `apex_engine/src/apexsim/training.py`

**Role:** Owns optimization, validation, checkpoints and model-specific loss paths.

The training loop is a state machine: clear gradients, forward, measure loss, backpropagate, update, validate, compare and persist.

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
import json
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 4
```python
import random
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 5
```python
from dataclasses import dataclass
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 6
```python
from pathlib import Path
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 7
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 8
```python
import numpy as np
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 9
```python
import torch
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 10
```python
from torch import nn
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 11
```python
from torch.utils.data import DataLoader
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 12
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 13
```python
from apexsim.config import ProjectConfig
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 14
```python
from apexsim.models.rssm import RSSMWorldModel
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 15
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 16
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 17
```python
@dataclass
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 18
```python
class TrainingResult:
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 19
```python
    best_val_loss: float
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 20
```python
    epochs_completed: int
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 21
```python
    checkpoint_path: Path
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 22
```python
    history_path: Path
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 23
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 24
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 25
```python
def seed_everything(seed: int) -> None:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 26
```python
    random.seed(seed)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 27
```python
    np.random.seed(seed)
```
Fixes a random seed to make the experiment easier to reproduce and compare.

### Line 28
```python
    torch.manual_seed(seed)
```
Fixes a random seed to make the experiment easier to reproduce and compare.

### Line 29
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 30
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 31
```python
def _batch_loss(model: nn.Module, batch: dict, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 32
```python
    history = batch["history"].to(device)
```
Creates or updates `history`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 33
```python
    future_inputs = batch["future_inputs"].to(device)
```
Creates or updates `future_inputs`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 34
```python
    targets = batch["future_targets"].to(device)
```
Creates or updates `targets`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 35
```python
    if isinstance(model, RSSMWorldModel):
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 36
```python
        predictions, kl = model(history, future_inputs, future_targets=targets)
```
Creates or updates `predictions, kl`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 37
```python
        reconstruction = torch.nn.functional.smooth_l1_loss(predictions, targets)
```
Creates or updates `reconstruction`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 38
```python
        # KL weight is intentionally modest for a small educational dataset.
```
Documents an assumption, intent or constraint that should remain aligned with the implementation.

### Line 39
```python
        loss = reconstruction + 0.02 * kl
```
Creates or updates `loss`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 40
```python
    else:
```
Handles all remaining cases; inspect whether this fallback is intentionally broad.

### Line 41
```python
        predictions = model(history, future_inputs)
```
Creates or updates `predictions`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 42
```python
        loss = torch.nn.functional.smooth_l1_loss(predictions, targets)
```
Creates or updates `loss`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 43
```python
    return loss, predictions
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 44
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 45
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 46
```python
def train_world_model(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 47
```python
    model: nn.Module,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 48
```python
    train_loader: DataLoader,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 49
```python
    val_loader: DataLoader,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 50
```python
    config: ProjectConfig,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 51
```python
    run_dir: str | Path,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 52
```python
) -> TrainingResult:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 53
```python
    seed_everything(config.seed)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 54
```python
    run_path = Path(run_dir)
```
Creates or updates `run_path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 55
```python
    run_path.mkdir(parents=True, exist_ok=True)
```
Creates or updates `run_path.mkdir(parents`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 56
```python
    device = torch.device(config.training.device)
```
Creates or updates `device`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 57
```python
    model.to(device)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 58
```python
    optimizer = torch.optim.AdamW(
```
Creates or updates `optimizer`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 59
```python
        model.parameters(),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 60
```python
        lr=config.training.learning_rate,
```
Creates or updates `lr`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 61
```python
        weight_decay=config.training.weight_decay,
```
Creates or updates `weight_decay`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 62
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 63
```python
    history: list[dict[str, float | int]] = []
```
Creates or updates `history: list[dict[str, float | int]]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 64
```python
    best_val = float("inf")
```
Creates or updates `best_val`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 65
```python
    stale_epochs = 0
```
Creates or updates `stale_epochs`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 66
```python
    checkpoint = run_path / "world_model.pt"
```
Creates or updates `checkpoint`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 67
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 68
```python
    for epoch in range(1, config.training.epochs + 1):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 69
```python
        model.train()
```
Enables training behaviour such as dropout and running-statistic updates.

### Line 70
```python
        train_losses = []
```
Creates or updates `train_losses`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 71
```python
        for batch in train_loader:
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 72
```python
            optimizer.zero_grad(set_to_none=True)
```
Clears gradients left from the previous optimization step so they are not accumulated unintentionally.

### Line 73
```python
            loss, _ = _batch_loss(model, batch, device)
```
Creates or updates `loss, _`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 74
```python
            loss.backward()
```
Runs reverse-mode automatic differentiation to populate gradients for trainable parameters.

### Line 75
```python
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.training.grad_clip)
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 76
```python
            optimizer.step()
```
Updates trainable parameters using the optimizer state and current gradients.

### Line 77
```python
            train_losses.append(float(loss.detach().cpu()))
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 78
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 79
```python
        model.eval()
```
Enables deterministic evaluation behaviour for layers that differ between training and inference.

### Line 80
```python
        val_losses = []
```
Creates or updates `val_losses`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 81
```python
        with torch.no_grad():
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 82
```python
            for batch in val_loader:
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 83
```python
                loss, _ = _batch_loss(model, batch, device)
```
Creates or updates `loss, _`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 84
```python
                val_losses.append(float(loss.detach().cpu()))
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 85
```python
        train_loss = float(np.mean(train_losses))
```
Creates or updates `train_loss`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 86
```python
        val_loss = float(np.mean(val_losses))
```
Creates or updates `val_loss`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 87
```python
        history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss})
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 88
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 89
```python
        if val_loss < best_val - 1e-6:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 90
```python
            best_val = val_loss
```
Creates or updates `best_val`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 91
```python
            stale_epochs = 0
```
Creates or updates `stale_epochs`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 92
```python
            torch.save(model.state_dict(), checkpoint)
```
Persists an artifact. The surrounding code should include run identity, schema and preprocessing lineage.

### Line 93
```python
        else:
```
Handles all remaining cases; inspect whether this fallback is intentionally broad.

### Line 94
```python
            stale_epochs += 1
```
Creates or updates `stale_epochs +`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 95
```python
            if stale_epochs >= config.training.patience:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 96
```python
                break
```
Stops the enclosing loop after the required condition is reached.

### Line 97
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 98
```python
    model.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True))
```
Creates or updates `model.load_state_dict(torch.load(checkpoint, map_location`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 99
```python
    history_path = run_path / "training_history.json"
```
Creates or updates `history_path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 100
```python
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
```
Persists an artifact. The surrounding code should include run identity, schema and preprocessing lineage.

### Line 101
```python
    return TrainingResult(best_val, len(history), checkpoint, history_path)
```
Returns the result to the caller; this is the function output boundary that tests should assert.
