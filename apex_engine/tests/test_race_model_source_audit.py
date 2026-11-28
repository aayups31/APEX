from pathlib import Path
from runpy import run_path

import pandas as pd


def test_retirement_exposure_and_saved_calibration(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    scripts = root / "research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    audit = run_path(str(scripts / "audit_race_model_sources.py"))
    source = pd.DataFrame({"Status": ["Retired", "Retired", "Lapped", "Did not start"], "Laps": [0, 4, 8, 0]})
    assert audit["retirement_exposure"](source) == {
        "trials": [3, 11],
        "events": [1, 1],
        "excluded": {"Did not start": 1},
    }
    saved = audit["read_json"](root / "docs/verification/race-model-source-audit.json")
    audit["check_seal"](saved)
    races = saved["races"]
    training = {event: row["retirement"] for event, row in races.items() if event.startswith("F1_2023")}
    held_out = {event: row["retirement"] for event, row in races.items() if event.startswith("F1_2024")}
    assert audit["hazard_score"](training, held_out) == saved["r048_all_cause_baseline"]


def test_pass_proxy_requires_both_drivers_to_be_clean_in_both_laps(monkeypatch):
    scripts = Path(__file__).resolve().parents[2] / "research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    audit = run_path(str(scripts / "audit_race_model_sources.py"))
    laps = pd.DataFrame(
        {
            "DriverNumber": ["1", "2", "1", "2"],
            "LapNumber": [1, 1, 2, 2],
            "Time": pd.to_timedelta([90, 91, 180, 179], unit="s"),
            "TrackStatus": ["1"] * 4,
            "IsAccurate": [True] * 4,
            "PitInTime": [pd.NaT] * 4,
            "PitOutTime": [pd.NaT] * 4,
        }
    )
    assert audit["pass_opportunities"](laps) == {"close_clean_intervals": 1, "timing_line_reversals": 1}
    laps.loc[3, "TrackStatus"] = "6"
    assert audit["pass_opportunities"](laps) == {"close_clean_intervals": 0, "timing_line_reversals": 0}


def test_neutralization_score_excludes_test_race(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    scripts = root / "research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    study = run_path(str(scripts / "fit_neutralization_span.py"))
    saved = study["read_json"](root / "docs/verification/r049-neutralization-span.json")
    study["check_seal"](saved)
    assert study["score"](saved["windows"]) == {k: saved[k] for k in ("metrics", "predictions")}
    assert all(row["event"] not in row["train_events"] for row in saved["predictions"])


def test_drs_history_uses_only_samples_before_line(monkeypatch):
    import numpy as np

    scripts = Path(__file__).resolve().parents[2] / "research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    study = run_path(str(scripts / "fit_traffic_drs_proxy.py"))
    seconds = np.arange(0.0, 12.0, 0.25)
    codes = np.where(seconds >= 10, 12.0, 0.0)
    assert study["drs_history"](seconds, codes, 0, 10) is False
    assert study["drs_history"](seconds, codes, 0, 11.5) is True
