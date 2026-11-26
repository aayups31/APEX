import importlib
from pathlib import Path

import pytest


@pytest.fixture
def scripts(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "research/scripts"))
    return importlib.import_module("compound_stint_state"), importlib.import_module(
        "audit_compound_driver_control"
    )


def test_forecast_is_independent_of_future_target_and_heldout_prior(scripts):
    model, _ = scripts
    row = model.read_json(model.FOLDER / "compound-v24-cohort.json")["cases"][0]
    compound = row["compounds"][1]
    training = {(event, compound, 4, 1, (1,)): (0.05, 0.3) for event in ("a", "b", "c")}
    prior = model.train_prior(training, "held", compound)
    training["held", compound, 8, 1, (1,)] = (25.0, 50.0)
    assert model.train_prior(training, "held", compound) == prior
    forecast = model.forecast(row, prior, asymmetric=True)
    assert model.forecast({**row, "current_target_s": [900] * 3}, prior, asymmetric=True) == forecast


def test_controls_exclude_future_duplicate_and_either_current_stint(scripts):
    _, controls = scripts
    pool = [(1, 2, 1, 1, 0.2), (1, 3, 1, 1, 99), (4, 5, 2, 3, 1), (6, 7, 4, 2, 2), (8, 9, 1, 1, 99)]
    assert controls.prior_differences(pool, 9, (2, 2)) == [0.2]
    assert controls.prior_differences(pool, 9, None) == [0.2, 1, 2]
