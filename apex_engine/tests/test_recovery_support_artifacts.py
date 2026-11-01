"""Full physical smoke pipeline plus isolated adversarial evidence boundaries."""
import copy
import shutil

import numpy as np
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.examples import imitation_study as imitation
from apexsim.examples import recovery_study as recovery
from apexsim.examples import support_study as support
from apexsim.provenance import payload_sha256, write_manifest
from apexsim.research.evidence import finish_run, read_json


@pytest.fixture(scope="module")
def campaign(tmp_path_factory):
    root = tmp_path_factory.mktemp("recovery-support")
    imitation.make_imitation_smoke_dataset(root/"dataset")
    imitation.fit_imitation_study(root/"dataset", root/"development")
    write_manifest(root/"development-replay.json", imitation.verify_imitation_development(root/"development"))
    imitation.run_imitation_evaluation(root/"development", root/"development-replay.json", root/"reference")
    recovery.prepare_recovery(root/"reference", root/"inputs")
    recovery.run_recovery(root/"inputs", root/"recovery")
    receipt = recovery.verify_recovery(root/"recovery")
    write_manifest(root/"recovery-replay.json", receipt)
    support.fit_support(root/"recovery", root/"recovery-replay.json", root/"detector")
    support.run_support(root/"detector", root/"support")
    return root


def test_complete_multilap_smoke_regenerates_and_never_claims_public_completion(campaign):
    summary, result = recovery.load_recovery(campaign/"recovery")
    receipt = read_json(campaign/"recovery-replay.json")
    assert summary["decision"] == "SIMULATED_EXECUTION_ONLY" and not result["task_closure_eligible"]
    assert result["gate"]["passed"] and len(result["cases"]) == 15
    assert receipt["verified"] and receipt["maximum_replay_difference"] == 0
    assert result["independent_audit"]["complete_horizons"] == 1


def test_complete_supervised_smoke_cli_regenerates_faults_and_abstention(campaign):
    checked = CliRunner().invoke(app, ["verify-support-benchmark", str(campaign/"support")])
    assert checked.exit_code == 0, checked.output
    assert '"maximum_replay_difference": 0.0' in checked.output
    summary, result = support.load_support(campaign/"support")
    assert summary["decision"] == "SIMULATED_EXECUTION_ONLY" and not result["task_closure_eligible"]
    assert len(result["cases"]) == 26 and result["gate"]["passed"]
    assert result["switch_audit"]["passed"] and result["switch_audit"]["switches_checked"] >= 24
    hard = [r for r in result["cases"] if r["scenario"] in support.HARD]
    assert len(hard) == 6 and all(r["abstained"] and r["progress_m"] == 0 for r in hard)


def test_relocated_detector_refits_and_fresh_outputs_cannot_be_overwritten(campaign, tmp_path):
    moved = tmp_path/"portable"
    shutil.copytree(campaign/"detector", moved)
    assert support.load_support_detector(moved)[0]["content_sha256"] == support.load_support_detector(campaign/"detector")[0]["content_sha256"]
    checked = CliRunner().invoke(app, ["verify-support-detector", str(moved)])
    assert checked.exit_code == 0, checked.output
    with pytest.raises(ValueError, match="fresh"):
        recovery.prepare_recovery(campaign/"reference", campaign/"inputs")
    with pytest.raises(ValueError, match="fresh"):
        support.run_support(campaign/"detector", campaign/"support")


def test_changed_trajectory_bytes_fail_exact_inventory(campaign, tmp_path):
    moved = tmp_path/"corrupt"
    shutil.copytree(campaign/"recovery", moved)
    (moved/"trajectories.npz").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="inventory"):
        recovery.load_recovery(moved)


def reseal(root, version, filename, mutate):
    summary, result = read_json(root/"summary.json"), read_json(root/filename)
    mutate(summary, result)
    for name in ("summary.json", "manifest.json", filename):
        (root/name).unlink()
    summary.pop("content_sha256")
    if filename == "results.json":
        summary["results_sha256"] = payload_sha256(result)
    else:
        summary["model_sha256"] = payload_sha256(result["model"])
        summary["ledger_sha256"] = payload_sha256(result["ledger"])
    write_manifest(root/filename, result)
    finish_run(root, version, summary)


def test_resealed_changed_cutoff_cannot_fake_training_and_validation(campaign, tmp_path):
    moved = tmp_path/"changed-cutoff"
    shutil.copytree(campaign/"detector", moved)
    reseal(moved, support.VERSION+"-detector", "detector.json", lambda s, r: r["model"].update(cutoff=r["model"]["cutoff"]*2))
    with pytest.raises(ValueError, match="numeric mismatch"):
        support.load_support_detector(moved)


def test_resealed_validation_ledger_is_rebuilt_from_frozen_source(campaign, tmp_path):
    moved = tmp_path/"changed-ledger"
    shutil.copytree(campaign/"detector", moved)
    reseal(moved, support.VERSION+"-detector", "detector.json", lambda s, r: r["ledger"]["validation_cases"].pop())
    with pytest.raises(ValueError, match="list mismatch"):
        support.load_support_detector(moved)


@pytest.mark.parametrize("module,name,version", [(recovery, "recovery", recovery.VERSION), (support, "support", support.VERSION)])
def test_resealed_false_completion_is_rejected_after_numerical_evidence(campaign, tmp_path, monkeypatch, module, name, version):
    # Full physical replay is tested above; isolate the truth/decision check here.
    moved = tmp_path/name
    shutil.copytree(campaign/name, moved)
    original = read_json(moved/"results.json")
    expected = {k: copy.deepcopy(v) for k, v in original.items() if k not in ("independent_audit", "decision", "task_closure_eligible")}
    with np.load(moved/"trajectories.npz", allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in archive.files}
    monkeypatch.setattr(module, "compute_"+name, lambda *args: (expected, arrays))
    monkeypatch.setattr(module, "audit_continuous", lambda *args, **kwargs: original["independent_audit"])
    def mutate(summary, result):
        summary["task_closure_eligible"] = result["task_closure_eligible"] = True
    reseal(moved, version, "results.json", mutate)
    with pytest.raises(ValueError, match="false completion"):
        getattr(module, "verify_"+name)(moved)


def test_actual_reserved_event_is_guarded_before_corrupt_arrays(campaign, tmp_path):
    moved = tmp_path/"reserved"
    shutil.copytree(campaign/"detector", moved)
    root = moved/"recovery/inputs/reference/development/dataset"
    header = read_json(root/"inputs.json")
    header["cases"][0]["event_id"] = "F1_2024_R04"
    (root/"inputs.json").unlink()
    write_manifest(root/"inputs.json", header)
    (root/"maps.npz").write_bytes(b"must not read")
    with pytest.raises(ValueError, match="Permanent benchmark event"):
        support.load_support_detector(moved)


def test_nontraining_fit_ledger_rejected_before_payload_access(monkeypatch, tmp_path):
    monkeypatch.setattr(support, "load_development", lambda *args: (None, {"base_episode_ledger": [{"role": "test"}]}, None, None, None))
    with pytest.raises(ValueError, match="forbids non-training"):
        support.detector_data(tmp_path)
