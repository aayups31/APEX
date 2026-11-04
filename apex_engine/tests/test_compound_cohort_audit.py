import importlib
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from apexsim.provenance import write_manifest


def test_full_cohort_enumeration_flags_age_gaps_and_missing_case(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/"research/scripts"))
    audit = importlib.import_module("audit_compound_cohort")
    base = datetime(2025, 4, 6, tzinfo=UTC).timestamp()
    tables = {"laps": [dict(driver_number=4, lap_number=lap, is_pit_out_lap=False,
                  lap_duration=95.-.042*(lap-1), date_start=datetime.fromtimestamp(base+100*lap, UTC).isoformat())
                for lap in range(1, 31)],
              "stints": [dict(driver_number=4, compound=c, tyre_age_at_start=0,
                             lap_start=start, lap_end=start+14, stint_number=i)
                         for i, (c, start) in enumerate((("SOFT", 1), ("HARD", 16)), 1)],
              "race_control": [dict(scope="Track", flag="CLEAR", date=datetime.fromtimestamp(base, UTC).isoformat())],
              "weather": [dict(date=datetime.fromtimestamp(base, UTC).isoformat(), rainfall=0)]}
    cases, report = audit.enumerate_cases(tables, 10006)
    assert len(cases) == 1 and report["pairs"][0]["maximum_common_run"] == 13
    data = {"cases": [{**cases[0], "context": {}}]}
    audit.compare_published(data, "10006", report, cases, report)
    with pytest.raises(ValueError, match="missing/extra"):
        audit.compare_published({"cases": []}, "10006", report, cases, report)
    bad = deepcopy(tables)
    bad["laps"][6]["is_pit_out_lap"] = True
    none, gaps = audit.enumerate_cases(bad, 10006)
    assert not none and gaps["pairs"][0]["maximum_common_run"] == 7
    assert gaps["pairs"][0]["disposition"] == "COMMON_AGE_RUN_SHORTER_THAN_TWELVE"
    duplicate = deepcopy(tables)
    duplicate["laps"].append(duplicate["laps"][0])
    with pytest.raises(ValueError, match="duplicate driver/lap"):
        audit.enumerate_cases(duplicate, 10006)


def test_full_fastf1_cohort_quality_gaps_and_benchmark_guard(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/"research/scripts"))
    audit = importlib.import_module("audit_compound_cohort")
    root = tmp_path/"native"
    (root/"tables").mkdir(parents=True)
    write_manifest(root/"manifest.json", {"query": {"year": 2024, "round_number": 1, "session": "R"}})
    monkeypatch.setattr(audit, "verify_fastf1_archive", lambda _: {"content_sha256": "fixture"})
    laps = np.arange(1, 31)
    base = pd.Timestamp("2024-03-02T15:00:00")
    frame = pd.DataFrame({"DriverNumber": ["4"]*30, "LapNumber": laps,
                          "Stint": [1]*15+[2]*15, "Compound": ["SOFT"]*15+["HARD"]*15,
                          "TyreLife": list(range(1, 16))*2,
                          "LapTime": pd.to_timedelta(95.-.042*(laps-1), unit="s"),
                          "IsAccurate": [True]*30, "Deleted": [False]*30, "TrackStatus": ["1"]*30,
                          "PitInTime": [pd.NaT]*30, "PitOutTime": [pd.NaT]*30,
                          "LapStartTime": pd.to_timedelta(100*laps, unit="s"),
                          "LapStartDate": base+pd.to_timedelta(100*laps, unit="s")})
    frame.to_parquet(root/"tables/laps.parquet", index=False)
    pd.DataFrame({"Time": pd.to_timedelta([0], unit="s"), "Rainfall": [False]}).to_parquet(root/"tables/weather_data.parquet", index=False)
    rows, report = audit.enumerate_fastf1(root, "F1_2024_R01")
    assert len(rows) == 1 and report["pairs"][0]["maximum_common_run"] == 15
    assert rows[0]["forecast_at_s"] == base.tz_localize("UTC").timestamp()+1800+95-.042*17
    frame.loc[6, "TrackStatus"] = "2"
    frame.to_parquet(root/"tables/laps.parquet", index=False)
    assert not audit.enumerate_fastf1(root, "F1_2024_R01")[0]
    (root/"manifest.json").unlink()
    write_manifest(root/"manifest.json", {"query": {"year": 2024, "round_number": 4, "session": "R"}})
    monkeypatch.setattr(audit, "verify_fastf1_archive", lambda _: pytest.fail("Reserved payload accessed"))
    with pytest.raises(ValueError, match="Permanent benchmark"):
        audit.enumerate_fastf1(root, "F1_2024_R04")
