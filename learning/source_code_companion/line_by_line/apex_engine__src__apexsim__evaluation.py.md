# `apex_engine/src/apexsim/evaluation.py`

**Role:** Converts standardized model output into physical and horizon-aware evidence.

Evaluation must use held-out groups, inverse transformations and physical guardrails; teacher-forced loss alone is not simulation quality.

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
from pathlib import Path
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 5
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 6
```python
import numpy as np
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 7
```python
import torch
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 8
```python
from torch import nn
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 9
```python
from torch.utils.data import DataLoader
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 10
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 11
```python
from apexsim.contracts import TARGET_COLUMNS
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 12
```python
from apexsim.data.features import Standardizer
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 13
```python
from apexsim.models.rssm import RSSMWorldModel
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 14
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 15
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 16
```python
def evaluate_world_model(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 17
```python
    model: nn.Module,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 18
```python
    loader: DataLoader,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 19
```python
    standardizer: Standardizer,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 20
```python
    output_path: str | Path | None = None,
```
Creates or updates `output_path: str | Path | None`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 21
```python
    device: str = "cpu",
```
Creates or updates `device: str`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 22
```python
) -> dict:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 23
```python
    model.eval()
```
Enables deterministic evaluation behaviour for layers that differ between training and inference.

### Line 24
```python
    model.to(device)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 25
```python
    predictions: list[np.ndarray] = []
```
Creates or updates `predictions: list[np.ndarray]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 26
```python
    targets: list[np.ndarray] = []
```
Creates or updates `targets: list[np.ndarray]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 27
```python
    with torch.no_grad():
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 28
```python
        for batch in loader:
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 29
```python
            history = batch["history"].to(device)
```
Creates or updates `history`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 30
```python
            future_inputs = batch["future_inputs"].to(device)
```
Creates or updates `future_inputs`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 31
```python
            if isinstance(model, RSSMWorldModel):
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 32
```python
                predicted, _ = model(history, future_inputs, future_targets=None)
```
Creates or updates `predicted, _`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 33
```python
            else:
```
Handles all remaining cases; inspect whether this fallback is intentionally broad.

### Line 34
```python
                predicted = model(history, future_inputs)
```
Creates or updates `predicted`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 35
```python
            predictions.append(predicted.cpu().numpy())
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 36
```python
            targets.append(batch["future_targets"].numpy())
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 37
```python
    pred_z = np.concatenate(predictions, axis=0)
```
Concatenates tensors or arrays; verify that every non-concatenated axis has identical meaning and size.

### Line 38
```python
    target_z = np.concatenate(targets, axis=0)
```
Concatenates tensors or arrays; verify that every non-concatenated axis has identical meaning and size.

### Line 39
```python
    pred = standardizer.inverse_targets(pred_z)
```
Creates or updates `pred`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 40
```python
    target = standardizer.inverse_targets(target_z)
```
Creates or updates `target`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 41
```python
    error = pred - target
```
Creates or updates `error`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 42
```python
    horizon_rmse = np.sqrt(np.mean(error**2, axis=(0, 2)))
```
Creates or updates `horizon_rmse`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 43
```python
    horizon_mae = np.mean(np.abs(error), axis=(0, 2))
```
Creates or updates `horizon_mae`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 44
```python
    per_feature = {}
```
Creates or updates `per_feature`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 45
```python
    for index, feature in enumerate(TARGET_COLUMNS):
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 46
```python
        per_feature[feature] = {
```
Creates or updates `per_feature[feature]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 47
```python
            "mae": float(np.mean(np.abs(error[..., index]))),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 48
```python
            "rmse": float(np.sqrt(np.mean(error[..., index] ** 2))),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 49
```python
        }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 50
```python
    physical = {
```
Creates or updates `physical`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 51
```python
        "negative_speed_rate": float(np.mean(pred[..., 0] < 0)),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 52
```python
        "extreme_speed_rate": float(np.mean(pred[..., 0] > 120)),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 53
```python
        "progress_unit_circle_error": float(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 54
```python
            np.mean(np.abs(pred[..., 2] ** 2 + pred[..., 3] ** 2 - 1.0))
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 55
```python
        ),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 56
```python
    }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 57
```python
    metrics = {
```
Creates or updates `metrics`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 58
```python
        "overall_mae": float(np.mean(np.abs(error))),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 59
```python
        "overall_rmse": float(np.sqrt(np.mean(error**2))),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 60
```python
        "speed_mae_mps": per_feature["speed_mps"]["mae"],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 61
```python
        "speed_rmse_mps": per_feature["speed_mps"]["rmse"],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 62
```python
        "per_feature": per_feature,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 63
```python
        "horizon_mae": horizon_mae.tolist(),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 64
```python
        "horizon_rmse": horizon_rmse.tolist(),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 65
```python
        "physical_violations": physical,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 66
```python
        "samples": int(pred.shape[0]),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 67
```python
    }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 68
```python
    if output_path is not None:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 69
```python
        path = Path(output_path)
```
Creates or updates `path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 70
```python
        path.parent.mkdir(parents=True, exist_ok=True)
```
Creates or updates `path.parent.mkdir(parents`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 71
```python
        path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
```
Persists an artifact. The surrounding code should include run identity, schema and preprocessing lineage.

### Line 72
```python
    return metrics
```
Returns the result to the caller; this is the function output boundary that tests should assert.
