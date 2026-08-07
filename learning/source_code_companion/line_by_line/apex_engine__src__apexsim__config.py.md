# `apex_engine/src/apexsim/config.py`

**Role:** Loads and validates experiment choices before expensive work begins.

Typed configuration turns hidden constants into reproducible evidence and stops incompatible history, horizon or feature choices at the boundary.

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
from pathlib import Path
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 4
```python
from typing import Literal
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 5
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 6
```python
import yaml
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 7
```python
from pydantic import BaseModel, Field, model_validator
```
Imports a dependency required by the definitions below; keeping imports explicit reveals architectural coupling.

### Line 8
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 9
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 10
```python
class DataConfig(BaseModel):
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 11
```python
    source: Literal["synthetic", "fastf1", "openf1"] = "synthetic"
```
Creates or updates `source: Literal["synthetic", "fastf1", "openf1"]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 12
```python
    raw_dir: Path = Path("data/raw")
```
Creates or updates `raw_dir: Path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 13
```python
    processed_dir: Path = Path("data/processed")
```
Creates or updates `processed_dir: Path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 14
```python
    canonical_input_path: Path | None = None
```
Creates or updates `canonical_input_path: Path | None`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 15
```python
    sample_hz: int = Field(5, ge=1, le=50)
```
Creates or updates `sample_hz: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 16
```python
    sessions: int = Field(8, ge=3)
```
Creates or updates `sessions: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 17
```python
    laps_per_session: int = Field(3, ge=1)
```
Creates or updates `laps_per_session: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 18
```python
    track_length_m: float = Field(5200.0, gt=500)
```
Creates or updates `track_length_m: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 19
```python
    session_seconds: int = Field(210, ge=30)
```
Creates or updates `session_seconds: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 20
```python
    train_fraction: float = 0.625
```
Creates or updates `train_fraction: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 21
```python
    val_fraction: float = 0.125
```
Creates or updates `val_fraction: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 22
```python
    test_fraction: float = 0.25
```
Creates or updates `test_fraction: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 23
```python
    sequence_length: int = Field(32, ge=4)
```
Creates or updates `sequence_length: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 24
```python
    prediction_horizon: int = Field(8, ge=1)
```
Creates or updates `prediction_horizon: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 25
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 26
```python
    @model_validator(mode="after")
```
Applies a decorator that changes registration, validation or runtime behaviour of the definition that follows.

### Line 27
```python
    def fractions_sum_to_one(self) -> "DataConfig":
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 28
```python
        total = self.train_fraction + self.val_fraction + self.test_fraction
```
Creates or updates `total`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 29
```python
        if abs(total - 1.0) > 1e-6:
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 30
```python
            raise ValueError("train/val/test fractions must sum to 1.0")
```
Stops execution because an invariant or supported-condition check failed.

### Line 31
```python
        return self
```
Returns the result to the caller; this is the function output boundary that tests should assert.

### Line 32
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 33
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 34
```python
class ModelConfig(BaseModel):
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 35
```python
    kind: Literal["gru", "rssm", "ssm", "linear"] = "gru"
```
Creates or updates `kind: Literal["gru", "rssm", "ssm", "linear"]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 36
```python
    hidden_dim: int = Field(64, ge=8)
```
Creates or updates `hidden_dim: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 37
```python
    latent_dim: int = Field(16, ge=2)
```
Creates or updates `latent_dim: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 38
```python
    layers: int = Field(1, ge=1, le=8)
```
Creates or updates `layers: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 39
```python
    dropout: float = Field(0.0, ge=0.0, lt=1.0)
```
Creates or updates `dropout: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 40
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 41
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 42
```python
class TrainingConfig(BaseModel):
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 43
```python
    epochs: int = Field(4, ge=1)
```
Creates or updates `epochs: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 44
```python
    batch_size: int = Field(64, ge=1)
```
Creates or updates `batch_size: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 45
```python
    learning_rate: float = Field(1e-3, gt=0)
```
Creates or updates `learning_rate: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 46
```python
    weight_decay: float = Field(1e-4, ge=0)
```
Creates or updates `weight_decay: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 47
```python
    grad_clip: float = Field(1.0, gt=0)
```
Bounds a value to a supported range. Monitor how often clipping occurs because it may hide distribution shift.

### Line 48
```python
    patience: int = Field(3, ge=1)
```
Creates or updates `patience: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 49
```python
    device: Literal["cpu", "cuda", "mps"] = "cpu"
```
Creates or updates `device: Literal["cpu", "cuda", "mps"]`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 50
```python
    max_train_windows: int | None = Field(3500, ge=32)
```
Creates or updates `max_train_windows: int | None`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 51
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 52
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 53
```python
class SimulationConfig(BaseModel):
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 54
```python
    rollout_steps: int = Field(80, ge=1)
```
Creates or updates `rollout_steps: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 55
```python
    throttle_scale: float = Field(1.0, ge=0.0, le=2.0)
```
Creates or updates `throttle_scale: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 56
```python
    brake_scale: float = Field(1.0, ge=0.0, le=2.0)
```
Creates or updates `brake_scale: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 57
```python
    grip_multiplier: float = Field(1.0, ge=0.3, le=1.5)
```
Creates or updates `grip_multiplier: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 58
```python
    rain_delta: float = Field(0.0, ge=-1.0, le=1.0)
```
Creates or updates `rain_delta: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 59
```python
    tyre_degradation_multiplier: float = Field(1.0, ge=0.1, le=3.0)
```
Creates or updates `tyre_degradation_multiplier: float`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 60
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 61
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 62
```python
class ProjectConfig(BaseModel):
```
Defines a type that owns related state and behaviour behind a named interface.

### Line 63
```python
    project_name: str = "Project APEX"
```
Creates or updates `project_name: str`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 64
```python
    seed: int = 42
```
Creates or updates `seed: int`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 65
```python
    artifacts_dir: Path = Path("artifacts/runs")
```
Creates or updates `artifacts_dir: Path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 66
```python
    data: DataConfig = DataConfig()
```
Creates or updates `data: DataConfig`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 67
```python
    model: ModelConfig = ModelConfig()
```
Creates or updates `model: ModelConfig`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 68
```python
    training: TrainingConfig = TrainingConfig()
```
Creates or updates `training: TrainingConfig`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 69
```python
    simulation: SimulationConfig = SimulationConfig()
```
Creates or updates `simulation: SimulationConfig`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 70
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 71
```python

```
Separates logical blocks so the surrounding control flow remains readable.

### Line 72
```python
def load_config(path: str | Path) -> ProjectConfig:
```
Defines a callable boundary. Its parameters form the input contract and its return value or side effects form the output contract.

### Line 73
```python
    config_path = Path(path)
```
Creates or updates `config_path`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 74
```python
    if not config_path.exists():
```
Branches only when this condition is true; verify both the true and false paths in tests.

### Line 75
```python
        raise FileNotFoundError(f"Configuration file does not exist: {config_path}")
```
Stops execution because an invariant or supported-condition check failed.

### Line 76
```python
    with config_path.open("r", encoding="utf-8") as handle:
```
Opens a managed resource or context and guarantees cleanup when the block exits.

### Line 77
```python
        payload = yaml.safe_load(handle) or {}
```
Creates or updates `payload`. Check its unit, shape, lifetime and whether it is derived only from information available at this point.

### Line 78
```python
    return ProjectConfig.model_validate(payload)
```
Returns the result to the caller; this is the function output boundary that tests should assert.
