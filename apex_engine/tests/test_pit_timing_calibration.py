import importlib
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def study(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "research/scripts"))
    return importlib.import_module("calibrate_pit_timing")


def test_pit_components_use_paired_clocks_and_clean_peers(study):
    rows = []
    for driver in range(1, 5):
        start = driver
        for lap in range(1, 6):
            inlap, outlap = driver == 1 and lap == 4, driver == 1 and lap == 5
            duration = 100 if inlap else 110 if outlap else 90
            end = start + duration
            times = [duration, start, end, end - 5 if inlap else None, start + 10 if outlap else None]
            rows.append(
                (
                    str(driver),
                    lap,
                    2 if outlap else 1,
                    "1",
                    False,
                    not (inlap or outlap),
                    *[pd.to_timedelta(t, unit="s") for t in times],
                )
            )
            start = end
    frame = pd.DataFrame(rows, columns=study.COLUMNS)
    stops, exclusions = study.extract(frame)
    assert not exclusions
    assert len(stops) == 1
    assert [stops[0][k] for k in study.CHANNELS] == [15, 10, 20, 30]
    assert len(stops[0]["peers"]) == 3
    frame.loc[(frame.DriverNumber == "4") & (frame.LapNumber == 5), "TrackStatus"] = "2"
    assert study.extract(frame) == ([], {"insufficient_clean_peers": 1})
    clocks = importlib.import_module("calibrate_pit_clocks")
    assert clocks.extract_clocks(frame) == [
        {"driver": "1", "inlap": 4, "before_line_s": 5, "after_line_s": 10, "lane_s": 15}
    ]


def test_clock_calibration_and_holdout_replay(study):
    clocks = importlib.import_module("calibrate_pit_clocks")
    parent = clocks.read_json(clocks.EVIDENCE)
    saved = clocks.read_json(clocks.EVIDENCE.with_name("pit-timing-r045-v2.json"))
    for doc in (parent, saved):
        clocks.check_seal(doc)
    assert saved["parent_sha256"] == parent["content_sha256"]
    model = clocks.fit(parent["calibration"]["pooled"], saved["training_clocks"])
    assert model == saved["calibration"]
    assert study.score(model, parent["evaluation"]) == saved["result"]
