import json
from pathlib import Path

import pandas as pd
import pytest

from apexsim.examples.complete_sim_demo import build_demo
from apexsim.provenance import ensure_run_directory, file_sha256


def test_race_artifacts_have_immutable_hashed_manifest(tmp_path: Path):
    output = tmp_path / "race-001"
    result = build_demo(seed=12, total_laps=1).run()
    result.save(output)

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "apex-run-manifest-v1"
    assert manifest["seed"] == 12
    assert manifest["config_sha256"]
    assert manifest["source_sha256"]
    assert manifest["source"]["working_tree_sha256"]
    assert manifest["environment_sha256"]
    artifact_hashes = {Path(item["path"]).name: item["sha256"] for item in manifest["artifacts"]}
    assert artifact_hashes["track.csv"] == file_sha256(output / "track.csv")
    assert artifact_hashes["summary.json"] == file_sha256(output / "summary.json")

    with pytest.raises(FileExistsError):
        result.save(output)


def test_fixed_seed_produces_identical_race_evidence(tmp_path: Path):
    first = build_demo(seed=123, total_laps=1).run()
    second = build_demo(seed=123, total_laps=1).run()

    pd.testing.assert_frame_equal(first.telemetry, second.telemetry, check_exact=True)
    pd.testing.assert_frame_equal(first.standings, second.standings, check_exact=True)
    pd.testing.assert_frame_equal(first.events, second.events, check_exact=True)

    first.save(tmp_path / "first")
    second.save(tmp_path / "second")
    for name in ("telemetry.csv", "standings.csv", "events.csv", "quality_report.json"):
        assert (tmp_path / "first" / name).read_bytes() == (tmp_path / "second" / name).read_bytes()


def test_run_directory_rejects_unsafe_or_reused_ids(tmp_path: Path):
    with pytest.raises(ValueError):
        ensure_run_directory(tmp_path, "../escape")
    run_dir = ensure_run_directory(tmp_path, "safe-run_01")
    (run_dir / "evidence.txt").write_text("frozen", encoding="utf-8")
    with pytest.raises(FileExistsError):
        ensure_run_directory(tmp_path, "safe-run_01")
