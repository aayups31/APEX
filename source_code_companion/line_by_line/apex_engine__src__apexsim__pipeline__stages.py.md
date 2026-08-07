# `apex_engine/src/apexsim/pipeline/stages.py`

**Role:** Defines reusable idempotent pipeline operations.

Each stage consumes paths/contracts and writes immutable evidence that can be retried independently.

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
import shutil
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
import joblib
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 8
```python
import numpy as np
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 9
```python
import pandas as pd
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 10
```python
import torch
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
from apexsim.contracts import MODEL_INPUT_COLUMNS, STATE_COLUMNS, TARGET_COLUMNS
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 15
```python
from apexsim.data.features import Standardizer
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 16
```python
from apexsim.data.synthetic import generate_synthetic_sessions
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 17
```python
from apexsim.data.validate import validate_canonical_frame
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 18
```python
from apexsim.data.windows import TelemetryWindowDataset, split_sessions
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 19
```python
from apexsim.evaluation import evaluate_world_model
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 20
```python
from apexsim.models.factory import build_model
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 21
```python
from apexsim.training import train_world_model
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 22
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 23
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 24
```python
def ingest_stage(config: ProjectConfig, run_dir: Path) -> Path:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 25
```python
    """Materialize one canonical telemetry file inside the immutable run directory.
```
Begins or ends documentation describing the module, class or function contract.

### Line 26
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 27
```python
    Synthetic runs generate the file directly. Real-data runs first use a source
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 28
```python
    adapter (FastF1 or OpenF1) to create the canonical contract, then provide that
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 29
```python
    file through ``canonical_input_path``. Copying it into the run directory makes
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 30
```python
    the exact training input part of run lineage and keeps downstream stages
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 31
```python
    source-independent.
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 32
```python
    """
```
Begins or ends documentation describing the module, class or function contract.

### Line 33
```python
    output = run_dir / "canonical_telemetry.csv"
```
Creates or updates `output`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 34
```python
    if output.exists():
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 35
```python
        return output
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 36
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 37
```python
    if config.data.canonical_input_path is not None:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 38
```python
        source = Path(config.data.canonical_input_path)
```
Creates or updates `source`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 39
```python
        if not source.exists():
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 40
```python
            raise FileNotFoundError(f"Canonical input does not exist: {source}")
```
Stops execution because an invariant or supported-condition check failed.

### Line 41
```python
        if source.resolve() != output.resolve():
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 42
```python
            shutil.copy2(source, output)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 43
```python
        return output
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 44
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 45
```python
    if config.data.source == "synthetic":
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 46
```python
        generate_synthetic_sessions(config, output)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 47
