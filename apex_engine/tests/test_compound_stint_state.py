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


def test_compound_transfer_reverses_driver_order_and_excludes_test_race(scripts):
    study = importlib.import_module("diagnose_compound_driver_transfer")
    row = {"compounds": ["HARD", "MEDIUM"], "prior": 0.3, "prefix": 0.5, "target": 0.8}
    reversed_row = {**row, "compounds": ["MEDIUM", "HARD"], "target": -100}
    folds = study.score({"train": [row], "test": [reversed_row]})
    scored = folds["test"]["predictions"][0]
    assert scored["training_race_medians"] == {"train": 0.5}
    assert scored["prediction"] == pytest.approx(-0.2)
    assert study.score({"only": [row]})["only"]["fallback_cases"] == 1


def test_saved_peer_forecasts_use_completed_other_driver_laps_and_exact_fallback(scripts):
    engine, _ = scripts
    data = engine.read_json(engine.FOLDER / "compound-v24-cohort.json")
    saved = engine.read_json(engine.FOLDER / "compound-v27-development.json")
    baseline = engine.read_json(engine.FOLDER / "compound-v24-development.json")
    for doc in (saved, data, baseline):
        engine.check_seal(doc)
    assert saved["dataset_sha256"] == data["content_sha256"] == baseline["dataset_sha256"]
    assert saved["control_sha256"] == baseline["content_sha256"]
    model = importlib.import_module("compound_causal_peer")
    assert saved["source_sha256_lf"] == model.canonical_file_sha(Path(model.__file__))
    control = baseline["results"]["nomination_practice_ridge"]
    fallback = {p["index"]: (p["laps_s"], p["bounded_laps"]) for p in control["predictions"]}
    forecasts = {
        i: model.predict(row, saved["contributors"][str(i)], fallback[i])
        for i, row in enumerate(data["cases"])
    }
    engine.compare(engine.score_forecasts(data["cases"], data["sources"], forecasts), saved["result"])
    row = data["cases"][0]
    with pytest.raises(ValueError, match="Ineligible"):
        model.predict(
            row, [{"driver": -1, "available_at_s": row["forecast_at_s"] + 1, "prior_laps": 12}], fallback[0]
        )
