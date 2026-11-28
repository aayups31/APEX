from pathlib import Path
from random import Random
from runpy import run_path

import pytest

from apexsim.research.evidence import check_seal, read_json
from apexsim.research.retirement_hazards import load_retirement_hazards


def test_reliability_model_replays_and_ignores_held_out_labels_when_fitting(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    scripts = root / "research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    study = run_path(str(scripts / "fit_cause_hazards.py"))
    saved = read_json(root / "docs/verification/retirement-causes-r048-v2.json")
    check_seal(saved)
    assert study["score"](saved["events"], reliability=True) == saved["result"]
    events = saved["events"]
    event = next(e for e in events if e.startswith("F1_2024"))
    events[event]["later"]["incident"] += 100
    changed = study["score"](events, reliability=True)
    assert changed["hazards_by_year"] == saved["result"]["hazards_by_year"]
    assert changed["aggregate"]["observed"] != saved["result"]["aggregate"]["observed"]
    classify = study["classify_corrected"]
    assert classify({"positionText": "DSQ", "reasonRetired": "Car underweight"}) == "censored"
    assert classify({"positionText": "DNF", "reasonRetired": "Accident on formation lap"}) == "excluded"
    assert classify({"positionText": "DNS", "reasonRetired": "Accident damage"}) == "excluded"
    assert classify({"positionText": "DNF", "reasonRetired": "Puncture"}) == "unknown"


def test_qualified_sampler_has_explicit_evaluated_seasons():
    folder = Path(__file__).resolve().parents[2] / "docs/verification"
    model = load_retirement_hazards(folder / "retirement-causes-r048-v2.json")
    early, later = model.for_lap(2025, 1), model.for_lap(2025, 2)
    assert early.incident > later.incident
    assert early.mechanical == later.mechanical
    a, b = Random(48), Random(48)
    assert [early.sample(a) for _ in range(500)] == [early.sample(b) for _ in range(500)]
    with pytest.raises(ValueError, match="Season outside"):
        model.for_lap(2026, 1)
