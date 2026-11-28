from pathlib import Path
from runpy import run_path

import numpy as np
import pandas as pd
import pytest

from apexsim.provenance import write_manifest
from apexsim.research.evidence import read_json, seal
from apexsim.research.green_traffic import (
    GreenTrafficReplay,
    fit_green_traffic,
    load_green_traffic_replay,
    load_sector_traffic_calibration,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "research/scripts"
EVIDENCE = ROOT / "docs/verification"


def test_fit_and_prediction_round_trip_with_unavailable_drs():
    def sample(passed, drs):
        return {
            "gap_s": 0.6,
            "pace_delta_s": -0.5,
            "prior_drs": drs,
            "next_gap_s": -0.2 if passed else 0.7,
            "pass": passed,
        }

    rows = [sample(True, True)] * 30 + [sample(False, False)] * 40 + [sample(False, None)] * 4
    fitted = fit_green_traffic(rows, use_prior_drs=True)
    replay = GreenTrafficReplay.from_dict(fitted.to_dict())
    open_wing = replay.forecast(0.6, -0.5, True)
    closed_wing = replay.forecast(0.6, -0.5, False)
    unknown = replay.forecast(0.6, -0.5)
    assert closed_wing.corroborated_pass_probability < unknown.corroborated_pass_probability
    assert unknown.corroborated_pass_probability < open_wing.corroborated_pass_probability
    assert unknown == fitted.forecast(0.6, -0.5)
    assert replay.forecast(1.6, 0.5).corroborated_pass_probability == replay.pooled_pass_probability
    with pytest.raises(ValueError, match="starting gap"):
        replay.forecast(2.01, 0.0)
    with pytest.raises(ValueError, match="Invalid"):
        GreenTrafficReplay.from_dict({**fitted.to_dict(), "pass_cells": {"999": 0.5}})


def test_reversal_requires_timestamped_same_pair_corroboration_and_nonpit_laps(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    study = run_path(str(SCRIPTS / "fit_green_traffic_r050.py"))
    rows = []
    for lap, clocks in ((2, (90, 91)), (3, (180, 181)), (4, (270, 269))):
        for driver, second in zip(("1", "2"), clocks, strict=True):
            rows.append(
                dict(
                    DriverNumber=driver,
                    LapNumber=lap,
                    Time=pd.Timedelta(second, unit="s"),
                    LapStartTime=pd.Timedelta(second - 90, unit="s"),
                    LapTime=pd.Timedelta(90, unit="s"),
                    TyreLife=float(lap),
                    Stint=1.0,
                    TrackStatus="1",
                    IsAccurate=True,
                    PitInTime=pd.NaT,
                    PitOutTime=pd.NaT,
                    Deleted=False,
                    FastF1Generated=False,
                )
            )
    overtakes = [
        {"date": "1970-01-01T00:03:20+00:00", "overtaken_driver_number": 1, "overtaking_driver_number": 2},
    ]
    extract = study["extract"]
    (positive,), _ = extract(pd.DataFrame(rows), {}, overtakes, 0)
    (unconfirmed,), _ = extract(pd.DataFrame(rows), {}, [], 0)
    assert positive["pass"] and positive["next_gap_s"] == -1
    assert not unconfirmed["pass"] and unconfirmed["next_gap_s"] == -1
    rows[-1]["PitOutTime"] = pd.Timedelta(200, unit="s")
    assert extract(pd.DataFrame(rows), {}, overtakes, 0)[0] == []


def test_sector_drs_unknown_or_brief_activity_cannot_be_treated_as_closed(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    sector_drs = run_path(str(SCRIPTS / "fit_sector_traffic_r050.py"))["sector_drs"]
    seconds = np.arange(0.0, 10.0, 0.25)
    codes = np.zeros(len(seconds))
    assert sector_drs((seconds, codes), 0, 10) is False
    codes[10] = 10
    assert sector_drs((seconds, codes), 0, 10) is None
    codes[10:18] = 14
    assert sector_drs((seconds, codes), 0, 10) is True
    codes[:18] = 99
    assert sector_drs((seconds, codes), 0, 10) is None
    seconds = np.arange(0.0, 30.0, 0.25)
    seconds = seconds[(seconds < 5.0) | (seconds >= 6.25)]
    assert sector_drs((seconds, np.zeros(len(seconds))), 0, 30) is None


def test_load_qualified_scoped_calibrations(tmp_path):
    forecast = load_green_traffic_replay(EVIDENCE / "r050-green-traffic.json")
    assert not forecast.use_prior_drs
    assert (
        forecast.forecast(0.5, -0.2).corroborated_pass_probability
        > forecast.forecast(0.5, 0.2).corroborated_pass_probability
    )
    sector_path = EVIDENCE / "r050-sector-traffic.json"
    sector = load_sector_traffic_calibration(sector_path)
    assert sector.adjustment(0.7, drs_open=False) == pytest.approx(0.3455)
    assert sector.adjustment(0.7, drs_open=True) == pytest.approx(0.3455 - 0.28725)
    assert sector.adjustment(2.0, drs_open=False) == 0
    for gap, drs in ((1.5, False), (2.0, True), (0.0, False)):
        with pytest.raises(ValueError, match="outside calibrated"):
            sector.adjustment(gap, drs_open=drs)

    rejected = read_json(sector_path)
    rejected.pop("content_sha256")
    rejected["gates"]["drs"]["confirmation_score"] = False
    path = tmp_path / "rejected.json"
    write_manifest(path, seal(rejected))
    with pytest.raises(ValueError, match="No qualified"):
        load_sector_traffic_calibration(path)
