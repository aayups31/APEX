from pathlib import Path

import pytest

from apexsim.config import load_config
from apexsim.data.manifest import SourceManifest
from apexsim.pipeline.runner import run_pipeline
from apexsim.pipeline.stages import ingest_stage


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


def test_pipeline_accepts_synthetic_canonical_input(tmp_path: Path):
    config = load_config("configs/fast.yaml")
    config.artifacts_dir = tmp_path / "runs"
    config.data.sessions = 5
    config.data.session_seconds = 45
    config.data.sequence_length = 12
    config.data.prediction_horizon = 3
    config.training.epochs = 1
    config.training.max_train_windows = 100
    config.training.batch_size = 32

    from apexsim.data.synthetic import generate_synthetic_sessions

    canonical = tmp_path / "adapter_output.csv"
    generate_synthetic_sessions(config, canonical)
    config.data.canonical_input_path = canonical

    summary = run_pipeline(config, "canonical_run")
    copied = tmp_path / "runs" / "canonical_run" / "canonical_telemetry.csv"
    assert summary["status"] == "succeeded"
    assert copied.exists()
    assert copied.read_bytes() == canonical.read_bytes()


def test_pipeline_rejects_unprovenanced_public_input(tmp_path: Path):
    canonical = tmp_path / "unprovenanced.csv"
    canonical.write_text("not,used\n", encoding="utf-8")
    config = load_config("configs/fast.yaml")
    config.data.source = "openf1"
    config.data.canonical_input_path = canonical

    with pytest.raises(ValueError, match="source_manifest_path"):
        ingest_stage(config, tmp_path / "run")


def test_public_dense_input_is_rejected_even_with_valid_legacy_manifest(tmp_path: Path):
    canonical = tmp_path / "legacy.csv"
    canonical.write_text("source,speed_mps\nfastf1,50\n", encoding="utf-8")
    manifest = SourceManifest("fastf1", {"fixture": True}, "https://docs.fastf1.dev/")
    manifest.add_file(canonical, role="derived_canonical")
    manifest_path = tmp_path / "source.json"
    manifest.save(manifest_path)
    config = load_config("configs/fast.yaml")
    config.data.source = "fastf1"
    config.data.canonical_input_path = canonical
    config.data.source_manifest_path = manifest_path
    original = canonical.read_bytes()
    with pytest.raises(ValueError, match="validated feature builder"):
        ingest_stage(config, tmp_path / "run")
    assert canonical.read_bytes() == original
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize("sources", ["fastf1", "synthetic\nopenf1", '""'])
@pytest.mark.parametrize("cached", [False, True])
def test_default_synthetic_config_cannot_admit_public_or_unknown_rows(tmp_path: Path, sources: str, cached: bool):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    canonical = run_dir / "canonical_telemetry.csv" if cached else tmp_path / "input.csv"
    canonical.write_text("source\n" + sources + "\n", encoding="utf-8")
    config = load_config("configs/fast.yaml")
    config.data.canonical_input_path = canonical
    with pytest.raises(ValueError, match="validated feature builder"):
        ingest_stage(config, run_dir)
    if not cached:
        assert not (run_dir / "canonical_telemetry.csv").exists()
