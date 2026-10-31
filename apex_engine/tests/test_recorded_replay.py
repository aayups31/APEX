import json
import shutil

import pandas as pd
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.examples import recorded_replay
from apexsim.examples.recorded_replay import (
    audit_recorded_replay,
    load_recorded_replay,
    verify_recorded_replay,
)
from apexsim.provenance import payload_sha256
from apexsim.research.evidence import inventory, seal


@pytest.fixture(scope="module")
def study(tmp_path_factory):
    root = tmp_path_factory.mktemp("r033")/"fixture"
    result = CliRunner().invoke(app, ["recorded-replay-smoke", "--output", str(root)])
    assert result.exit_code == 0, result.output+repr(result.exception)
    return root


def reseal(root):
    summary = json.loads((root/"summary.json").read_text())
    summary.pop("content_sha256")
    summary["results_sha256"] = payload_sha256(json.loads((root/"results.json").read_text()))
    summary["input_header_sha256"] = payload_sha256(json.loads((root/"inputs.json").read_text()))
    summary["longitudinal_inputs_sha256"] = payload_sha256(json.loads((root/"longitudinal_inputs.json").read_text()))
    summary = seal(summary)
    (root/"summary.json").write_text(json.dumps(summary))
    manifest = seal({"schema_version": recorded_replay.VERSION+"-manifest", "summary_sha256": summary["content_sha256"], "files": inventory(root)})
    (root/"manifest.json").write_text(json.dumps(manifest))


def test_complete_simulated_pipeline_replays_and_cannot_close_public_task(study):
    summary, result = load_recorded_replay(study)
    assert result["coverage_gate_passed"] and result["source_laps"] == 8
    assert result["totals"]["native_car_rows"] == 400
    assert result["supported_longitudinal_sections"] == 8
    assert not summary["task_closure_eligible"] and result["full_bicycle_measured_state_control_coverage"] == 0
    assert verify_recorded_replay(study)["maximum_native_reload_difference"] == 0
    audit = audit_recorded_replay(study)
    assert audit["verified"] and audit["rows"] == 400 and audit["longitudinal_inputs_checked"] == 8
    assert audit["maximum_native_conversion_error"] == 0


def test_relocated_outputs_and_cli_verifiers_are_portable_and_immutable(study, tmp_path):
    target = tmp_path/"relocated"
    shutil.copytree(study, target)
    for command in ("verify-recorded-replay", "audit-recorded-replay"):
        invocation = CliRunner().invoke(app, [command, str(target)])
        assert invocation.exit_code == 0, invocation.output+repr(invocation.exception)
    before = inventory(study)
    invocation = CliRunner().invoke(app, ["recorded-replay-smoke", "--output", str(study)])
    assert isinstance(invocation.exception, FileExistsError)
    assert inventory(study) == before


def test_source_tamper_is_refused_before_alignment(study, tmp_path, monkeypatch):
    target = tmp_path/"tamper"
    shutil.copytree(study, target)
    with next((target/"simulated_native").glob("*_car.parquet")).open("ab") as handle:
        handle.write(b"changed")
    monkeypatch.setattr(recorded_replay, "compute_alignment", lambda *a: pytest.fail("Used unverified input"))
    with pytest.raises(ValueError, match="inventory/hash"):
        verify_recorded_replay(target)


def test_protected_event_guard_precedes_all_binary_payload_reads(study, tmp_path, monkeypatch):
    target = tmp_path/"protected"
    shutil.copytree(study, target)
    header = json.loads((target/"inputs.json").read_text())
    header["laps"][0]["event_id"] = "F1_2023_R04"
    (target/"inputs.json").write_text(json.dumps(header))
    monkeypatch.setattr(pd, "read_parquet", lambda *a, **k: pytest.fail("Protected native payload accessed"))
    with pytest.raises(ValueError, match="Permanent benchmark"):
        verify_recorded_replay(target)


def test_fake_public_profile_cannot_replace_frozen_geometry_and_native_provenance(study, tmp_path):
    target = tmp_path/"fake-public"
    shutil.copytree(study, target)
    header = json.loads((target/"inputs.json").read_text())
    header.update(profile="research", input_truth="FASTF1_PARSED_SOURCE")
    (target/"inputs.json").write_text(json.dumps(header))
    with pytest.raises(FileNotFoundError):
        verify_recorded_replay(target)


def test_resealed_false_public_acceptance_fails_mathematical_replay(study, tmp_path):
    target = tmp_path/"false-gate"
    shutil.copytree(study, target)
    result = json.loads((target/"results.json").read_text())
    result["task_closure_eligible"] = True
    (target/"results.json").write_text(json.dumps(result))
    summary = json.loads((target/"summary.json").read_text())
    summary["task_closure_eligible"] = True
    (target/"summary.json").write_text(json.dumps(summary))
    reseal(target)
    with pytest.raises(ValueError, match="replay value"):
        verify_recorded_replay(target)


def test_resealed_fabricated_body_state_is_rejected_by_replay_and_independent_audit(study, tmp_path):
    target = tmp_path/"fabricated-state"
    shutil.copytree(study, target)
    path = sorted((target/"frames").glob("*.parquet"))[0]
    frame = pd.read_parquet(path)
    frame.loc[10, "body_vy_mps"] = 0
    frame.to_parquet(path, index=False)
    reseal(target)
    with pytest.raises(ValueError, match="aligned-frame replay"):
        verify_recorded_replay(target)
    with pytest.raises(ValueError, match="unknown-state"):
        audit_recorded_replay(target)


def test_independent_audit_rejects_resealed_dropped_sections(study, tmp_path):
    target = tmp_path/"dropped-section"
    shutil.copytree(study, target)
    bundles = json.loads((target/"longitudinal_inputs.json").read_text())
    (target/"longitudinal_inputs.json").write_text(json.dumps(bundles[:-1]))
    reseal(target)
    with pytest.raises(ValueError, match="section inventory"):
        audit_recorded_replay(target)
