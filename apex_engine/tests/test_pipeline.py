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
    source_manifest_path = tmp_path / "adapter_output.csv.source.json"
    source_manifest = SourceManifest(
        source="fastf1",
        query={"fixture": "pipeline"},
        terms_url="https://docs.fastf1.dev/",
        notes=["Synthetic bytes used only to test the public-data lineage boundary."],
    )
    source_manifest.add_request("fixture://fastf1", {"fixture": "pipeline"}, None)
    source_manifest.add_file(canonical, role="derived_canonical")
    source_manifest.save(source_manifest_path)
    config.data.canonical_input_path = canonical
    config.data.source_manifest_path = source_manifest_path
    config.data.source = "fastf1"

    summary = run_pipeline(config, "canonical_run")
    copied = tmp_path / "runs" / "canonical_run" / "canonical_telemetry.csv"
    assert summary["status"] == "succeeded"
    assert copied.exists()
    assert copied.read_bytes() == canonical.read_bytes()
    assert (tmp_path / "runs" / "canonical_run" / "source_manifest.json").exists()


def test_pipeline_rejects_unprovenanced_public_input(tmp_path: Path):
    canonical = tmp_path / "unprovenanced.csv"
    canonical.write_text("not,used\n", encoding="utf-8")
    config = load_config("configs/fast.yaml")
    config.data.source = "openf1"
    config.data.canonical_input_path = canonical

    with pytest.raises(ValueError, match="source_manifest_path"):
        ingest_stage(config, tmp_path / "run")
