import importlib
from pathlib import Path

import pandas as pd
import pytest

from apexsim.research.fienia_strategy import PaperStrategyAction, PaperStrategyModel, PaperStrategyParameters
from apexsim.research.pit_timing import load_pit_timing
from apexsim.sim_core.types import TyreCompound


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


def test_expanded_calibration_replays_and_refuses_holdout_overlap(study):
    expanded = importlib.import_module("calibrate_pit_expanded")
    parent = expanded.read_json(expanded.PARENT)
    location = expanded.PARENT.with_name("pit-timing-r045-v3.json")
    saved = expanded.read_json(location)
    expanded.check_seal(saved)
    assert saved["parent_sha256"] == parent["content_sha256"]
    added = saved["training_additions"]
    replay = expanded.evaluate(parent, added)
    assert replay == {key: saved[key] for key in replay}
    overlapped = {**parent, "evaluation": {**parent["evaluation"], **added}}
    with pytest.raises(ValueError, match="overlap"):
        expanded.evaluate(overlapped, added)


def test_research_strategy_uses_qualified_pit_components(study):
    evidence = study.BASE / "docs/verification/pit-timing-r045-v3.json"
    timing = load_pit_timing(evidence, "albert_park")
    assert not timing.pooled
    assert timing.inlap_s + timing.outlap_s == timing.total_s
    with pytest.raises(ValueError, match="No circuit-specific"):
        load_pit_timing(evidence, "marina_bay")
    assert load_pit_timing(evidence, "marina_bay", allow_pooled=True).pooled

    params = PaperStrategyParameters(total_laps=4)
    baseline = PaperStrategyModel(params)
    applied = PaperStrategyModel(timing.apply(params))
    initial = baseline.initial_state(TyreCompound.SOFT)
    pit = PaperStrategyAction(params.nominal_fuel_energy_mj(), 0, TyreCompound.HARD)
    drive = PaperStrategyAction(params.nominal_fuel_energy_mj(), 0)
    a, _ = baseline.transition(initial, pit)
    b, _ = applied.transition(initial, pit)
    assert b.last_lap_time_s - a.last_lap_time_s == pytest.approx(timing.inlap_s - params.pit_inlap_penalty_s)
    a, _ = baseline.transition(a, drive)
    b, _ = applied.transition(b, drive)
    assert b.last_lap_time_s - a.last_lap_time_s == pytest.approx(
        timing.outlap_s - params.pit_outlap_penalty_s
    )
    assert b.race_time_s - a.race_time_s == pytest.approx(timing.total_s - params.consecutive_pit_penalty_s)
