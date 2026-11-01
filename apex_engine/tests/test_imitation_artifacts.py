import copy
import shutil

import numpy as np
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.examples import imitation_study as study
from apexsim.provenance import payload_sha256, write_manifest
from apexsim.research.evidence import finish_run, read_json


@pytest.fixture(scope="module")
def campaign(tmp_path_factory):
    root = tmp_path_factory.mktemp("imitation")
    dataset, development, evaluation = root/"dataset", root/"development", root/"evaluation"
    study.make_imitation_smoke_dataset(dataset)
    study.fit_imitation_study(dataset, development)
    receipt = study.verify_imitation_development(development)
    write_manifest(root/"development-replay.json", receipt)
    study.run_imitation_evaluation(development, root/"development-replay.json", evaluation)
    return root


def test_complete_smoke_cli_replays_all_stages_without_public_completion(campaign):
    result = CliRunner().invoke(app, ["verify-imitation-driver", str(campaign/"evaluation")])
    assert result.exit_code == 0, result.output
    assert '"maximum_replay_difference": 0.0' in result.output
    summary, saved = study.load_imitation_evaluation(campaign/"evaluation")
    assert summary["decision"] == "SIMULATED_EXECUTION_ONLY" and not saved["task_closure_eligible"]
    assert len(saved["cases"]) == 22
    assert saved["independent_audit"]["passed"]
    development = read_json(campaign/"development/development.json")
    assert len(development["trials"]) == 34 and development["aggregated_training_rows"] > development["base_training_rows"]


def test_frozen_artifacts_are_portable_and_existing_outputs_immutable(campaign, tmp_path):
    moved = tmp_path/"portable"
    shutil.copytree(campaign/"evaluation", moved)
    assert study.load_imitation_evaluation(moved)[0]["content_sha256"] == study.load_imitation_evaluation(campaign/"evaluation")[0]["content_sha256"]
    assert study.verify_imitation_development(moved/"development", replay_dynamics=False)["verified"]
    with pytest.raises(ValueError, match="fresh"):
        study.fit_imitation_study(campaign/"dataset", campaign/"development")
    with pytest.raises(ValueError, match="fresh"):
        study.run_imitation_evaluation(campaign/"development", campaign/"development-replay.json", campaign/"evaluation")


def test_changed_model_or_training_payload_fails_exact_inventory(campaign, tmp_path):
    moved = tmp_path/"corrupt"
    shutil.copytree(campaign/"development", moved)
    (moved/"training.npz").write_bytes(b"tamper")
    with pytest.raises(ValueError, match="inventory"):
        study.load_development(moved)


def reseal_development(root, change):
    summary, result = read_json(root/"summary.json"), read_json(root/"development.json")
    change(summary, result)
    for name in ("summary.json", "manifest.json", "development.json"):
        (root/name).unlink()
    summary.pop("content_sha256")
    summary["development_sha256"] = payload_sha256(result)
    write_manifest(root/"development.json", result)
    finish_run(root, study.VERSION+"-development", summary)


def test_resealed_wrong_validation_selection_is_rejected(campaign, tmp_path):
    moved = tmp_path/"changed-selection"
    shutil.copytree(campaign/"development", moved)

    def change(summary, result):
        name = next(n for n in result["models"] if n != result["selected"] and n.startswith("bc_d1"))
        result["selected"] = summary["selected"] = name
        summary["selected_model_sha256"] = payload_sha256(result["models"][name])

    reseal_development(moved, change)
    with pytest.raises(ValueError, match="false frozen model choice"):
        study.verify_imitation_development(moved, replay_dynamics=False)


def test_resealed_missing_failed_or_successful_case_is_rejected(campaign, tmp_path):
    moved = tmp_path/"reduced"
    shutil.copytree(campaign/"development", moved)
    reseal_development(moved, lambda summary, result: result["trials"].pop())
    with pytest.raises(ValueError, match="trial catalog"):
        study.verify_imitation_development(moved, replay_dynamics=False)


def test_resealed_coefficient_change_cannot_fake_genuine_training(campaign, tmp_path):
    moved = tmp_path/"changed-coefficients"
    shutil.copytree(campaign/"development", moved)

    def change(summary, result):
        result["models"][result["selected"]]["coefficients"][0] += .01
        summary["selected_model_sha256"] = payload_sha256(result["models"][result["selected"]])

    reseal_development(moved, change)
    with pytest.raises(ValueError, match="QR ridge"):
        study.verify_imitation_development(moved, replay_dynamics=False)


def test_resealed_false_public_completion_is_rejected(campaign, tmp_path, monkeypatch):
    # Reuse the already-regenerated real synthetic paths to isolate the final gate.
    moved = tmp_path/"false-completion"
    shutil.copytree(campaign/"evaluation", moved)
    summary, result = study.load_imitation_evaluation(moved)
    raw = {k: copy.deepcopy(v) for k, v in result.items() if k not in ("independent_audit", "decision", "task_closure_eligible")}
    with np.load(moved/"trajectories.npz", allow_pickle=False) as archive:
        paths = {name: archive[name] for name in archive.files}
    monkeypatch.setattr(study, "compute_imitation_evaluation", lambda *args: (raw, paths))
    monkeypatch.setattr("apexsim.research.imitation_audit.audit_final_paths", lambda *args: result["independent_audit"])
    for item in (summary, result):
        item.update(task_closure_eligible=True, decision="ACCEPT_CONDITIONAL_IMITATION_DRIVER")
    for name in ("summary.json", "manifest.json", "results.json"):
        (moved/name).unlink()
    summary.pop("content_sha256")
    summary["results_sha256"] = payload_sha256(result)
    write_manifest(moved/"results.json", result)
    finish_run(moved, study.VERSION, summary)
    with pytest.raises(ValueError, match="false completion"):
        study.verify_imitation_evaluation(moved)


def test_real_reserved_event_guard_precedes_corrupt_model_arrays(campaign, tmp_path):
    moved = tmp_path/"protected"
    shutil.copytree(campaign/"development", moved)
    header = read_json(moved/"dataset/inputs.json")
    header["cases"][0]["event_id"] = "F1_2024_R04"
    (moved/"dataset/inputs.json").unlink()
    write_manifest(moved/"dataset/inputs.json", header)
    (moved/"training.npz").write_bytes(b"should never be read")
    with pytest.raises(ValueError, match="Permanent benchmark event"):
        study.load_development(moved)
