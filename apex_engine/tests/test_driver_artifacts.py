"""Artifact trust-boundary tests; physics is exercised by the real synthetic laps.

Only the already-tested source/calibration boundary and costly rollout generator
are replaced here. Inventory, bindings, false-completion logic and scientific
artifact checks use the production implementations.
"""
import copy
import shutil

import numpy as np
import pytest

from apexsim.examples import driver_study
from apexsim.examples.recorded_replay import VERSION as RECORDED_VERSION
from apexsim.provenance import payload_sha256, write_manifest
from apexsim.research.driver_audit import audit_arrays
from apexsim.research.evidence import finish_run, read_json, seal


@pytest.fixture
def artifact(tmp_path, monkeypatch):
    root = tmp_path/"study"
    root.mkdir()
    calibration = seal({"fixture_truth": "SIMULATED_TRUST_BOUNDARY_FIXTURE"})
    raw = {"cases": [], "refinements": [], "nominal_and_refinement_gate_passed": False,
           "calibration_sha256": calibration["content_sha256"], "selected": {"fraction": .35, "maximum_mps": 60.},
           "production_promotion": False, "conditional_research_only": True, "complete_measured_car_replay": False}
    result = dict(raw, independent_audit=audit_arrays(raw, {}), task_closure_eligible=False, decision="REJECT_CONDITIONAL_RESEARCH_DRIVER")
    monkeypatch.setattr(driver_study, "load_calibration", lambda path: (calibration, {}, {}))
    monkeypatch.setattr(driver_study, "verify_driver_calibration", lambda path: {"verified": True})
    monkeypatch.setattr(driver_study, "compute_rollouts", lambda *args: (copy.deepcopy(raw), {}))
    np.savez_compressed(root/"trajectories.npz")
    write_manifest(root/"results.json", result)
    finish_run(root, driver_study.VERSION, {"schema_version": driver_study.VERSION, "decision": result["decision"],
                                          "task_closure_eligible": False, "results_sha256": payload_sha256(result),
                                          "calibration_sha256": calibration["content_sha256"], "implementation_sha256": {},
                                          "production_promotion": False, "conditional_research_only": True})
    return root


def reseal(root, mutate):
    summary, result = read_json(root/"summary.json"), read_json(root/"results.json")
    mutate(summary, result)
    for name in ("summary.json", "manifest.json", "results.json"):
        (root/name).unlink()
    summary.pop("content_sha256")
    summary["results_sha256"] = payload_sha256(result)
    write_manifest(root/"results.json", result)
    finish_run(root, driver_study.VERSION, summary)


def test_portable_failure_artifact_replays_without_false_acceptance(artifact, tmp_path):
    moved = tmp_path/"portable"
    shutil.copytree(artifact, moved)
    verified = driver_study.verify_driver_study(moved)
    assert verified["verified"] and not verified["task_closure_eligible"]


def test_existing_destinations_are_immutable(artifact):
    with pytest.raises(FileExistsError):
        driver_study.run_driver_study(artifact, artifact)
    with pytest.raises(FileExistsError):
        driver_study.freeze_driver_calibration(artifact, artifact)


def test_changed_trajectory_payload_is_rejected(artifact):
    (artifact/"trajectories.npz").write_bytes(b"tamper")
    with pytest.raises(ValueError, match="inventory"):
        driver_study.load_driver_study(artifact)


def test_resealed_false_completion_does_not_pass_scientific_verifier(artifact):
    def forge(summary, result):
        for item in (summary, result):
            item.update(task_closure_eligible=True, decision="ACCEPT_CONDITIONAL_RESEARCH_DRIVER")

    reseal(artifact, forge)
    with pytest.raises(ValueError, match="false completion"):
        driver_study.verify_driver_study(artifact)


def test_resealed_source_binding_change_is_rejected(artifact):
    def forge(summary, result):
        summary["calibration_sha256"] = result["calibration_sha256"] = "0"*64

    reseal(artifact, forge)
    with pytest.raises(ValueError, match="binding"):
        driver_study.load_driver_study(artifact)


def test_protected_header_is_guarded_before_missing_binary_payload(tmp_path):
    (tmp_path/"recorded").mkdir()
    write_manifest(tmp_path/"recorded/inputs.json", {"schema_version": RECORDED_VERSION+"-inputs",
                                                   "laps": [{"event_id": "F1_2024_R05", "track_id": "shanghai", "driver_id": "4"}]})
    with pytest.raises(ValueError):
        driver_study.load_calibration(tmp_path)
