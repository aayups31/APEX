import copy
import json

import numpy as np
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.data import tyre_dataset
from apexsim.examples.tyre_degradation_demo import (
    EVENTS,
    evaluate_tyre_study,
    make_tyre_smoke_dataset,
    run_tyre_degradation_demo,
    verify_tyre_study,
)
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research.hierarchical_tyre import HierarchySettings


@pytest.fixture(scope="module")
def study(tmp_path_factory):
    root = tmp_path_factory.mktemp("tyre-cli")
    output = root / "run"
    result = CliRunner().invoke(app, ["tyre-degradation-smoke", "--output", str(output)])
    assert result.exit_code == 0, result.output
    return output


def test_cli_reload_posterior_and_manifest(study):
    result = CliRunner().invoke(app, ["verify-tyre-study", str(study)])
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["verified"] and not report["task_closure_eligible"]
    assert report["profile"] == "smoke" and report["posterior_shape"][:2] == [2, 200]
    summary = json.loads((study / "summary.json").read_text())
    assert summary["fuel_sensitivity"] == []
    assert summary["hierarchical_split"] == {"train": list(EVENTS[:2]), "calibration": [EVENTS[2]], "test": list(EVENTS[3:])}
    manifest = json.loads((study / "manifest.json").read_text())
    assert set(manifest["files"]) == {p.name for p in study.iterdir()} - {"manifest.json"}


def test_existing_output_refused_without_any_file_changes(study):
    before = {p.name: file_sha256(p) for p in study.iterdir()}
    with pytest.raises(FileExistsError):
        run_tyre_degradation_demo(study / "dataset.json", study, profile="smoke")
    assert before == {p.name: file_sha256(p) for p in study.iterdir()}


def test_corrupted_posterior_is_refused(study, tmp_path):
    import shutil

    target = tmp_path / "tampered"
    shutil.copytree(study, target)
    with (target / "hierarchical_draws.npz").open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        verify_tyre_study(target)


def test_missing_completion_manifest_is_refused(study, tmp_path):
    with pytest.raises(FileNotFoundError):
        verify_tyre_study(tmp_path)


def test_dataset_seal_and_simulated_research_claim_refused(tmp_path):
    data = make_tyre_smoke_dataset()
    source = tmp_path / "bad.json"
    data["segments"][0]["rows"][0]["corrected_s"] += 1
    write_manifest(source, data)
    with pytest.raises(ValueError, match="content hash mismatch"):
        run_tyre_degradation_demo(source, tmp_path / "bad-run", profile="smoke")
    clean = tmp_path / "simulated.json"
    write_manifest(clean, make_tyre_smoke_dataset())
    with pytest.raises(ValueError, match="source-bound public race archives"):
        run_tyre_degradation_demo(clean, tmp_path / "false-claim")
    assert not (tmp_path / "false-claim").exists()


def test_benchmark_denied_before_archive_verification_or_native_read(tmp_path, monkeypatch):
    calendar = tmp_path / "calendar"
    calendar.mkdir()
    write_manifest(calendar / "events.json", {"events": []})
    protected = tmp_path / "protected"
    protected.mkdir()
    write_manifest(protected / "manifest.json", {"query": {"year": 2023, "round_number": 4, "session": "R"}})
    monkeypatch.setattr(tyre_dataset, "verify_jolpica_archive", lambda _: {"content_sha256": "fixture"})
    def forbidden(_):
        pytest.fail("Protected archive payload was accessed")
    monkeypatch.setattr(tyre_dataset, "verify_fastf1_archive", forbidden)
    monkeypatch.setattr(tyre_dataset.pd, "read_parquet", forbidden)
    with pytest.raises(ValueError, match="Permanent benchmark"):
        tyre_dataset.build_tyre_dataset([protected], calendar)


def test_changed_test_events_cannot_change_hierarchy_or_validation(study):
    original = json.loads((study / "dataset.json").read_text())
    changed = copy.deepcopy(original)
    for segment in changed["segments"]:
        if segment["event_id"] in EVENTS[3:]:
            segment["rows"][-1]["corrected_s"] += 100
    settings = HierarchySettings(warmup=100, draws=200)
    summary, artifacts, model = evaluate_tyre_study(changed, settings)
    frozen = json.loads((study / "summary.json").read_text())
    assert summary["calibration_scales"] == {int(k): v for k, v in frozen["calibration_scales"].items()}
    assert json.loads(json.dumps(summary["hierarchical_noise_fit"])) == frozen["hierarchical_noise_fit"]
    assert summary["hierarchical_posterior"] == frozen["hierarchical_posterior"]
    with np.load(study / "hierarchical_draws.npz", allow_pickle=False) as weights:
        np.testing.assert_array_equal(model.chains, weights["parameters"])
        np.testing.assert_array_equal(model.variance_chains, weights["group_variances"])
    before = json.loads((study / "hierarchical_calibration_predictions.json").read_text())
    assert artifacts["hierarchical_calibration_predictions"] == before
    predictions = json.loads((study / "hierarchical_test_predictions.json").read_text())
    assert [r["predicted_corrected_s"] for r in predictions] == [r["predicted_corrected_s"] for r in artifacts["hierarchical_test_predictions"]]
    assert any(a["observed_corrected_s"] != b["observed_corrected_s"] for a, b in zip(predictions, artifacts["hierarchical_test_predictions"], strict=True))


def test_smoke_fixture_seal_and_benchmark_membership():
    dataset = make_tyre_smoke_dataset()
    assert dataset["content_sha256"] == payload_sha256({k: v for k, v in dataset.items() if k != "content_sha256"})
    assert dataset["truth_labels"]["lap_values"] == "SIMULATED"
