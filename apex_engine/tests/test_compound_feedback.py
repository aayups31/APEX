import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_feedback_waits_for_witness_and_ignores_subject_driver(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    module = importlib.import_module("diagnose_compound_feedback")
    rows = [
        {
            "driver": d,
            "stints": [1, 2],
            "ages": list(range(12)),
            "compounds": ["SOFT", c],
            "current_prefix_s": [90] * 3,
            "current_target_s": [91] * 3,
            "forecast_at_s": time,
        }
        for d, c, time in [
            (1, "HARD", 0),
            (1, "HARD", 0),
            (2, "HARD", 20),
            (3, "HARD", 21),
            (1, "HARD", 22),
            (4, "MEDIUM", 23),
        ]
    ]
    base = {i: {"laps_s": [90] * 3} for i in range(len(rows))}
    base[1] = {"laps_s": [91] * 3}
    clocks = [{"target_ends": [10, 11, 12], "release_s": 20}] * 2 + [{"release_s": None}] * 4
    forecasts, peers = module.race_forecasts(rows, base, clocks, range(len(rows)))
    assert forecasts[2][0] == [90] * 3
    assert forecasts[3][0] == [90.125] * 3
    assert peers[3]["peer_windows"] == [[0, 1]]
    assert peers[4]["peer_windows"] == peers[5]["peer_windows"] == []
    rows[3]["current_target_s"] = [1234] * 3
    assert module.race_forecasts(rows, base, clocks, range(len(rows)))[0] == forecasts


def test_feedback_replays_and_diagnostic_never_promotes(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    module = importlib.import_module("diagnose_compound_feedback")
    actual = module.study()
    saved = module.read_json(module.FOLDER / "compound-v16-development.json")
    module.check_seal(saved)
    assert actual["result"]["failed_events"] == saved["result"]["failed_events"]
    assert actual["feedback"] == saved["feedback"]
    for found, expected in zip(actual["result"]["predictions"], saved["result"]["predictions"], strict=True):
        assert found["laps_s"] == pytest.approx(expected["laps_s"], rel=0, abs=1e-9)
    assert (
        actual["supported_case_oracle_diagnostic"]["failed_events"]
        == saved["supported_case_oracle_diagnostic"]["failed_events"]
    )
    assert actual["new_holdout_acquisition_allowed"] == actual["result"]["qualified"]
