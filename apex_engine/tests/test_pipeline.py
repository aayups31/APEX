from pathlib import Path

from apexsim.config import load_config
from apexsim.pipeline.runner import run_pipeline


def test_end_to_end_pipeline(tmp_path: Path):
    config = load_config("configs/fast.yaml")
    config.artifacts_dir = tmp_path / "runs"
    config.data.sessions = 5
    config.data.session_seconds = 45
    config.data.sequence_length = 12
    config.data.prediction_horizon = 3
    config.training.epochs = 1
    config.training.max_train_windows = 100
    config.training.batch_size = 32
    summary = run_pipeline(config, "test_run")
    assert summary["status"] == "succeeded"
    assert (tmp_path / "runs" / "test_run" / "summary.json").exists()


def test_pipeline_accepts_canonical_adapter_output(tmp_path: Path):
    config = load_config("configs/fast.yaml")
    config.artifacts_dir = tmp_path / "runs"
    config.data.sessions = 5
    config.data.session_seconds = 45
    config.data.sequence_length = 12
    config.data.prediction_horizon = 3
    config.training.epochs = 1
    config.training.max_train_windows = 100
    config.training.batch_size = 32

    # First materialize the canonical contract exactly as a source adapter would.
    from apexsim.data.synthetic import generate_synthetic_sessions

    canonical = tmp_path / "adapter_output.csv"
    generate_synthetic_sessions(config, canonical)
    config.data.canonical_input_path = canonical
    config.data.source = "fastf1"

    summary = run_pipeline(config, "canonical_run")
    copied = tmp_path / "runs" / "canonical_run" / "canonical_telemetry.csv"
    assert summary["status"] == "succeeded"
    assert copied.exists()
    assert copied.read_bytes() == canonical.read_bytes()
