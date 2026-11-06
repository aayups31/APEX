import importlib
from pathlib import Path

from apexsim.research.evidence import read_json


def test_monza_contradiction_and_independent_lap_outputs(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root/"research/scripts"))
    trial = importlib.import_module("diagnose_compound_decision")
    # The median difference can change sign when lap order changes.
    assert trial.contrasts([90., 91., 94.], [93., 90., 92.]) == (-1., 1.)
    data = read_json(root/"docs/verification/compound-v10-development-data.json")
    result = trial.study(data)
    assert result["impossible_shared_decision_events"] == [
        {"event": "F1_2024_R16", "observed": [1, 0], "cases": 13}]
    assert len(result["predictions"]) == 392
    assert not result["development_qualified"] and not result["new_holdout_acquisition_allowed"]
    assert all(m["passed"] for event in result["events"] for m in event["oracle"])


def test_forecast_race_cannot_modify_own_calibrated_drift(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root/"research/scripts"))
    trial = importlib.import_module("diagnose_compound_decision")
    rows = read_json(root/"docs/verification/compound-v10-development-data.json")["cases"]
    before = trial.calibration(rows, "F1_2024_R16", "HARD")
    modified = [{**row, "current_target_s": [999.]*3} if row["session"] == "F1_2024_R16" else row for row in rows]
    assert trial.calibration(modified, "F1_2024_R16", "HARD") == before
