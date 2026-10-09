import json

import pytest

from apexsim.examples.sac_strategy_demo import evaluate_strategy, profile_settings, run_sac_strategy_demo
from apexsim.provenance import file_sha256, payload_sha256
from apexsim.sim_core.types import TyreCompound


def test_frozen_profiles():
    research = profile_settings("research")
    assert [s.seed for s in research] == [11, 23, 37] and all(s.steps == 12000 for s in research)
    assert profile_settings("smoke")[0].steps == 300
    with pytest.raises(ValueError):
        profile_settings("unknown")


def test_illegal_policy_attempt_is_counted():
    result = evaluate_strategy(TyreCompound.MEDIUM, lambda e, o, m: ([2., 0.], 0), 300.)
    assert not result["legal"] and result["regret_s"] is None and result["failure"]


def test_smoke_artifacts_weights_and_manifest(tmp_path):
    pytest.importorskip("casadi")
    output = tmp_path / "smoke"
    summary = run_sac_strategy_demo(output, "smoke")
    assert summary["training_steps"] == 300 and summary["training_episodes"] == 100
    assert summary["evaluation_attempts"] == summary["legal_evaluation_episodes"] == 3
    assert summary["checkpoint_reload_action_parity"] and not summary["promotion_recommended"]
    assert summary["mean_regret_s"] >= -1e-6
    training = json.loads((output / "training.json").read_text())[0]
    assert training["updates"] == 236 and training["actor_parameter_change_l2"] > 0
    manifest = json.loads((output / "manifest.json").read_text())
    digest = manifest.pop("content_sha256")
    assert digest == payload_sha256(manifest)
    assert manifest["summary_sha256"] == summary["content_sha256"]
    assert "seed-11.pt" in manifest["files"]
    for name, record in manifest["files"].items():
        assert record["sha256"] == file_sha256(output / name)
    with pytest.raises(FileExistsError):
        run_sac_strategy_demo(output, "smoke")


def test_bad_profile_leaves_no_output(tmp_path):
    output = tmp_path / "bad"
    with pytest.raises(ValueError):
        run_sac_strategy_demo(output, "bad")
    assert not output.exists()
