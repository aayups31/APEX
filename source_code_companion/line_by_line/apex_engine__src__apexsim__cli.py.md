# `apex_engine/src/apexsim/cli.py`

**Role:** Routes human commands to tested domain functions.

A CLI should be thin. It parses intent, validates inputs and calls the same adapters and stages used by tests and orchestration.

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
import typer
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 7
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 8
```python
from apexsim.config import load_config
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 9
```python
from apexsim.data.fastf1_adapter import ingest_fastf1_session
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 10
```python
from apexsim.data.openf1_adapter import ingest_openf1_session
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 11
```python
from apexsim.data.synthetic import generate_synthetic_sessions
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 12
```python
from apexsim.data.validate import validate_canonical_frame
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 13
```python
from apexsim.pipeline.runner import run_pipeline
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 14
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 15
```python
app = typer.Typer(no_args_is_help=True, help="Project APEX F1 world-simulation engine")
```
Creates or updates `app`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 16
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 17
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 18
```python
@app.command()
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 19
```python
def generate(config: Path = Path("configs/fast.yaml"), output: Path = Path("data/raw/synthetic.csv")) -> None:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 20
```python
    cfg = load_config(config)
```
Creates or updates `cfg`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 21
```python
    frame = generate_synthetic_sessions(cfg, output)
```
Creates or updates `frame`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 22
```python
    typer.echo(f"Generated {len(frame):,} canonical telemetry rows at {output}")
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

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
@app.command("ingest-fastf1")
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 26
```python
def ingest_fastf1(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 27
```python
    year: int,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 28
```python
    event: str,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 29
```python
    session: str,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 30
```python
    driver: str,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 31
```python
    output: Path = Path("data/raw/fastf1.csv"),
```
Creates or updates `output: Path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 32
```python
    sample_hz: int = 5,
```
Creates or updates `sample_hz: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 33
```python
) -> None:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 34
```python
    frame = ingest_fastf1_session(year, event, session, driver, output, sample_hz)
```
Creates or updates `frame`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 35
```python
    typer.echo(f"Ingested {len(frame):,} FastF1 rows at {output}")
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 36
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 37
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 38
```python
@app.command("ingest-openf1")
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 39
```python
def ingest_openf1(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 40
```python
    session_key: int,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 41
```python
    driver_number: int,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 42
```python
    output: Path = Path("data/raw/openf1.csv"),
```
Creates or updates `output: Path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 43
```python
    sample_hz: int = 4,
```
Creates or updates `sample_hz: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 44
```python
) -> None:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 45
```python
    frame = ingest_openf1_session(session_key, driver_number, output, sample_hz)
```
Creates or updates `frame`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 46
```python
    typer.echo(f"Ingested {len(frame):,} OpenF1 rows at {output}")
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 47
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 48
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 49
```python
@app.command()
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 50
```python
def validate(path: Path) -> None:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 51
```python
    import pandas as pd
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 52
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 53
```python
    report = validate_canonical_frame(pd.read_csv(path), strict=False)
```
Loads persisted tabular evidence; validate schema, units and ordering immediately afterward.

### Line 54
```python
    typer.echo(json.dumps(report.to_dict(), indent=2))
```
Creates or updates `typer.echo(json.dumps(report.to_dict(), indent`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 55
```python
    if not report.passed:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 56
```python
        raise typer.Exit(code=1)
```
Stops execution because an invariant or supported-condition check failed.

### Line 57
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 58
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 59
```python
@app.command()
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 60
```python
def run(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 61
```python
    config: Path = Path("configs/fast.yaml"),
```
Creates or updates `config: Path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 62
```python
    run_id: str = "reference_gru",
```
Creates or updates `run_id: str`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 63
```python
) -> None:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 64
```python
    summary = run_pipeline(load_config(config), run_id)
```
Creates or updates `summary`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 65
```python
    typer.echo(json.dumps(summary, indent=2))
```
Creates or updates `typer.echo(json.dumps(summary, indent`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 66
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 67
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 68
```python
@app.command("run-canonical")
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 69
```python
def run_canonical(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 70
```python
    input_path: Path,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 71
```python
    config: Path = Path("configs/fast.yaml"),
```
Creates or updates `config: Path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 72
```python
    run_id: str = "historical_world_model",
```
Creates or updates `run_id: str`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 73
```python
) -> None:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 74
```python
    """Run the full pipeline from a validated canonical FastF1/OpenF1 CSV."""
```
Begins or ends documentation describing the module, class or function contract.

### Line 75
```python
    cfg = load_config(config)
```
Creates or updates `cfg`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 76
```python
    if not input_path.exists():
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 77
```python
        raise typer.BadParameter(f"Canonical input does not exist: {input_path}")
```
Stops execution because an invariant or supported-condition check failed.

### Line 78
```python
    cfg.data.canonical_input_path = input_path
```
Creates or updates `cfg.data.canonical_input_path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 79
```python
    summary = run_pipeline(cfg, run_id)
```
Creates or updates `summary`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 80
```python
    typer.echo(json.dumps(summary, indent=2))
```
Creates or updates `typer.echo(json.dumps(summary, indent`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 81
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 82
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 83
```python
@app.command()
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 84
```python
def ui(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 85
```python
    run_dir: Path = Path("artifacts/runs/reference_gru"),
```
Creates or updates `run_dir: Path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 86
```python
    config: Path = Path("configs/fast.yaml"),
```
Creates or updates `config: Path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 87
```python
    share: bool = False,
```
Creates or updates `share: bool`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 88
```python
) -> None:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 89
```python
    from apexsim.ui import launch
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 90
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 91
```python
    launch(run_dir, config, share=share)
```
Creates or updates `launch(run_dir, config, share`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 92
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 93
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 94
```python
@app.command()
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 95
```python
def api(
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 96
```python
    artifacts_dir: Path = Path("artifacts/runs"),
```
Creates or updates `artifacts_dir: Path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 97
```python
    host: str = "127.0.0.1",
```
Creates or updates `host: str`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 98
```python
    port: int = 8000,
```
Creates or updates `port: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 99
```python
) -> None:
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 100
```python
    import uvicorn
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 101
```python
    from apexsim.serving import create_api
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 102
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 103
```python
    uvicorn.run(create_api(artifacts_dir), host=host, port=port)
```
Creates or updates `uvicorn.run(create_api(artifacts_dir), host`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 104
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 105
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 106
```python
if __name__ == "__main__":
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 107
```python
    app()
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.
