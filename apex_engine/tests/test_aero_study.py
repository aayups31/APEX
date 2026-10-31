import json
import shutil

import numpy as np
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.examples import aero_study
from apexsim.examples.aero_study import audit_aero_study, load_aero_study, verify_aero_study
from apexsim.provenance import payload_sha256
from apexsim.research import aero_bicycle
from apexsim.research.aero_audit import independent_loaded_rhs
from apexsim.research.aero_bicycle import AeroParameters
from apexsim.research.aero_identifiability import identifiability_report
from apexsim.research.bicycle import BicycleControl, BicycleParameters, BicycleState
from apexsim.research.evidence import inventory, seal


@pytest.fixture(scope="module")
def study(tmp_path_factory):
    root = tmp_path_factory.mktemp("r032")/"study"
    invocation = CliRunner().invoke(app, ["aero-load-study", "--output", str(root)])
    assert invocation.exit_code == 0, invocation.output+repr(invocation.exception)
    return root


def reseal(root):
    summary = json.loads((root/"summary.json").read_text())
    summary.pop("content_sha256")
    summary["results_sha256"] = payload_sha256(json.loads((root/"results.json").read_text()))
    summary = seal(summary)
    (root/"summary.json").write_text(json.dumps(summary))
    manifest = seal({"schema_version": aero_study.VERSION+"-manifest", "summary_sha256": summary["content_sha256"], "files": inventory(root)})
    (root/"manifest.json").write_text(json.dumps(manifest))


def test_structural_confounds_are_exposed_and_oracle_is_not_public_identification():
    result = identifiability_report()
    assert result["passed"] and result["rank"] == 4 and result["parameters"] == 5
    assert result["drag_only_rank"] == 1 and result["zero_tyre_force_rank"] == 3
    assert result["fixed_density_rank"] == 4
    assert result["maximum_normalized_fd_error"] <= 1e-5
    assert not result["real_parameters_identified"]


def test_independent_scalar_load_solver_never_reuses_primary_helpers(monkeypatch):
    state, command = BicycleState(vy_mps=.2, yaw_rate_radps=.02), BicycleControl(.03, -1000, -500)
    p, aero = BicycleParameters(), AeroParameters()
    expected, diagnostic = aero_bicycle.aero_bicycle_rhs(state, command, p, aero)

    def forbidden(*args, **kwargs):
        pytest.fail("Independent R032 audit used primary solver")

    monkeypatch.setattr(aero_bicycle, "solve_axle_loads", forbidden)
    monkeypatch.setattr(aero_bicycle, "axle_force", forbidden)
    monkeypatch.setattr(aero_bicycle, "aero_bicycle_rhs", forbidden)
    actual, loads = independent_loaded_rhs(state.array(), command, p, aero)
    np.testing.assert_allclose(actual, expected, atol=1e-7, rtol=0)
    np.testing.assert_allclose(loads, [diagnostic.loads.front.normal_n, diagnostic.loads.rear.normal_n], atol=1e-7, rtol=0)


def test_complete_campaign_replay_and_independent_audit(study):
    assert verify_aero_study(study)["maximum_reload_difference"] == 0
    audit = audit_aero_study(study)
    assert audit["verified"] and audit["cases"] == 7
    assert max(audit["maximum_error_by_state"]) <= 1e-4
    _, result = load_aero_study(study)
    assert result["task_closure_eligible"] and len(result["sensitivity"]) == 8
    assert result["force_grid"]["supported"]+result["force_grid"]["abstained"] == 45


def test_portable_run_and_immutable_output(study, tmp_path):
    target = tmp_path/"portable"
    shutil.copytree(study, target)
    assert verify_aero_study(target)["verified"]
    invocation = CliRunner().invoke(app, ["aero-load-study", "--output", str(study)])
    assert isinstance(invocation.exception, FileExistsError)


def test_modified_bytes_are_rejected_before_recomputation(study, tmp_path, monkeypatch):
    target = tmp_path/"tampered"
    shutil.copytree(study, target)
    with (target/"trajectories.npz").open("ab") as handle:
        handle.write(b"changed")
    monkeypatch.setattr(aero_study, "compute_evidence", lambda: pytest.fail("Recomputed unverified input"))
    with pytest.raises(ValueError, match="inventory/hash"):
        verify_aero_study(target)


def test_resealed_false_identification_and_bad_paths_cannot_pass_science(study, tmp_path):
    target = tmp_path/"false-identification"
    shutil.copytree(study, target)
    result = json.loads((target/"results.json").read_text())
    result["identifiability"]["real_parameters_identified"] = True
    (target/"results.json").write_text(json.dumps(result))
    reseal(target)
    with pytest.raises(ValueError, match="replay value"):
        verify_aero_study(target)
    path = tmp_path/"bad-path"
    shutil.copytree(study, path)
    with np.load(path/"trajectories.npz", allow_pickle=False) as saved:
        values = {k: saved[k].copy() for k in saved.files}
    values["left__rk4_01"][2, 0] += 1
    np.savez_compressed(path/"trajectories.npz", **values)
    reseal(path)
    with pytest.raises(ValueError, match="DOP853 audit failed"):
        audit_aero_study(path)


def test_numeric_replay_tolerance_does_not_override_exact_integrity(study, monkeypatch):
    original = aero_study.compute_evidence

    def rounding():
        result, arrays = original()
        result["hand_error_n"] += 1e-10
        arrays["left__rk4_01"] += 1e-10
        return result, arrays

    monkeypatch.setattr(aero_study, "compute_evidence", rounding)
    assert verify_aero_study(study)["verified"]
