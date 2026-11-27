from pathlib import Path
from runpy import run_path

import pytest


def test_outlap_coverage_excludes_late_peers_and_unreconciled_exit(monkeypatch):
    scripts = Path(__file__).resolve().parents[2] / "research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    observe = run_path(str(scripts / "audit_compound_outlap_support.py"))["observe"]
    row = {"driver": 1, "stints": [1, 2], "forecast_at_s": 200}
    key = (1, 2)
    clocks = {(1, 7): (150, 100)}
    peers = {7: [(2, 149, 80), (3, 150, 82), (4, 199, 84), (5, 201, 50)]}
    result = observe(row, {key: [7]}, {(key, 7): 49}, clocks, peers)
    assert result["exact_exit_s"] is None
    assert result["outlap_relative_s"] == 18
    assert [peer["driver"] for peer in result["peers"]] == [2, 3, 4]
    assert observe({**row, "forecast_at_s": 149}, {key: [7]}, {(key, 7): 100}, clocks, peers) == {
        "reason": "outlap_not_timed_before_cutoff",
        "exact_exit_s": 100,
    }


def test_outlap_forecast_replays_and_rejects_future_input(monkeypatch):
    scripts = Path(__file__).resolve().parents[2] / "research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    study = run_path(str(scripts / "compound_outlap_pace.py"))
    data, control, base = study["load_sources"]()
    saved = study["read_json"](study["FOLDER"] / "compound-v32-development.json")
    study["check_seal"](saved)
    coverage = saved["coverage"]
    replay = study["evaluate"](data, control, base, coverage)
    compare = run_path(str(scripts / "audit_compound_repair.py"))["compare"]
    for key in ("result", "gained_events", "lost_events", "continue_direction"):
        compare(replay[key], saved[key], key)
    first = next(
        row for race in coverage["races"].values() for row in race["records"]
        if row.get("outlap_relative_s") is not None
    )
    first["peers"][0]["end_s"] = data["cases"][first["index"]]["forecast_at_s"] + 1
    poisoned = study["seal"]({key: item for key, item in coverage.items() if key != "content_sha256"})
    with pytest.raises(ValueError, match="exceeds cutoff"):
        study["evaluate"](data, control, base, poisoned)
