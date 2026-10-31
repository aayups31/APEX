import shutil
from pathlib import Path

import pytest

from apexsim.examples.open_loop_study import (
    load_study,
    native_stint,
    run_open_loop_study,
    verify_open_loop_study,
)
from apexsim.examples.recorded_replay import make_recorded_smoke
from apexsim.provenance import payload_sha256, write_manifest
from apexsim.research.evidence import finish_run, read_json, seal
from apexsim.research.longitudinal_calibration import SpecificPowerDrag
from apexsim.research.open_loop_audit import audit_open_loop_study


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    root = tmp_path_factory.mktemp("r034")
    recorded, development, output = root/"recorded", root/"development", root/"output"
    make_recorded_smoke(recorded)
    cells = [track+"/"+driver for track in ("bahrain", "monza") for driver in ("4", "44")]
    models = {"candidates": {"shared_drag": {"cells": {c: {"parameters": SpecificPowerDrag(600, .001).as_dict()} for c in cells}}},
              "legacy": {c: {"rolling_accel": .1, "throttle_accel_gain": 8., "drag_accel_coeff": .001} for c in cells}}
    development.mkdir()
    write_manifest(development/"models.json", models)
    write_manifest(development/"summary.json", seal({"profile": "smoke", "models_sha256": payload_sha256(models)}))
    run_open_loop_study(recorded, development, output)
    return output


def test_smoke_accounts_short_horizons_without_claiming_public_completion(report):
    summary, result = load_study(report)
    assert not summary["task_closure_eligible"]
    assert result["source_laps"] == 8 and result["sections"] == 8
    assert result["supported_horizon_cases"] == 24 and result["abstained_horizon_cases"] == 8
    assert all(lap["full_lap_physics_error"] is None for lap in result["lap_catalog"])
    assert verify_open_loop_study(report)["maximum_replay_difference"] == 0
    assert audit_open_loop_study(report)["paths_checked"] == 120


def test_relocation_and_immutable_destination(report, tmp_path):
    moved = tmp_path/"portable"
    shutil.copytree(report, moved)
    assert verify_open_loop_study(moved)["verified"]
    with pytest.raises(FileExistsError):
        run_open_loop_study(report/"recorded", report.parent/"development", moved)


def test_tampering_is_rejected(report, tmp_path):
    copied = tmp_path/"tampered"
    shutil.copytree(report, copied)
    (copied/"predictions.npz").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="inventory"):
        load_study(copied)


def test_resealed_false_completion_is_rejected_scientifically(report, tmp_path):
    copied = tmp_path/"false"
    shutil.copytree(report, copied)
    summary, result = load_study(copied)
    (copied/"summary.json").unlink()
    (copied/"manifest.json").unlink()
    (copied/"results.json").unlink()
    result["task_closure_eligible"] = True
    write_manifest(copied/"results.json", result)
    summary.pop("content_sha256")
    summary["task_closure_eligible"] = True
    summary["results_sha256"] = payload_sha256(result)
    finish_run(copied, summary["schema_version"], summary)
    with pytest.raises(ValueError, match="Scientific replay"):
        verify_open_loop_study(copied)


def test_protected_header_guard_precedes_missing_payload(report, tmp_path):
    copied = tmp_path/"protected"
    shutil.copytree(report, copied)
    header = read_json(copied/"recorded/inputs.json")
    header["laps"][0]["event_id"] = "F1_2024_R04"
    (copied/"recorded/inputs.json").unlink()
    write_manifest(copied/"recorded/inputs.json", header)
    (copied/"predictions.npz").unlink()
    with pytest.raises(ValueError, match="Permanent benchmark event"):
        load_study(copied)


def test_missing_stint_is_explicit():
    result = native_stint(Path("unused"), {}, False)
    assert result["stint_id"] is None and result["membership_truth"].startswith("UNKNOWN")
