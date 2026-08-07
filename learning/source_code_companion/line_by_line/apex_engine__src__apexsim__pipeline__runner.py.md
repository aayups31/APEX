# `apex_engine/src/apexsim/pipeline/runner.py`

**Role:** Coordinates run lifecycle and stage transitions.

The runner owns ordering, failure state and summary publication while stage functions own domain logic.

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
from datetime import datetime, timezone
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 5
```python
from pathlib import Path
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 6
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 7
```python
from apexsim.config import ProjectConfig
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 8
```python
from apexsim.pipeline.stages import (
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 9
```python
    ablation_stage,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 10
```python
    dataset_stage,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 11
```python
    evaluate_stage,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 12
```python
    ingest_stage,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 13
```python
    publish_stage,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 14
```python
    quality_stage,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 15
```python
    train_stage,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 16
```python
)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 17
```python
from apexsim.registry import RunRegistry
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 18
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 19
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 20
```python
def run_pipeline(config: ProjectConfig, run_id: str) -> dict:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 21
```python
    run_dir = config.artifacts_dir / run_id
```
Creates or updates `run_dir`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 22
```python
    run_dir.mkdir(parents=True, exist_ok=True)
```
Creates or updates `run_dir.mkdir(parents`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 23
```python
    registry = RunRegistry(config.artifacts_dir / "runs.sqlite")
```
Creates or updates `registry`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 24
```python
    registry.start(run_id, config.model.kind, str(run_dir))
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 25
```python
    started = datetime.now(timezone.utc).isoformat()
```
Creates or updates `started`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 26
```python
    try:
```
Begins an operation that may fail for an expected reason.

### Line 27
```python
        canonical = ingest_stage(config, run_dir)
```
Creates or updates `canonical`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 28
```python
        quality = quality_stage(canonical, run_dir)
```
Creates or updates `quality`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 29
```python
        dataset = dataset_stage(config, canonical, run_dir)
```
Creates or updates `dataset`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 30
```python
        model = train_stage(config, canonical, run_dir)
```
Creates or updates `model`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 31
```python
        metrics = evaluate_stage(config, canonical, run_dir)
```
Creates or updates `metrics`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 32
```python
        ablations = ablation_stage(config, canonical, run_dir)
```
Creates or updates `ablations`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 33
```python
        publication = publish_stage(config, canonical, run_dir)
```
Creates or updates `publication`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 34
```python
        summary = {
```
Creates or updates `summary`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 35
```python
            "run_id": run_id,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 36
```python
            "status": "succeeded",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 37
```python
            "started_at": started,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 38
```python
            "finished_at": datetime.now(timezone.utc).isoformat(),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 39
```python
            "canonical_data": str(canonical),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 40
```python
            "quality": quality,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 41
```python
            "splits": dataset["splits"],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 42
```python
            "model": model,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 43
```python
            "metrics": metrics,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 44
```python
            "best_ablation": ablations[0],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 45
```python
            "publication": publication,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 46
```python
        }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 47
```python
        (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
```
Persists an artifact. The surrounding code should include run identity, schema and preprocessing lineage.

### Line 48
```python
        registry.finish(run_id, "succeeded", metrics)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 49
```python
        return summary
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 50
```python
    except Exception:
```
Handles a specific failure mode. The handler should preserve useful diagnostic evidence.

### Line 51
```python
        registry.finish(run_id, "failed")
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 52
```python
        raise
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.
