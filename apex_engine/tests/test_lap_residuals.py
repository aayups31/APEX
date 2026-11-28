from pathlib import Path
from random import Random
from runpy import run_path
from statistics import mean

import pytest

from apexsim.research.evidence import read_json
from apexsim.research.lap_residuals import COMPOUNDS, load_lap_residuals


def test_qualified_lap_residual_model_replays_and_samples():
    root = Path(__file__).resolve().parents[2]
    path = root / "docs/verification/lap-residuals-r046-v1.json"
    model = load_lap_residuals(path)
    evidence = read_json(path)
    folds = evidence["calibration_races"]
    assert all(race not in training for race, training in folds.items())
    for race, rows in evidence["forecasts"].items():
        assert race not in folds
        row = rows[0]
        d1, d2, age, lap, *compounds = row["features"]
        compound = COMPOUNDS[compounds.index(1)]
        last = row["last_s"]
        prefix = (last - d2 - d1, last - d2, last)
        forecast = model.forecast(row["driver"], prefix, tyre_age=age, lap=lap, compound=compound)
        assert forecast.point_s == pytest.approx(row["arms"]["ridge"]["point_s"])
        assert bool(forecast.driver_residuals) == row["arms"]["ridge"]["driver_specific"]
        rng1, rng2 = Random(46), Random(46)
        assert [forecast.sample(rng1) for _ in range(10)] == [forecast.sample(rng2) for _ in range(10)]
        assert not model.forecast(
            "unknown", prefix, tyre_age=age, lap=lap, compound=compound
        ).driver_residuals


def test_indexed_empirical_crps_matches_pairwise_definition(monkeypatch):
    scripts = Path(__file__).resolve().parents[2] / "research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    sc = run_path(str(scripts / "fit_lap_residuals.py"))
    samples = [-2, -0.3, 0, 0.1, 2, 2.5]
    index = sc["empirical_index"](samples)
    for actual in (-9, -0.3, 0.5, 12):
        direct = (
            mean(abs(s - actual) for s in samples) - mean(abs(a - b) for a in samples for b in samples) / 2
        )
        assert sc["empirical_score"](index, actual) == pytest.approx(direct)
