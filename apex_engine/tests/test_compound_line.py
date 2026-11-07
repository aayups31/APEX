import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_line_proximity_uses_only_prior_other_cars(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    module = importlib.import_module("compound_line_proximity")
    row = {
        "driver": 1,
        "forecast_at_s": 109,
        "current_history": [{"end_s": n} for n in (101, 105, 109)],
        "reference_history": [{"end_s": n} for n in (21, 31, 41, 51, 61, 71)],
    }
    clocks = sorted(
        [(r["end_s"], 1) for r in row["current_history"] + row["reference_history"]]
        + [(90, 2), (101, 2), (108, 3), (109, 4)]
    )
    links = module.link(row, clocks, set(clocks))
    assert links[0] == [None, (101, 2), (108, 3)]
    assert module.proximity_features(row, links) == [4, -9, 1 / 3, 10, 0, 0, 10, 0, 0]
    assert module.link(row, [*clocks, (110, 5)], set(clocks)) == links
    row["forecast_at_s"] = 108
    with pytest.raises(ValueError, match="Future"):
        module.link(row, clocks, set(clocks))


def test_sealed_line_proximity_forecasts_reproduce_all_race_gates(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    study = importlib.import_module("diagnose_compound_line")
    saved = study.read_json(study.FOLDER / "compound-v15-development.json")
    study.check_seal(saved)
    replay = study.study()
    result = replay["result"]
    assert replay["links_sha256"] == saved["links_sha256"]
    assert result["failed_events"] == saved["result"]["failed_events"]
    assert replay["development_qualified"] == saved["development_qualified"]
    for found, expected in zip(result["predictions"], saved["result"]["predictions"], strict=True):
        assert (found["index"], found["event"], found["crossings"]) == (
            expected["index"],
            expected["event"],
            expected["crossings"],
        )
        assert found["laps_s"] == pytest.approx(expected["laps_s"], abs=1e-9, rel=0)
    for found, expected in zip(result["folds"], saved["result"]["folds"], strict=True):
        assert found["cases"] == expected["cases"]
        for metric, old in zip(found["labels"], expected["labels"], strict=True):
            assert metric["failure_codes"] == old["failure_codes"]
            assert metric["mae_s"] == pytest.approx(old["mae_s"], abs=1e-9, rel=0)
