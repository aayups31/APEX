import importlib
from pathlib import Path

import pytest


@pytest.fixture
def field_model(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "research/scripts"))
    return importlib.import_module("compound_field_evolution")


def stint(driver, ages, *, shift=0):
    return {
        "driver": driver,
        "stint": 1,
        "compound": "HARD",
        "ends": {age: age * 90 + shift for age in ages},
        "values": {age: 85 + age / 10 for age in ages},
    }


def test_field_cutoff_excludes_self_gaps_stale_and_future_laps(field_model):
    field = [
        stint(1, range(1, 19)),
        stint(2, range(1, 19)),
        stint(3, [1, 2, 4, 5, 6, 7]),
        stint(4, range(1, 7), shift=-61),
    ]
    index = field_model.index_field(field)
    peers = field_model.snapshot(index, 1, 630)
    assert set(peers) == {2}
    assert peers[2]["end"] == 630
    assert peers[2]["change"] == pytest.approx(0.3)
    row = {
        "driver": 1,
        "stints": [0, 1],
        "compounds": ["MEDIUM", "HARD"],
        "ages": list(range(5, 17)),
        "forecast_at_s": 630,
        "current_history": [{"end_s": 630}],
        "reference_history": [{"end_s": 90 * n} for n in range(1, 7)],
    }
    current = field_model.causal_context(index, row)
    future = field_model.future_field_diagnostic(index, row)
    for age in range(8, 19):
        field[1]["values"][age] += 7
    assert field_model.causal_context(index, row) == current
    after = field_model.future_field_diagnostic(index, row)
    assert after[1] == future[1] == [1, 1]
    assert after[0][0] - future[0][0] == pytest.approx(7)
    del field[1]["ends"][9]
    assert field_model.future_field_diagnostic(field_model.index_field(field), row)[1] == [0, 0]


def test_field_replay_from_saved_causal_inputs(field_model):
    data, result, nominations, practice, control = [
        field_model.read_json(field_model.FOLDER / f"compound-{name}.json")
        for name in (
            "v24-cohort",
            "v28-development",
            "v21-nominations",
            "v17-practice-trends",
            "v24-development",
        )
    ]
    for doc in (data, result, nominations, practice, control):
        field_model.check_seal(doc)
    assert result["source_sha256_lf"] == field_model.canonical_file_sha(Path(field_model.__file__))
    assert result["dataset_sha256"] == data["content_sha256"] == control["dataset_sha256"]
    assert result["control_sha256"] == control["content_sha256"]
    assert result["protocol_sha256_lf"] == field_model.canonical_file_sha(
        field_model.BASE / "research/protocols/COMPOUND_FIELD_EVOLUTION_V28.md"
    )
    allocation = {
        event: (source["issued"], codes)
        for source in nominations["sources"]
        for event, codes in source["events"].items()
    }
    matrix = []
    for row, context in zip(data["cases"], result["contexts"], strict=True):
        assert len(context["causal"]) == 18
        matrix.append(field_model.base_vector(row, allocation, practice["events"]) + context["causal"])
    replay = field_model.score(data, matrix)
    field_model.compare(replay["predictions"], result["result"]["predictions"])
    field_model.compare(replay["folds"], result["result"]["folds"])
    assert replay["qualified"] == result["development_qualified"] == result["new_holdout_acquisition_allowed"]


def test_predicted_field_replays_and_excludes_entire_test_race(field_model, monkeypatch):
    model = importlib.import_module("compound_field_forecast")
    original = model.read_json
    saved = original(model.FOLDER / "compound-v29-development.json")
    model.check_seal(saved)
    replay = model.run()
    assert saved["source_sha256_lf"] == replay["source_sha256_lf"]
    assert saved["parent_sha256"] == replay["parent_sha256"]
    assert saved["protocol_sha256_lf"] == replay["protocol_sha256_lf"]
    field_model.compare(replay["field_estimates"], saved["field_estimates"])
    field_model.compare(replay["field_errors"], saved["field_errors"])
    field_model.compare(replay["result"], saved["result"])
    data = original(model.FOLDER / "compound-v24-cohort.json")
    prev = original(model.FOLDER / "compound-v28-development.json")
    event = str(data["cases"][0]["session"])
    for row, context in zip(data["cases"], prev["contexts"], strict=True):
        if str(row["session"]) == event:
            context["future_diagnostic"] = [100.0] * 6
    del prev["content_sha256"]
    changed = model.seal(prev)
    monkeypatch.setattr(
        model,
        "read_json",
        lambda path: changed if path.name == "compound-v28-development.json" else original(path),
    )
    poisoned = model.run()
    for a, b in zip(replay["result"]["predictions"], poisoned["result"]["predictions"], strict=True):
        if a["event"] == event:
            assert a == b
