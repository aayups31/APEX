import json
import shutil

import numpy as np
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.examples import bicycle_study
from apexsim.examples.bicycle_study import (
    audit_bicycle_study,
    frozen_cases,
    load_bicycle_study,
    verify_bicycle_study,
)
from apexsim.provenance import file_sha256, payload_sha256
from apexsim.research import bicycle
from apexsim.research.bicycle import (
    BicycleControl,
    BicycleParameters,
    BicycleState,
    BicycleSupportError,
    integrate_bicycle,
)
from apexsim.research.bicycle_audit import independent_rhs, independent_support_exit, independent_trajectory


@pytest.fixture(scope="module")
def study(tmp_path_factory):
    root = tmp_path_factory.mktemp("r031")/"study"
    result = CliRunner().invoke(app, ["bicycle-dynamics-study", "--output", str(root)])
    assert result.exit_code == 0, result.output+repr(result.exception)
    return root


def reseal(root):
    result = json.loads((root/"results.json").read_text())
    summary = json.loads((root/"summary.json").read_text())
    summary["results_sha256"] = payload_sha256(result)
    summary["content_sha256"] = payload_sha256({k: v for k, v in summary.items() if k != "content_sha256"})
    (root/"summary.json").write_text(json.dumps(summary))
    manifest = json.loads((root/"manifest.json").read_text())
    manifest["summary_sha256"] = summary["content_sha256"]
    manifest["files"] = bicycle_study._inventory(root)
    manifest["content_sha256"] = payload_sha256({k: v for k, v in manifest.items() if k != "content_sha256"})
    (root/"manifest.json").write_text(json.dumps(manifest))


def test_complete_equation_campaign_replays_and_all_cli_commands_work(study):
    verified = verify_bicycle_study(study)
    assert verified["verified"] and verified["task_closure_eligible"]
    assert verified["maximum_reload_difference_si"] == 0
    _, result = load_bicycle_study(study)
    assert result["supported_cases"] == 13 and result["abstention_challenges"] == 1
    assert result["force_checks"]["grid_points"] == 420
    assert all(case["passed"] for case in result["cases"])
    assert not result["production_promotion"] and result["input_truth"] == "SYNTHETIC"
    for command in ("verify-bicycle-dynamics", "audit-bicycle-dynamics"):
        invocation = CliRunner().invoke(app, [command, str(study)])
        assert invocation.exit_code == 0, invocation.output+repr(invocation.exception)


def test_independent_equations_do_not_use_main_force_rhs_adapter_or_integrator(monkeypatch):
    p = BicycleParameters()
    state = BicycleState(vy_mps=.5, yaw_rate_radps=.1)
    command = BicycleControl(.04, 1000, -500, 100)
    expected = bicycle.bicycle_rhs(state, command, p)[0]

    def forbidden(*args, **kwargs):
        pytest.fail("Independent audit reused primary dynamics")

    monkeypatch.setattr(bicycle, "bicycle_rhs", forbidden)
    monkeypatch.setattr(bicycle, "axle_force", forbidden)
    monkeypatch.setattr(bicycle, "integrate_bicycle", forbidden)
    np.testing.assert_allclose(independent_rhs(state.array(), command, p), expected, atol=1e-12)
    path = independent_trajectory(state.array(), np.array([0, .1]), [command], p)
    assert path.shape == (2, 6) and np.isfinite(path).all()


def test_original_full_rear_grip_challenge_retains_exit_and_supported_prefix():
    case = next(c for c in frozen_cases() if c["name"] == "near_limit_drive")
    assert case["commands"][0].rear_fx_request_n == 6200
    time, boundary = independent_support_exit(case["initial"].array(), case["time_s"], case["commands"], case["params"])
    assert 0 < time < 1 and np.isfinite(boundary).all()
    for step in (.02, .01, .005):
        with pytest.raises(BicycleSupportError) as info:
            integrate_bicycle(case["initial"], case["time_s"], case["commands"], case["params"], max_step_s=step)
        error = info.value
        assert abs(error.time_s-time) <= .02
        assert error.partial_states.shape == (len(error.partial_time_s), 6)
        assert error.partial_time_s[-1] < error.time_s


def test_study_is_portable_and_existing_outputs_are_immutable(study, tmp_path):
    copied = tmp_path/"portable"
    shutil.copytree(study, copied)
    assert verify_bicycle_study(copied)["verified"]
    before = file_sha256(study/"manifest.json")
    result = CliRunner().invoke(app, ["bicycle-dynamics-study", "--output", str(study)])
    assert result.exit_code != 0 and isinstance(result.exception, FileExistsError)
    assert file_sha256(study/"manifest.json") == before


def test_modified_array_bytes_fail_before_mathematical_replay(study, tmp_path, monkeypatch):
    copied = tmp_path/"tampered"
    shutil.copytree(study, copied)
    with (copied/"trajectories.npz").open("ab") as handle:
        handle.write(b"tamper")
    monkeypatch.setattr(bicycle_study, "compute_evidence", lambda: pytest.fail("Read unverified evidence"))
    with pytest.raises(ValueError, match="inventory/hash"):
        verify_bicycle_study(copied)


def test_resealed_false_physical_promotion_cannot_pass_scientific_replay(study, tmp_path):
    copied = tmp_path/"false-promotion"
    shutil.copytree(study, copied)
    result = json.loads((copied/"results.json").read_text())
    result["production_promotion"] = True
    (copied/"results.json").write_text(json.dumps(result))
    reseal(copied)
    with pytest.raises(ValueError, match="scientific replay value"):
        verify_bicycle_study(copied)


def test_resealed_wrong_trajectory_cannot_pass_replay_or_independent_audit(study, tmp_path):
    copied = tmp_path/"false-trajectory"
    shutil.copytree(study, copied)
    with np.load(copied/"trajectories.npz", allow_pickle=False) as saved:
        arrays = {key: saved[key].copy() for key in saved.files}
    arrays["left__rk4_01"][3, 1] += 1
    np.savez_compressed(copied/"trajectories.npz", **arrays)
    reseal(copied)
    with pytest.raises(ValueError, match="trajectory mismatch"):
        verify_bicycle_study(copied)
    with pytest.raises(ValueError, match="DOP853 trajectory audit"):
        audit_bicycle_study(copied)


def test_resealed_reduced_case_catalogue_is_refused(study, tmp_path):
    copied = tmp_path/"dropped-case"
    shutil.copytree(study, copied)
    config = json.loads((copied/"configuration.json").read_text())
    config["cases"] = [c for c in config["cases"] if c["name"] != "near_limit_drive"]
    (copied/"configuration.json").write_text(json.dumps(config))
    reseal(copied)
    with pytest.raises(ValueError, match="configuration/truth"):
        verify_bicycle_study(copied)


def test_exact_stored_integrity_is_separate_from_numeric_replay_tolerance(study, monkeypatch):
    original = bicycle_study.compute_evidence

    def harmless_rounding():
        result, arrays = original()
        result["force_checks"]["maximum_hand_fixture_error_si"] += 1e-10
        arrays["left__rk4_01"] += 1e-10
        return result, arrays

    monkeypatch.setattr(bicycle_study, "compute_evidence", harmless_rounding)
    assert verify_bicycle_study(study)["verified"]
