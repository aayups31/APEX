import importlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from apexsim.provenance import write_manifest


@pytest.fixture
def native_source(tmp_path, monkeypatch):
    scripts = Path(__file__).resolve().parents[2]/"research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    module = importlib.import_module("compound_multiseason")
    monkeypatch.chdir(tmp_path)
    root = tmp_path/"native"
    (root/"tables").mkdir(parents=True)
    calendar = tmp_path/".cache/jolpica-2024-20260916"
    calendar.mkdir(parents=True)
    write_manifest(root/"manifest.json", {"query": {"year": 2024, "round_number": 1, "session": "R"}})
    write_manifest(calendar/"events.json", {"events": [dict(season=2024, round_number=1,
                   event_id="F1_2024_R01", circuit_id="fixture", race_date="2024-03-02")]})
    # Archive verifiers have their own integrity tests. This fixture isolates
    # native time conversion, weather exclusion and preservation of age gaps.
    monkeypatch.setattr(module, "verify_fastf1_archive", lambda p: {"content_sha256": "fixture"})
    monkeypatch.setattr(module, "verify_jolpica_archive", lambda p: {"content_sha256": "fixture-calendar"})
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
    pd.DataFrame({"Time": pd.to_timedelta([0], unit="s"), "Rainfall": [False]}).to_parquet(
        root/"tables/weather_data.parquet", index=False)
    return module, root, frame, base


def test_multiseason_native_utc_clock_and_corrected_pace(native_source):
    module, root, _, base = native_source
    rows, source = module.fastf1_cases(root)
    assert len(rows) == source["blocks"] == 1
    row = rows[0]
    assert row["forecast_at_s"] == pytest.approx(base.tz_localize("UTC").timestamp()+1800+95-.042*17)
    assert row["reference_end_s"] < row["forecast_at_s"]
    assert row["current_prefix_s"] == pytest.approx([91.85]*3)
    assert row["actual_s"] == pytest.approx(0., abs=1e-12)


@pytest.mark.parametrize("exclusion", ["rain", "yellow"])
def test_multiseason_never_bridges_invalid_context(native_source, exclusion):
    module, root, frame, _ = native_source
    if exclusion == "rain":
        pd.DataFrame({"Time": pd.to_timedelta([0, 1000, 1600], unit="s"),
                      "Rainfall": [False, True, False]}).to_parquet(root/"tables/weather_data.parquet", index=False)
    else:
        frame.loc[7, "TrackStatus"] = "2"
        frame.to_parquet(root/"tables/laps.parquet", index=False)
    rows, source = module.fastf1_cases(root)
    assert rows == [] and source["unsupported_pairs"] == 1


def test_multiseason_benchmark_guard_precedes_native_reads(tmp_path, monkeypatch):
    scripts = Path(__file__).resolve().parents[2]/"research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    module = importlib.import_module("compound_multiseason")
    write_manifest(tmp_path/"manifest.json", {"query": {"year": 2024, "round_number": 4, "session": "R"}})
    monkeypatch.setattr(module, "verify_fastf1_archive", lambda p: pytest.fail("Benchmark archive read"))
    with pytest.raises(ValueError, match="Permanent benchmark"):
        module.fastf1_cases(tmp_path)


def test_frozen_text_hash_is_portable_but_detects_content_change(tmp_path, monkeypatch):
    scripts = Path(__file__).resolve().parents[2]/"research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    module = importlib.import_module("confirm_compound_multiseason")
    first, second = tmp_path/"lf.json", tmp_path/"crlf.json"
    first.write_bytes(b'{\n  "value": 1\n}\n')
    second.write_bytes(b'{\r\n  "value": 1\r\n}\r\n')
    assert module.canonical_file_sha(first) == module.canonical_file_sha(second)
    second.write_bytes(b'{\r\n  "value": 2\r\n}\r\n')
    assert module.canonical_file_sha(first) != module.canonical_file_sha(second)
