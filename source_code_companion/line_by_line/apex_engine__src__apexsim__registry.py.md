# `apex_engine/src/apexsim/registry.py`

**Role:** Persists run identity, status, configuration, metrics and artifact locations.

A registry is evidence, not a leaderboard. It makes promotion and rollback auditable.

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
import sqlite3
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 5
```python
from datetime import datetime, timezone
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

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 9
```python
class RunRegistry:
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 10
```python
    def __init__(self, database_path: str | Path) -> None:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 11
```python
        self.path = Path(database_path)
```
Creates or updates `self.path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 12
```python
        self.path.parent.mkdir(parents=True, exist_ok=True)
```
Creates or updates `self.path.parent.mkdir(parents`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 13
```python
        with self._connect() as connection:
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 14
```python
            connection.execute(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 15
```python
                """
```
Begins or ends documentation describing the module, class or function contract.

### Line 16
```python
                CREATE TABLE IF NOT EXISTS runs (
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 17
```python
                    run_id TEXT PRIMARY KEY,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 18
```python
                    status TEXT NOT NULL,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 19
```python
                    model_kind TEXT NOT NULL,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 20
```python
                    started_at TEXT NOT NULL,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 21
```python
                    finished_at TEXT,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 22
```python
                    run_dir TEXT NOT NULL,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 23
```python
                    metrics_json TEXT
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 24
```python
                )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 25
```python
                """
```
Begins or ends documentation describing the module, class or function contract.

### Line 26
```python
            )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 27
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 28
```python
    def _connect(self) -> sqlite3.Connection:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 29
```python
        return sqlite3.connect(self.path)
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 30
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 31
```python
    def start(self, run_id: str, model_kind: str, run_dir: str) -> None:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 32
```python
        now = datetime.now(timezone.utc).isoformat()
```
Creates or updates `now`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 33
```python
        with self._connect() as connection:
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 34
```python
            connection.execute(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 35
```python
                "INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 36
```python
                (run_id, "running", model_kind, now, None, run_dir, None),
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
    def finish(self, run_id: str, status: str, metrics: dict | None = None) -> None:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 40
```python
        now = datetime.now(timezone.utc).isoformat()
```
Creates or updates `now`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 41
```python
        with self._connect() as connection:
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 42
```python
            connection.execute(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 43
```python
                "UPDATE runs SET status=?, finished_at=?, metrics_json=? WHERE run_id=?",
```
Creates or updates `"UPDATE runs SET status`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 44
```python
                (status, now, json.dumps(metrics) if metrics else None, run_id),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 45
```python
            )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 46
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 47
```python
    def list_runs(self) -> list[dict]:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 48
```python
        with self._connect() as connection:
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 49
```python
            connection.row_factory = sqlite3.Row
```
Creates or updates `connection.row_factory`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 50
```python
            rows = connection.execute("SELECT * FROM runs ORDER BY started_at DESC").fetchall()
```
Creates or updates `rows`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 51
```python
        result = []
```
Creates or updates `result`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 52
```python
        for row in rows:
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 53
```python
            item = dict(row)
```
Creates or updates `item`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 54
```python
            item["metrics"] = json.loads(item.pop("metrics_json")) if item.get("metrics_json") else None
```
Creates or updates `item["metrics"]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 55
```python
            result.append(item)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 56
```python
        return result
```
Returns the result to the caller; this is the function output boundary that tests should assert.
