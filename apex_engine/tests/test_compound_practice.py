import importlib
from datetime import date, datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path
from statistics import median

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_practice_selection_checks_weekend_before_taking_fp2(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    select = importlib.import_module("compound_practice_archive").select_session
    fp1 = {
        "session_type": "Practice",
        "session_name": "Practice 1",
        "year": 2025,
        "meeting_key": 1234,
        "date_end": "2025-05-02T12:00:00+00:00",
    }
    fp2 = {**fp1, "session_name": "Practice 2"}
    day = date(2025, 5, 4)
    assert select([fp1, fp2], 2025, day, 1234) == fp2
    assert select([fp1, {**fp2, "is_cancelled": True}], 2025, day, None) == fp1
    assert select([{**fp2, "date_end": "2025-05-04T23:00:00Z"}], 2025, day, None) is None
    with pytest.raises(ValueError, match="Ambiguous"):
        select([fp1, {**fp2, "meeting_key": 5678}], 2025, day, None)


def test_practice_measures_raw_durations_and_keeps_dry_consecutive_interiors(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    measure = importlib.import_module("compound_practice_trends").measure
    start = datetime(2025, 5, 2, tzinfo=timezone.utc)
    laps = [
        {
            "driver_number": 1,
            "lap_number": i,
            "date_start": (start + timedelta(seconds=100 * i)).isoformat(),
            "lap_duration": 90 + 0.1 * i,
            "is_pit_out_lap": False,
        }
        for i in range(1, 9)
    ]
    tables = {
        "laps": laps,
        "stints": [
            {
                "driver_number": 1,
                "stint_number": 1,
                "lap_start": 1,
                "lap_end": 8,
                "compound": "SOFT",
                "tyre_age_at_start": 0,
            }
        ],
        "weather": [{"date": start.isoformat(), "rainfall": 0}],
        "race_control": [],
    }
    result = measure(tables)
    assert result["SOFT"]["drift_s"] == pytest.approx(0.9)
    assert result["HARD"]["drift_s"] is None
    laps[3]["is_pit_out_lap"] = True
    assert measure(tables)["SOFT"]["drivers"] == 0
    laps[3]["is_pit_out_lap"] = False
    tables["weather"][0]["rainfall"] = 1
    assert measure(tables)["SOFT"]["drivers"] == 0


def test_practice_evidence_rebuilds_driver_slopes_and_forecasts(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    module = importlib.import_module("diagnose_compound_practice")
    trends = module.read_json(module.FOLDER / "compound-v17-practice-trends.json")
    for compounds in trends["events"].values():
        for item in compounds.values():
            by_driver = {}
            for block in item["blocks"]:
                times = block["duration_s"]
                assert len(times) == 6 and max(times) <= 1.07 * min(times)
                slopes = [(t1 - t0) / (j - i) for (i, t0), (j, t1) in combinations(enumerate(times), 2)]
                drift = 9 * median(slopes)
                assert block["drift_s"] == pytest.approx(drift)
                by_driver.setdefault(block["driver"], []).append(drift)
            assert len(by_driver) == item["drivers"]
            if by_driver:
                assert item["drift_s"] == pytest.approx(median(median(group) for group in by_driver.values()))
            else:
                assert item["drift_s"] is None
    saved = module.read_json(module.FOLDER / "compound-v17-development.json")
    module.check_seal(saved)
    actual = module.study()
    assert actual["new_holdout_acquisition_allowed"] == saved["result"]["qualified"]
    assert actual["result"]["failed_events"] == saved["result"]["failed_events"]
    for found, expected in zip(actual["result"]["predictions"], saved["result"]["predictions"], strict=True):
        assert found["laps_s"] == pytest.approx(expected["laps_s"], abs=1e-9, rel=0)
        assert found["crossings"] == expected["crossings"]
