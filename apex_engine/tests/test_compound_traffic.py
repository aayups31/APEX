from pathlib import Path
from runpy import run_path

import pytest


def test_traffic_forecast_has_bounded_exposure_and_antisymmetric_pace(monkeypatch):
    scripts = Path(__file__).resolve().parents[2]/"research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    predict = run_path(str(scripts/"confirm_compound_traffic.py"))["predict"]
    model = {"traffic_offset": .2, "traffic_slope": .9, "seconds_per_share": 1.,
             "slopes": {"SOFT": .03, "HARD": .02}}
    value, exposure = predict(model, -.4, ("SOFT", "HARD"), (1., 0.))
    reverse, reverse_exposure = predict(model, .4, ("HARD", "SOFT"), (0., 1.))
    assert exposure == [1., .2]
    assert reverse_exposure == exposure[::-1]
    assert value == pytest.approx(-.51)
    assert reverse == pytest.approx(-value)


def test_scope_less_safety_car_deployment_is_global(monkeypatch):
    scripts = Path(__file__).resolve().parents[2]/"research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    normalize = run_path(str(scripts/"confirm_compound_traffic.py"))["normalize_race_control"]
    rows = [{"category": "SafetyCar", "scope": None, "message": "SAFETY CAR DEPLOYED"},
            {"category": "Flag", "scope": "Sector", "message": "YELLOW"}]
    assert normalize(rows) == [{**rows[0], "scope": "Track"}, rows[1]]
    assert rows[0]["scope"] is None
