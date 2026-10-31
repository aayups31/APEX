import json
import shutil
from dataclasses import replace

import numpy as np
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.examples.longitudinal_dataset import inventory, read_json, verify_longitudinal_dataset
from apexsim.examples.longitudinal_study import (
    VERSION,
    compute_development,
    evaluate_longitudinal_study,
    fit_longitudinal_study,
    load_inputs,
    verify_longitudinal_development,
    verify_longitudinal_study,
)
from apexsim.provenance import file_sha256, payload_sha256
from apexsim.research.longitudinal_audit import independent_longitudinal_audit


@pytest.fixture(scope="module")
def study(tmp_path_factory):
    root = tmp_path_factory.mktemp("r030-study")/"run"
    result = CliRunner().invoke(app, ["longitudinal-calibration-smoke", "--output", str(root)])
    assert result.exit_code == 0, result.output+repr(result.exception)
    return root


def test_complete_simulated_study_replays_and_independent_solver_agrees(study):
    verified = verify_longitudinal_study(study)
    assert verified["verified"] and verified["decision"] == "SIMULATED_EXECUTION_ONLY"
    assert not verified["task_closure_eligible"]
    assert verified["maximum_reload_difference_mps"] == 0
    independent = independent_longitudinal_audit(study)
    assert independent["verified"] and independent["checked_convex_fits"] == 8
    assert independent["maximum_dop853_difference_mps"] < 1e-6


def test_test_outcomes_cannot_change_training_validation_or_bootstrap_selection(study):
    source, sections = load_inputs(study/"development/dataset")
    changed = [replace(s, speed_mps=np.r_[s.speed_mps[0], s.speed_mps[1:]+.5]) if s.metadata["role"] == "test" else s for s in sections]
    a, draws_a, predictions_a = compute_development(sections, source["profile"])
    b, draws_b, predictions_b = compute_development(changed, source["profile"])
    assert a == b and draws_a == draws_b
    assert set(predictions_a) == set(predictions_b)
    for key in predictions_a:
        np.testing.assert_array_equal(predictions_a[key], predictions_b[key])


def test_frozen_development_verifier_does_not_score_test_and_outputs_are_immutable(study):
    dev = study/"development"
    before = inventory(dev)
    assert verify_longitudinal_development(dev)["test_outcomes_used"] is False
    with pytest.raises(FileExistsError):
        fit_longitudinal_study(dev/"dataset", dev)
    with pytest.raises(FileExistsError):
        evaluate_longitudinal_study(dev, study)
    assert inventory(dev) == before


def test_portable_study_and_tamper_refusal(study, tmp_path):
    target = tmp_path/"portable"
    shutil.copytree(study, target)
    assert verify_longitudinal_study(target)["verified"]
    with (target/"predictions.npz").open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError, match="inventory/hash"):
        verify_longitudinal_study(target)


def test_fake_public_profile_cannot_replace_native_geometry_provenance(study, tmp_path):
    target = tmp_path/"fake-public"
    shutil.copytree(study/"development/dataset", target)
    summary = read_json(target/"summary.json")
    summary["profile"] = "research"
    summary["content_sha256"] = payload_sha256({k: v for k, v in summary.items() if k != "content_sha256"})
    (target/"summary.json").write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="frozen native/geometry"):
        load_inputs(target)


def test_protected_section_is_rejected_before_npz_access(study, tmp_path, monkeypatch):
    target = tmp_path/"protected"
    shutil.copytree(study/"development/dataset", target)
    metadata = read_json(target/"section_metadata.json")
    metadata[0]["event_id"] = "F1_2023_R04"
    (target/"section_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr(np, "load", lambda *a, **k: pytest.fail("Protected native payload read"))
    with pytest.raises(ValueError, match="Permanent benchmark"):
        load_inputs(target)


def test_resealed_false_acceptance_fails_scientific_replay(study, tmp_path):
    target = tmp_path/"false-acceptance"
    shutil.copytree(study, target)
    result = read_json(target/"results.json")
    result["decision"] = "ACCEPT_SCOPED_LONGITUDINAL_CALIBRATION"
    (target/"results.json").write_text(json.dumps(result), encoding="utf-8")
    summary = read_json(target/"summary.json")
    summary["decision"] = result["decision"]
    summary["task_closure_eligible"] = True
    summary["results_sha256"] = payload_sha256(result)
    summary["content_sha256"] = payload_sha256({k: v for k, v in summary.items() if k != "content_sha256"})
    (target/"summary.json").write_text(json.dumps(summary), encoding="utf-8")
    manifest = {"schema_version": VERSION+"-study-manifest", "summary_sha256": summary["content_sha256"], "files": inventory(target)}
    manifest["content_sha256"] = payload_sha256(manifest)
    (target/"manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="replay value"):
        verify_longitudinal_study(target)


def test_smoke_has_no_public_native_reconstruction_and_original_bytes_are_preserved(study):
    before = file_sha256(study/"manifest.json")
    with pytest.raises(FileNotFoundError):
        verify_longitudinal_dataset(study/"development/dataset")
    assert file_sha256(study/"manifest.json") == before
