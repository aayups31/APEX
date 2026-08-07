from __future__ import annotations

import json
import shutil
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from apexsim.config import ProjectConfig
from apexsim.contracts import MODEL_INPUT_COLUMNS, STATE_COLUMNS, TARGET_COLUMNS
from apexsim.data.features import Standardizer
from apexsim.data.synthetic import generate_synthetic_sessions
from apexsim.data.validate import validate_canonical_frame
from apexsim.data.windows import TelemetryWindowDataset, split_sessions
from apexsim.evaluation import evaluate_world_model
from apexsim.models.factory import build_model
from apexsim.training import train_world_model


def ingest_stage(config: ProjectConfig, run_dir: Path) -> Path:
    """Materialize one canonical telemetry file inside the immutable run directory.

    Synthetic runs generate the file directly. Real-data runs first use a source
    adapter (FastF1 or OpenF1) to create the canonical contract, then provide that
    file through ``canonical_input_path``. Copying it into the run directory makes
    the exact training input part of run lineage and keeps downstream stages
    source-independent.
    """
    output = run_dir / "canonical_telemetry.csv"
    if output.exists():
        return output

    if config.data.canonical_input_path is not None:
        source = Path(config.data.canonical_input_path)
        if not source.exists():
            raise FileNotFoundError(f"Canonical input does not exist: {source}")
        if source.resolve() != output.resolve():
            shutil.copy2(source, output)
        return output

    if config.data.source == "synthetic":
        generate_synthetic_sessions(config, output)
        return output

    raise ValueError(
        "FastF1/OpenF1 sources require a canonical input file. Run the matching "
        "ingestion command, then use `apexsim run-canonical --input-path ...`."
    )


def quality_stage(canonical_path: Path, run_dir: Path) -> dict:
    output = run_dir / "quality_report.json"
    if output.exists():
        return json.loads(output.read_text(encoding="utf-8"))
    frame = pd.read_csv(canonical_path)
    report = validate_canonical_frame(frame, strict=True).to_dict()
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def dataset_stage(config: ProjectConfig, canonical_path: Path, run_dir: Path) -> dict:
    split_path = run_dir / "splits.json"
    scaler_path = run_dir / "standardizer.json"
    if split_path.exists() and scaler_path.exists():
        return {
            "splits": json.loads(split_path.read_text(encoding="utf-8")),
            "standardizer": json.loads(scaler_path.read_text(encoding="utf-8")),
        }
    frame = pd.read_csv(canonical_path)
    splits = split_sessions(
        frame,
        config.data.train_fraction,
        config.data.val_fraction,
        config.seed,
    )
    train_frame = frame[frame.session_id.isin(splits["train"])]
    standardizer = Standardizer.fit(train_frame)
    split_path.write_text(json.dumps(splits, indent=2), encoding="utf-8")
    scaler_path.write_text(json.dumps(standardizer.to_dict(), indent=2), encoding="utf-8")
    return {"splits": splits, "standardizer": standardizer.to_dict()}


def _load_datasets(config: ProjectConfig, canonical_path: Path, run_dir: Path):
    frame = pd.read_csv(canonical_path)
    splits = json.loads((run_dir / "splits.json").read_text(encoding="utf-8"))
    standardizer = Standardizer.from_dict(
        json.loads((run_dir / "standardizer.json").read_text(encoding="utf-8"))
    )
    datasets = {
        name: TelemetryWindowDataset(
            frame,
            session_ids,
            config.data.sequence_length,
            config.data.prediction_horizon,
            standardizer,
            max_windows=config.training.max_train_windows if name == "train" else 1200,
        )
        for name, session_ids in splits.items()
    }
    return frame, standardizer, datasets


