# `apex_engine/src/apexsim/serving.py`

**Role:** Creates typed API boundaries for health, runs and scenarios.

Serving should load compatible artifacts once, validate units and avoid exposing internal tensors as public contracts.

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
from fastapi import FastAPI, HTTPException
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 7
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 8
```python
from apexsim.registry import RunRegistry
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
def create_api(artifacts_dir: str | Path = "artifacts/runs") -> FastAPI:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 12
```python
    root = Path(artifacts_dir)
```
Creates or updates `root`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 13
```python
    registry = RunRegistry(root / "runs.sqlite")
```
Creates or updates `registry`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 14
```python
    app = FastAPI(title="Project APEX API", version="0.1.0")
```
Creates or updates `app`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 15
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 16
```python
    @app.get("/health")
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 17
```python
    def health() -> dict[str, str]:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 18
```python
        return {"status": "ok"}
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 19
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 20
```python
    @app.get("/runs")
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 21
```python
    def runs() -> list[dict]:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 22
```python
        return registry.list_runs()
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 23
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 24
```python
    @app.get("/runs/{run_id}")
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 25
```python
    def run_details(run_id: str) -> dict:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 26
```python
        path = root / run_id / "summary.json"
```
Creates or updates `path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 27
```python
        if not path.exists():
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 28
```python
            raise HTTPException(status_code=404, detail="Run not found")
```
Stops execution because an invariant or supported-condition check failed.

### Line 29
```python
        return json.loads(path.read_text())
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 30
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 31
```python
    @app.get("/runs/{run_id}/rollout")
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 32
```python
    def rollout_preview(run_id: str) -> list[dict]:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 33
```python
        path = root / run_id / "rollout_preview.csv"
```
Creates or updates `path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 34
```python
        if not path.exists():
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 35
```python
            raise HTTPException(status_code=404, detail="Rollout preview not found")
```
Stops execution because an invariant or supported-condition check failed.

### Line 36
```python
        import pandas as pd
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 37
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 38
```python
        return pd.read_csv(path).to_dict(orient="records")
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 39
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 40
```python
    return app
```
Returns the result to the caller; this is the function output boundary that tests should assert.
