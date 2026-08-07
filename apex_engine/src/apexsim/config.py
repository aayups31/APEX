from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class DataConfig(BaseModel):
    source: Literal["synthetic", "fastf1", "openf1"] = "synthetic"
    raw_dir: Path = Path("data/raw")
    processed_dir: Path = Path("data/processed")
    canonical_input_path: Path | None = None
    sample_hz: int = Field(5, ge=1, le=50)
    sessions: int = Field(8, ge=3)
    laps_per_session: int = Field(3, ge=1)
    track_length_m: float = Field(5200.0, gt=500)
    session_seconds: int = Field(210, ge=30)
    train_fraction: float = 0.625
    val_fraction: float = 0.125
    test_fraction: float = 0.25
    sequence_length: int = Field(32, ge=4)
    prediction_horizon: int = Field(8, ge=1)

    @model_validator(mode="after")
    def fractions_sum_to_one(self) -> "DataConfig":
        total = self.train_fraction + self.val_fraction + self.test_fraction
        if abs(total - 1.0) > 1e-6:
            raise ValueError("train/val/test fractions must sum to 1.0")
        return self


class ModelConfig(BaseModel):
    kind: Literal["gru", "rssm", "ssm", "linear"] = "gru"
    hidden_dim: int = Field(64, ge=8)
    latent_dim: int = Field(16, ge=2)
    layers: int = Field(1, ge=1, le=8)
    dropout: float = Field(0.0, ge=0.0, lt=1.0)


class TrainingConfig(BaseModel):
    epochs: int = Field(4, ge=1)
    batch_size: int = Field(64, ge=1)
    learning_rate: float = Field(1e-3, gt=0)
    weight_decay: float = Field(1e-4, ge=0)
    grad_clip: float = Field(1.0, gt=0)
    patience: int = Field(3, ge=1)
    device: Literal["cpu", "cuda", "mps"] = "cpu"
    max_train_windows: int | None = Field(3500, ge=32)


class SimulationConfig(BaseModel):
    rollout_steps: int = Field(80, ge=1)
    throttle_scale: float = Field(1.0, ge=0.0, le=2.0)
    brake_scale: float = Field(1.0, ge=0.0, le=2.0)
    grip_multiplier: float = Field(1.0, ge=0.3, le=1.5)
    rain_delta: float = Field(0.0, ge=-1.0, le=1.0)
    tyre_degradation_multiplier: float = Field(1.0, ge=0.1, le=3.0)


class ProjectConfig(BaseModel):
    project_name: str = "Project APEX"
    seed: int = 42
    artifacts_dir: Path = Path("artifacts/runs")
    data: DataConfig = DataConfig()
    model: ModelConfig = ModelConfig()
    training: TrainingConfig = TrainingConfig()
    simulation: SimulationConfig = SimulationConfig()


def load_config(path: str | Path) -> ProjectConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file does not exist: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return ProjectConfig.model_validate(payload)
