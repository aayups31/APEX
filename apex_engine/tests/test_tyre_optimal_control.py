import pytest

from apexsim.research.evidence import check_seal, read_json, verify_inventory
from apexsim.research.tyre_optimal_control import (
    REPLACEMENT,
    VERSION,
    Strategy,
    reference_lap,
    rollout,
    run_study,
    verify_study,
)


def test_pit_replaces_both_temperatures_and_wear():
    plan = Strategy(("conserve",) * 4, 2, "hard")
    laps = rollout(plan, reference_lap)["laps"]
    assert laps[0]["final"]["wear"] > 0.14
    assert laps[1]["initial"] == {
        "tread_k": REPLACEMENT.tread_k,
        "carcass_k": REPLACEMENT.carcass_k,
        "wear": 0.0,
    }
    assert laps[1]["compound"] == "hard"
    assert laps[2]["initial"] == laps[1]["final"]
    with pytest.raises(ValueError, match="Invalid synthetic tyre strategy"):
        rollout(Strategy(plan.efforts, 2), reference_lap)


def test_benchmark_replays_every_strategy_and_seals_run(tmp_path):
    path = tmp_path / "r042"
    summary = run_study(path)
    check_seal(summary)
    receipt = verify_inventory(path, VERSION)
    assert receipt["summary_sha256"] == summary["content_sha256"]
    traces = read_json(path / "trajectories.json")
    catalog = [r["strategy"] for r in traces["reference"]]
    assert len(catalog) == 112
    for mesh in traces["meshes"].values():
        assert [r["strategy"] for r in mesh] == catalog
    for choice in summary["choices"]:
        loss = choice["pit_loss_s"]
        scored = [
            r["time_without_pit_loss_s"] + loss * (r["strategy"]["pit_before_lap"] is not None)
            for r in traces["reference"]
        ]
        assert choice["reference_time_s"] == min(scored)
        assert choice["reference_index"] == scored.index(min(scored))
    assert summary["passed"]
    assert summary["choices"][0]["mesh_strategy"]["pit_before_lap"] is not None
    assert summary["choices"][1]["mesh_strategy"]["pit_before_lap"] is None
    replay = verify_study(path)
    check_seal(replay)
    assert replay["verified"] and replay["passed"]
    assert replay["summary_sha256"] == summary["content_sha256"]
    assert replay["integration_count"] == 5
    with pytest.raises(FileExistsError):
        run_study(path)
    with (path / "trajectories.json").open("a", encoding="utf-8") as artifact:
        artifact.write(" ")
    with pytest.raises(ValueError, match="inventory/hash mismatch"):
        verify_study(path)