```python
        return output
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 48
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 49
```python
    raise ValueError(
```
Stops execution because an invariant or supported-condition check failed.

### Line 50
```python
        "FastF1/OpenF1 sources require a canonical input file. Run the matching "
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 51
```python
        "ingestion command, then use `apexsim run-canonical --input-path ...`."
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 52
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 53
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 54
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 55
```python
def quality_stage(canonical_path: Path, run_dir: Path) -> dict:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 56
```python
    output = run_dir / "quality_report.json"
```
Creates or updates `output`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 57
```python
    if output.exists():
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 58
```python
        return json.loads(output.read_text(encoding="utf-8"))
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 59
```python
    frame = pd.read_csv(canonical_path)
```
Loads persisted tabular evidence; validate schema, units and ordering immediately afterward.

### Line 60
```python
    report = validate_canonical_frame(frame, strict=True).to_dict()
```
Creates or updates `report`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 61
```python
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
```
Persists an artifact. The surrounding code should include run identity, schema and preprocessing lineage.

### Line 62
```python
    return report
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 63
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 64
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 65
```python
def dataset_stage(config: ProjectConfig, canonical_path: Path, run_dir: Path) -> dict:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 66
```python
    split_path = run_dir / "splits.json"
```
Creates or updates `split_path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 67
```python
    scaler_path = run_dir / "standardizer.json"
```
Creates or updates `scaler_path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 68
```python
    if split_path.exists() and scaler_path.exists():
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 69
```python
        return {
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 70
```python
            "splits": json.loads(split_path.read_text(encoding="utf-8")),
```
Creates or updates `"splits": json.loads(split_path.read_text(encoding`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 71
```python
            "standardizer": json.loads(scaler_path.read_text(encoding="utf-8")),
```
Creates or updates `"standardizer": json.loads(scaler_path.read_text(encoding`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 72
```python
        }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 73
```python
    frame = pd.read_csv(canonical_path)
```
Loads persisted tabular evidence; validate schema, units and ordering immediately afterward.

### Line 74
```python
    splits = split_sessions(
```
Creates or updates `splits`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 75
```python
        frame,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 76
```python
        config.data.train_fraction,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 77
```python
        config.data.val_fraction,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 78
```python
        config.seed,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 79
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 80
```python
    train_frame = frame[frame.session_id.isin(splits["train"])]
```
Creates or updates `train_frame`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 81
```python
    standardizer = Standardizer.fit(train_frame)
```
Learns parameters or preprocessing statistics from the supplied training evidence only.

### Line 82
```python
    split_path.write_text(json.dumps(splits, indent=2), encoding="utf-8")
```
Persists an artifact. The surrounding code should include run identity, schema and preprocessing lineage.

### Line 83
```python
    scaler_path.write_text(json.dumps(standardizer.to_dict(), indent=2), encoding="utf-8")
```
Persists an artifact. The surrounding code should include run identity, schema and preprocessing lineage.

### Line 84
```python
    return {"splits": splits, "standardizer": standardizer.to_dict()}
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 85
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 86
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 87
```python
def _load_datasets(config: ProjectConfig, canonical_path: Path, run_dir: Path):
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 88
```python
    frame = pd.read_csv(canonical_path)
```
Loads persisted tabular evidence; validate schema, units and ordering immediately afterward.

### Line 89
```python
    splits = json.loads((run_dir / "splits.json").read_text(encoding="utf-8"))
```
Creates or updates `splits`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 90
```python
    standardizer = Standardizer.from_dict(
```
Creates or updates `standardizer`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 91
```python
        json.loads((run_dir / "standardizer.json").read_text(encoding="utf-8"))
```
Creates or updates `json.loads((run_dir / "standardizer.json").read_text(encoding`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 92
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 93
```python
    datasets = {
```
Creates or updates `datasets`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 94
```python
        name: TelemetryWindowDataset(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 95
```python
            frame,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 96
```python
            session_ids,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 97
```python
            config.data.sequence_length,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 98
```python
            config.data.prediction_horizon,
```
Runs model inference using learned parameters without fitting on the requested examples.

### Line 99
```python
            standardizer,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 100
```python
            max_windows=config.training.max_train_windows if name == "train" else 1200,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 101
```python
        )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 102
```python
        for name, session_ids in splits.items()
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 103
```python
    }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 104
```python
    return frame, standardizer, datasets
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 105
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 106
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 107
```python
def train_stage(config: ProjectConfig, canonical_path: Path, run_dir: Path) -> dict:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 108
```python
    model_dir = run_dir / "model"
```
Creates or updates `model_dir`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 109
```python
    model_dir.mkdir(parents=True, exist_ok=True)
```
Creates or updates `model_dir.mkdir(parents`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 110
```python
    checkpoint = model_dir / "world_model.pt"
```
Creates or updates `checkpoint`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 111
```python
    meta_path = model_dir / "model_meta.json"
```
Creates or updates `meta_path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 112
```python
    if checkpoint.exists() and meta_path.exists():
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 113
```python
        return json.loads(meta_path.read_text(encoding="utf-8"))
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 114
```python
    _, standardizer, datasets = _load_datasets(config, canonical_path, run_dir)
```
Creates or updates `_, standardizer, datasets`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 115
```python
    if len(datasets["train"]) == 0 or len(datasets["val"]) == 0:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 116
```python
        raise RuntimeError("Not enough windows after session split; increase session duration or count.")
```
Stops execution because an invariant or supported-condition check failed.

### Line 117
```python
    train_loader = DataLoader(datasets["train"], batch_size=config.training.batch_size, shuffle=True)
```
Creates or updates `train_loader`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 118
```python
    val_loader = DataLoader(datasets["val"], batch_size=config.training.batch_size, shuffle=False)
```
Creates or updates `val_loader`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 119
```python
    model = build_model(config.model, len(MODEL_INPUT_COLUMNS), len(TARGET_COLUMNS))
```
Creates or updates `model`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 120
```python
    result = train_world_model(model, train_loader, val_loader, config, model_dir)
```
Creates or updates `result`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 121
```python
    meta = {
```
Creates or updates `meta`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 122
```python
        "kind": config.model.kind,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 123
```python
        "input_dim": len(MODEL_INPUT_COLUMNS),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 124
```python
        "state_dim": len(TARGET_COLUMNS),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 125
```python
        "hidden_dim": config.model.hidden_dim,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 126
```python
        "latent_dim": config.model.latent_dim,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 127
```python
        "layers": config.model.layers,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 128
```python
        "dropout": config.model.dropout,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 129
```python
        "best_val_loss": result.best_val_loss,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 130
```python
        "epochs_completed": result.epochs_completed,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 131
```python
    }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 132
```python
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
```
Persists an artifact. The surrounding code should include run identity, schema and preprocessing lineage.

### Line 133
```python
    return meta
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 134
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 135
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 136
```python
def load_trained_model(config: ProjectConfig, run_dir: Path):
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 137
```python
    meta = json.loads((run_dir / "model" / "model_meta.json").read_text(encoding="utf-8"))
```
Creates or updates `meta`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 138
```python
    config.model.kind = meta["kind"]
```
Creates or updates `config.model.kind`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 139
```python
    config.model.hidden_dim = meta["hidden_dim"]
```
Creates or updates `config.model.hidden_dim`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 140
```python
    config.model.latent_dim = meta["latent_dim"]
```
Creates or updates `config.model.latent_dim`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 141
```python
    config.model.layers = meta["layers"]
```
Creates or updates `config.model.layers`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 142
```python
    config.model.dropout = meta["dropout"]
```
Creates or updates `config.model.dropout`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 143
```python
    model = build_model(config.model, meta["input_dim"], meta["state_dim"])
```
Creates or updates `model`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 144
```python
    state = torch.load(run_dir / "model" / "world_model.pt", map_location="cpu", weights_only=True)
```
Creates or updates `state`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 145
```python
    model.load_state_dict(state)
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 146
```python
    return model
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 147
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 148
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 149
```python
def evaluate_stage(config: ProjectConfig, canonical_path: Path, run_dir: Path) -> dict:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 150
```python
    output = run_dir / "metrics.json"
```
Creates or updates `output`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 151
```python
    if output.exists():
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 152
```python
        return json.loads(output.read_text(encoding="utf-8"))
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 153
```python
    _, standardizer, datasets = _load_datasets(config, canonical_path, run_dir)
```
Creates or updates `_, standardizer, datasets`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 154
```python
    test_loader = DataLoader(datasets["test"], batch_size=config.training.batch_size, shuffle=False)
```
Creates or updates `test_loader`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 155
```python
    model = load_trained_model(config, run_dir)
```
Creates or updates `model`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 156
```python
    return evaluate_world_model(model, test_loader, standardizer, output, config.training.device)
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 157
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 158
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 159
```python
def ablation_stage(config: ProjectConfig, canonical_path: Path, run_dir: Path) -> list[dict]:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 160
```python
    output = run_dir / "ablations.json"
```
Creates or updates `output`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 161
```python
    if output.exists():
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 162
```python
        return json.loads(output.read_text(encoding="utf-8"))
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 163
```python
    frame = pd.read_csv(canonical_path)
```
Loads persisted tabular evidence; validate schema, units and ordering immediately afterward.

### Line 164
```python
    splits = json.loads((run_dir / "splits.json").read_text(encoding="utf-8"))
```
Creates or updates `splits`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 165
```python
    train = frame[frame.session_id.isin(splits["train"])].copy()
```
Creates or updates `train`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 166
```python
    test = frame[frame.session_id.isin(splits["test"])].copy()
```
Creates or updates `test`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 167
```python
    feature_sets = {
```
Creates or updates `feature_sets`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 168
```python
        "state_only": STATE_COLUMNS,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 169
```python
        "state_plus_actions": STATE_COLUMNS + ["throttle", "brake", "gear_norm", "drs"],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 170
```python
        "full_context": MODEL_INPUT_COLUMNS,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 171
```python
        "no_weather": [c for c in MODEL_INPUT_COLUMNS if c not in {"rainfall", "air_temp_c", "track_temp_c", "wind_speed_mps"}],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 172
```python
        "no_track_geometry": [c for c in MODEL_INPUT_COLUMNS if c not in {"curvature", "steering_proxy", "track_progress_sin", "track_progress_cos"}],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 173
```python
    }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 174
```python
    results = []
```
Creates or updates `results`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 175
```python
    for name, features in feature_sets.items():
```
Iterates over a collection or time dimension. Confirm order, boundaries and whether state should persist between iterations.

### Line 176
```python
        # One-step ridge is intentionally used as a cheap, interpretable ablation probe.
```
Documents an assumption, intent or constraint that should remain aligned with the implementation.

### Line 177
```python
        x_train = train[features].iloc[:-1].to_numpy(np.float32)
```
Creates or updates `x_train`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 178
```python
        y_train = train[TARGET_COLUMNS].iloc[1:].to_numpy(np.float32)
```
Creates or updates `y_train`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 179
```python
        same_session = train.session_id.iloc[:-1].to_numpy() == train.session_id.iloc[1:].to_numpy()
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 180
```python
        x_train, y_train = x_train[same_session], y_train[same_session]
```
Creates or updates `x_train, y_train`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 181
```python
        x_test = test[features].iloc[:-1].to_numpy(np.float32)
```
Creates or updates `x_test`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 182
```python
        y_test = test[TARGET_COLUMNS].iloc[1:].to_numpy(np.float32)
```
Creates or updates `y_test`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 183
```python
        same_test = test.session_id.iloc[:-1].to_numpy() == test.session_id.iloc[1:].to_numpy()
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 184
```python
        x_test, y_test = x_test[same_test], y_test[same_test]
```
Creates or updates `x_test, y_test`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 185
```python
        from sklearn.linear_model import Ridge
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 186
```python
        from sklearn.preprocessing import StandardScaler
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 187
```python
        from sklearn.pipeline import make_pipeline
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 188
```python
        from sklearn.multioutput import MultiOutputRegressor
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 189
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 190
```python
        model = make_pipeline(StandardScaler(), MultiOutputRegressor(Ridge(alpha=1.0)))
```
Creates or updates `model`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 191
```python
        model.fit(x_train, y_train)
```
Learns parameters or preprocessing statistics from the supplied training evidence only.

### Line 192
```python
        prediction = model.predict(x_test)
```
Runs model inference using learned parameters without fitting on the requested examples.

### Line 193
```python
        results.append(
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 194
```python
            {
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 195
```python
                "ablation": name,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 196
```python
                "features": features,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 197
```python
                "speed_mae_mps": float(np.mean(np.abs(prediction[:, 0] - y_test[:, 0]))),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 198
```python
                "overall_mae": float(np.mean(np.abs(prediction - y_test))),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 199
```python
            }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 200
```python
        )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 201
```python
    results.sort(key=lambda item: item["speed_mae_mps"])
```
Creates or updates `results.sort(key`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 202
```python
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
```
Persists an artifact. The surrounding code should include run identity, schema and preprocessing lineage.

### Line 203
```python
    return results
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 204
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 205
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 206
```python
def publish_stage(config: ProjectConfig, canonical_path: Path, run_dir: Path) -> dict:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 207
```python
    output = run_dir / "publication.json"
```
Creates or updates `output`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 208
```python
    if output.exists():
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 209
```python
        return json.loads(output.read_text(encoding="utf-8"))
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 210
```python
    frame, standardizer, datasets = _load_datasets(config, canonical_path, run_dir)
```
Creates or updates `frame, standardizer, datasets`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 211
```python
    model = load_trained_model(config, run_dir)
```
Creates or updates `model`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 212
```python
    sample = datasets["test"][0]
```
Creates or updates `sample`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 213
```python
    history = sample["history"].unsqueeze(0)
```
Creates or updates `history`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 214
```python
    future_inputs = sample["future_inputs"].unsqueeze(0)
```
Creates or updates `future_inputs`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 215
```python
    with torch.no_grad():
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 216
```python
        if config.model.kind == "rssm":
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 217
```python
            prediction, _ = model(history, future_inputs, future_targets=None)
```
Creates or updates `prediction, _`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 218
```python
        else:
```
Handles all remaining cases; inspect whether this fallback is intentionally broad.

### Line 219
```python
            prediction = model(history, future_inputs)
```
Creates or updates `prediction`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 220
```python
    predicted = standardizer.inverse_targets(prediction.numpy()[0])
```
Creates or updates `predicted`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 221
```python
    truth = standardizer.inverse_targets(sample["future_targets"].numpy())
```
Creates or updates `truth`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 222
```python
    comparison = pd.DataFrame(
```
Creates or updates `comparison`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 223
```python
        {
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 224
```python
            "step": np.arange(len(predicted)),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 225
```python
            "predicted_speed_mps": predicted[:, 0],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 226
```python
            "actual_speed_mps": truth[:, 0],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 227
```python
            "predicted_accel_mps2": predicted[:, 1],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 228
```python
            "actual_accel_mps2": truth[:, 1],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 229
```python
        }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 230
```python
    )
```
Calls a function or method. Trace its input contract, returned value and any persistent side effects.

### Line 231
```python
    comparison_path = run_dir / "rollout_preview.csv"
```
Creates or updates `comparison_path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 232
```python
    comparison.to_csv(comparison_path, index=False)
```
Persists an artifact. The surrounding code should include run identity, schema and preprocessing lineage.

### Line 233
```python
    payload = {
```
Creates or updates `payload`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 234
```python
        "run_dir": str(run_dir),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 235
```python
        "model_kind": config.model.kind,
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 236
```python
        "rollout_preview": str(comparison_path),
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 237
```python
        "test_sessions": json.loads((run_dir / "splits.json").read_text())["test"],
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 238
```python
        "ui_command": f"apexsim ui --run-dir {run_dir}",
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 239
```python
    }
```
Executes this statement inside the current control-flow block; connect it to the nearest function contract and testable invariant.

### Line 240
```python
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
```
Persists an artifact. The surrounding code should include run identity, schema and preprocessing lineage.

### Line 241
```python
    return payload
```
Returns the result to the caller; this is the function output boundary that tests should assert.
