import importlib
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from apexsim.provenance import write_manifest
from apexsim.research.evidence import seal


def load_script(monkeypatch, name):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/"research/scripts"))
    return importlib.import_module(name)


def test_nested_selection_cannot_see_outer_targets(monkeypatch):
    study = load_script(monkeypatch, "diagnose_compound_bounded")
    rows = []
    for event in range(4):
        for driver in range(6):
            compound = ("SOFT", "MEDIUM", "HARD")[driver % 3]
            actual = .6 if driver < 3 else -.6
            rows.append(dict(session=event, driver=driver, stints=[1, 2], ages=list(range(2, 14)),
                             compounds=["HARD" if compound == "SOFT" else "SOFT", compound],
                             current_prefix_s=[90., 90.1, 90.2], reference_target_s=[91., 91.1, 91.2],
                             current_target_s=[91.-actual, 91.1-actual, 91.2-actual],
                             prefix_s=-.2, pairwise_prefix_s=-.3, actual_s=actual, pairwise_actual_s=actual,
                             reference_end_s=100., forecast_at_s=200.))
    settings = [dict(baseline="reference", group="pace", alpha=10., bound_s=cap) for cap in (0., .25)]
    binding = study.source_hashes()
    result = study.compare(seal({"cases": rows, "implementation_sha256_lf": binding}),
                           settings=settings, cs=(.1,), thresholds=(.5,), tree=False)
    altered = deepcopy(rows)
    for row in altered:
        if row["session"] == 0:
            row.update(actual_s=99., pairwise_actual_s=99., current_target_s=[200.]*3)
    changed = study.compare(seal({"cases": altered, "implementation_sha256_lf": binding}),
                            settings=settings, cs=(.1,), thresholds=(.5,), tree=False)
    original = [r for r in result["nested_predictions"] if r["session"] == 0]
    mutated = [r for r in changed["nested_predictions"] if r["session"] == 0]
    for a, b in zip(original, mutated, strict=True):
        for field in ("predicted_s", "lower_s", "upper_s", "crossover_score", "predicted_crossover"):
            assert a[field] == b[field]
    for field in ("setting", "event_head", "radius_s", "training_events"):
        assert result["outer_folds"][0][field] == changed["outer_folds"][0][field]
    assert not result["candidate_accepted"] and not result["production_promotion"]
    for fold in result["outer_folds"]:
        assert fold["event"] not in fold["training_events"]
    assert result["outer_folds"][0]["pace"] != changed["outer_folds"][0]["pace"]
    auditor = load_script(monkeypatch, "audit_compound_bounded")
    data = seal({"cases": rows, "implementation_sha256_lf": binding})
    assert auditor.audit(data, result)["cases_audited"] == len(rows)
    corrupted = deepcopy(result)
    corrupted["nested_predictions"][0]["predicted_s"] += .1
    corrupted = seal({k: v for k, v in corrupted.items() if k != "content_sha256"})
    with pytest.raises(ValueError, match="predicted_s"):
        auditor.audit(data, corrupted)
    corrupted = deepcopy(result)
    corrupted["nested_macro_pace"][0]["mae_s"] += .1
    corrupted = seal({k: v for k, v in corrupted.items() if k != "content_sha256"})
    with pytest.raises(ValueError, match="macro/"):
        auditor.audit(data, corrupted)


def test_fastf1_context_utc_alignment_future_weather_and_benchmark_guard(tmp_path, monkeypatch):
    study = load_script(monkeypatch, "prepare_compound_bounded")
    native = load_script(monkeypatch, "compound_multiseason")
    monkeypatch.setattr(study, "BASE", tmp_path)
    monkeypatch.chdir(tmp_path)
    root = tmp_path/"native"
    (root/"tables").mkdir(parents=True)
    calendar = tmp_path/".cache/jolpica-2024-20260916"
    calendar.mkdir(parents=True)
    write_manifest(root/"manifest.json", {"query": {"year": 2024, "round_number": 1, "session": "R"}})
    write_manifest(calendar/"events.json", {"events": [dict(season=2024, round_number=1,
                   event_id="F1_2024_R01", circuit_id="fixture", race_date="2024-03-02")]})
    for module in (study, native):
        monkeypatch.setattr(module, "verify_fastf1_archive", lambda p: {"content_sha256": "fixture"})
        monkeypatch.setattr(module, "verify_jolpica_archive", lambda p: {"content_sha256": "calendar"})
    laps = np.arange(1, 31)
    base = pd.Timestamp("2024-03-02T15:00:00")
    frame = pd.DataFrame({"DriverNumber": ["4"]*30, "LapNumber": laps, "Stint": [1]*15+[2]*15,
                          "Compound": ["SOFT"]*15+["HARD"]*15, "TyreLife": list(range(1, 16))*2,
                          "LapTime": pd.to_timedelta(95.-.042*(laps-1), unit="s"),
                          "IsAccurate": [True]*30, "Deleted": [False]*30, "TrackStatus": ["1"]*30,
                          "PitInTime": [pd.NaT]*30, "PitOutTime": [pd.NaT]*30,
                          "LapStartTime": pd.to_timedelta(100*laps, unit="s"),
                          "LapStartDate": base+pd.to_timedelta(100*laps, unit="s")})
    frame.to_parquet(root/"tables/laps.parquet", index=False)
    weather = pd.DataFrame({"Time": pd.to_timedelta([0, 1850, 2000], unit="s"),
                            "Rainfall": [False]*3, "TrackTemp": [30., 32., 100.]})
    weather.to_parquet(root/"tables/weather_data.parquet", index=False)
    rows, _ = native.fastf1_cases(root)
    result = study.fastf1_context(root, rows)
    assert result[0]["context"]["track_temperature_c"] == 32.
    assert result[0]["context"]["weather_at_s"] == base.tz_localize("UTC").timestamp()+1850
    weather.loc[2, "TrackTemp"] = -9999.
    weather.to_parquet(root/"tables/weather_data.parquet", index=False)
    assert study.fastf1_context(root, rows) == result
    # The guard precedes native payload verification/access even in enrichment.
    metadata = root/"manifest.json"
    metadata.unlink()
    write_manifest(metadata, {"query": {"year": 2024, "round_number": 4, "session": "R"}})
    monkeypatch.setattr(study, "verify_fastf1_archive", lambda p: pytest.fail("Reserved payload accessed"))
    with pytest.raises(ValueError, match="Permanent benchmark"):
        study.fastf1_context(root, rows)