def train_stage(config: ProjectConfig, canonical_path: Path, run_dir: Path) -> dict:
    model_dir = run_dir / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = model_dir / "world_model.pt"
    meta_path = model_dir / "model_meta.json"
    if checkpoint.exists() and meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    _, standardizer, datasets = _load_datasets(config, canonical_path, run_dir)
    if len(datasets["train"]) == 0 or len(datasets["val"]) == 0:
        raise RuntimeError("Not enough windows after session split; increase session duration or count.")
    train_loader = DataLoader(datasets["train"], batch_size=config.training.batch_size, shuffle=True)
    val_loader = DataLoader(datasets["val"], batch_size=config.training.batch_size, shuffle=False)
    model = build_model(config.model, len(MODEL_INPUT_COLUMNS), len(TARGET_COLUMNS))
    result = train_world_model(model, train_loader, val_loader, config, model_dir)
    meta = {
        "kind": config.model.kind,
        "input_dim": len(MODEL_INPUT_COLUMNS),
        "state_dim": len(TARGET_COLUMNS),
        "hidden_dim": config.model.hidden_dim,
        "latent_dim": config.model.latent_dim,
        "layers": config.model.layers,
        "dropout": config.model.dropout,
        "best_val_loss": result.best_val_loss,
        "epochs_completed": result.epochs_completed,
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def load_trained_model(config: ProjectConfig, run_dir: Path):
    meta = json.loads((run_dir / "model" / "model_meta.json").read_text(encoding="utf-8"))
    config.model.kind = meta["kind"]
    config.model.hidden_dim = meta["hidden_dim"]
    config.model.latent_dim = meta["latent_dim"]
    config.model.layers = meta["layers"]
    config.model.dropout = meta["dropout"]
    model = build_model(config.model, meta["input_dim"], meta["state_dim"])
    state = torch.load(run_dir / "model" / "world_model.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    return model


def evaluate_stage(config: ProjectConfig, canonical_path: Path, run_dir: Path) -> dict:
    output = run_dir / "metrics.json"
    if output.exists():
        return json.loads(output.read_text(encoding="utf-8"))
    _, standardizer, datasets = _load_datasets(config, canonical_path, run_dir)
    test_loader = DataLoader(datasets["test"], batch_size=config.training.batch_size, shuffle=False)
    model = load_trained_model(config, run_dir)
    return evaluate_world_model(model, test_loader, standardizer, output, config.training.device)


def ablation_stage(config: ProjectConfig, canonical_path: Path, run_dir: Path) -> list[dict]:
    output = run_dir / "ablations.json"
    if output.exists():
        return json.loads(output.read_text(encoding="utf-8"))
    frame = pd.read_csv(canonical_path)
    splits = json.loads((run_dir / "splits.json").read_text(encoding="utf-8"))
    train = frame[frame.session_id.isin(splits["train"])].copy()
    test = frame[frame.session_id.isin(splits["test"])].copy()
    feature_sets = {
        "state_only": STATE_COLUMNS,
        "state_plus_actions": STATE_COLUMNS + ["throttle", "brake", "gear_norm", "drs"],
        "full_context": MODEL_INPUT_COLUMNS,
        "no_weather": [c for c in MODEL_INPUT_COLUMNS if c not in {"rainfall", "air_temp_c", "track_temp_c", "wind_speed_mps"}],
        "no_track_geometry": [c for c in MODEL_INPUT_COLUMNS if c not in {"curvature", "steering_proxy", "track_progress_sin", "track_progress_cos"}],
    }
    results = []
    for name, features in feature_sets.items():
        # One-step ridge is intentionally used as a cheap, interpretable ablation probe.
        x_train = train[features].iloc[:-1].to_numpy(np.float32)
        y_train = train[TARGET_COLUMNS].iloc[1:].to_numpy(np.float32)
        same_session = train.session_id.iloc[:-1].to_numpy() == train.session_id.iloc[1:].to_numpy()
        x_train, y_train = x_train[same_session], y_train[same_session]
        x_test = test[features].iloc[:-1].to_numpy(np.float32)
        y_test = test[TARGET_COLUMNS].iloc[1:].to_numpy(np.float32)
        same_test = test.session_id.iloc[:-1].to_numpy() == test.session_id.iloc[1:].to_numpy()
        x_test, y_test = x_test[same_test], y_test[same_test]
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import make_pipeline
        from sklearn.multioutput import MultiOutputRegressor

        model = make_pipeline(StandardScaler(), MultiOutputRegressor(Ridge(alpha=1.0)))
        model.fit(x_train, y_train)
        prediction = model.predict(x_test)
        results.append(
            {
                "ablation": name,
                "features": features,
                "speed_mae_mps": float(np.mean(np.abs(prediction[:, 0] - y_test[:, 0]))),
                "overall_mae": float(np.mean(np.abs(prediction - y_test))),
            }
        )
    results.sort(key=lambda item: item["speed_mae_mps"])
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def publish_stage(config: ProjectConfig, canonical_path: Path, run_dir: Path) -> dict:
    output = run_dir / "publication.json"
    if output.exists():
        return json.loads(output.read_text(encoding="utf-8"))
    frame, standardizer, datasets = _load_datasets(config, canonical_path, run_dir)
    model = load_trained_model(config, run_dir)
    sample = datasets["test"][0]
    history = sample["history"].unsqueeze(0)
    future_inputs = sample["future_inputs"].unsqueeze(0)
    with torch.no_grad():
        if config.model.kind == "rssm":
            prediction, _ = model(history, future_inputs, future_targets=None)
        else:
            prediction = model(history, future_inputs)
    predicted = standardizer.inverse_targets(prediction.numpy()[0])
    truth = standardizer.inverse_targets(sample["future_targets"].numpy())
    comparison = pd.DataFrame(
        {
            "step": np.arange(len(predicted)),
            "predicted_speed_mps": predicted[:, 0],
            "actual_speed_mps": truth[:, 0],
            "predicted_accel_mps2": predicted[:, 1],
            "actual_accel_mps2": truth[:, 1],
        }
    )
    comparison_path = run_dir / "rollout_preview.csv"
    comparison.to_csv(comparison_path, index=False)
    payload = {
        "run_dir": str(run_dir),
        "model_kind": config.model.kind,
        "rollout_preview": str(comparison_path),
        "test_sessions": json.loads((run_dir / "splits.json").read_text())["test"],
        "ui_command": f"apexsim ui --run-dir {run_dir}",
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
