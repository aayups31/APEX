import json
import shutil
from pathlib import Path

import pytest
import torch

from apexsim.examples.sac_strategy_demo import run_sac_strategy_demo
from apexsim.examples.strategy_scenarios_demo import load_frozen_run, run_strategy_scenarios_demo
from apexsim.provenance import file_sha256, payload_sha256
from apexsim.research.continuation_reference import tiny_continuation_reference
from apexsim.research.sac_env import StrategyLearningEnv
from apexsim.research.strategy_scenarios import SCENARIOS, PlanController, Scenario, evaluate_scenario
from apexsim.sim_core.types import TyreCompound


@pytest.fixture(scope="module")
def frozen_run(tmp_path_factory):
    pytest.importorskip("casadi")
    root = tmp_path_factory.mktemp("r018-input") / "smoke"
    run_sac_strategy_demo(root, "smoke")
    return root


def _rehash(root, name):
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["files"][name] = {"sha256": file_sha256(root / name), "bytes": (root / name).stat().st_size}
    manifest.pop("content_sha256")
    manifest["content_sha256"] = payload_sha256(manifest)
    (root / "manifest.json").write_text(json.dumps(manifest))


def test_frozen_artifact_integration(frozen_run, tmp_path):
    output = tmp_path / "scenarios"
    summary = run_strategy_scenarios_demo(frozen_run, output)
    assert summary["passed"] and summary["training_steps"] == 0
    assert summary["evaluation_attempts"] == 75 and summary["failed_episodes"] == 0
    assert summary["frozen_policy_state_unchanged"] and not summary["promotion_recommended"]
    assert summary["published_magnitude_comparison"] == "INCONCLUSIVE"
    assert summary["max_objective_replay_error_s"] <= 1e-8
    rows = json.loads((output / "rollouts.json").read_text())
    assert len(rows) == 75 and all(len(r["trajectory"]) == 3 for r in rows)
    assert all("signed_full_race_gap_to_causal_s" in r for r in rows)
    assert len(summary["case_rankings"]) == 15
    manifest = json.loads((output / "manifest.json").read_text())
    digest = manifest.pop("content_sha256")
    assert digest == payload_sha256(manifest)
    assert manifest["summary_sha256"] == summary["content_sha256"]
    for name, record in manifest["files"].items():
        assert record["sha256"] == file_sha256(output / name)
        assert record["bytes"] == (output / name).stat().st_size
    with pytest.raises(FileExistsError):
        run_strategy_scenarios_demo(frozen_run, output)
    with pytest.raises(ValueError, match="outside"):
        run_strategy_scenarios_demo(frozen_run, frozen_run / "child")
    assert not (frozen_run / "child").exists()


@pytest.mark.parametrize("tamper", ["bytes", "config", "updates", "kind", "nonfinite", "inventory", "traversal"])
def test_input_tampering_rejected_without_output(frozen_run, tmp_path, tamper):
    root = tmp_path / "input"
    shutil.copytree(frozen_run, root)
    if tamper == "bytes":
        with (root / "seed-11.pt").open("ab") as handle:
            handle.write(b"tamper")
    elif tamper == "config":
        config = json.loads((root / "config.json").read_text())
        config["environment"]["battery_smoothing_mj"] = .02
        (root / "config.json").write_text(json.dumps(config))
        _rehash(root, "config.json")
    elif tamper in ("updates", "kind", "nonfinite"):
        checkpoint = torch.load(root / "seed-11.pt", weights_only=True)
        if tamper == "updates":
            checkpoint["updates"] -= 1
        elif tamper == "kind":
            checkpoint["checkpoint_kind"] = "resume"
        else:
            next(iter(checkpoint["actor"].values())).fill_(float("nan"))
        torch.save(checkpoint, root / "seed-11.pt")
        _rehash(root, "seed-11.pt")
    elif tamper == "inventory":
        (root / "extra.json").write_text("{}")
    else:
        manifest = json.loads((root / "manifest.json").read_text())
        manifest["files"]["../seed-11.pt"] = manifest["files"].pop("seed-11.pt")
        manifest.pop("content_sha256")
        manifest["content_sha256"] = payload_sha256(manifest)
        (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        run_strategy_scenarios_demo(root, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_causal_boundary_information_and_zero_dose():
    pytest.importorskip("casadi")
    env = StrategyLearningEnv()
    actions = tiny_continuation_reference(env.model, env.model.initial_state(TyreCompound.SOFT)).actions
    received = []
    controller = PlanController(actions, "causal_replan")

    def observe(e, o, m, dose):
        received.append((e.state.lap, dose))
        return controller(e, o, m, dose)

    row = evaluate_scenario(TyreCompound.SOFT, SCENARIOS[3], observe)
    assert row["legal"] and received == [(0, None), (1, .6), (2, None)]
    assert row["event"]["before"]["race_time_s"] == row["event"]["after"]["race_time_s"]
    with pytest.raises(ValueError, match="frozen"):
        evaluate_scenario(TyreCompound.SOFT, Scenario("future", 2, .1), observe)
    with pytest.raises(ValueError, match="Unknown"):
        PlanController(actions, "unknown")


def test_failed_policy_is_preserved():
    pytest.importorskip("casadi")
    row = evaluate_scenario(TyreCompound.SOFT, SCENARIOS[0], lambda e, o, m, d: ([2., 0.], 0))
    assert not row["legal"] and row["failure"] and row["matched_state_regret_s"] is None
    assert row["trajectory"] == []


def test_missing_manifest(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_frozen_run(Path(tmp_path))
