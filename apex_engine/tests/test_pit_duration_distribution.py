from pathlib import Path
from runpy import run_path

import pytest


def test_empirical_pit_duration_score_and_saved_gate_replay(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    scripts = root / "research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    study = run_path(str(scripts / "fit_pit_duration_distribution.py"))
    assert study["crps"]([1.0, 3.0], 2.0) == pytest.approx(0.5)
    saved = study["read_json"](root / "docs/verification/pit-duration-r047-v1.json")
    study["check_seal"](saved)
    assert study["run"]() == saved
    assert saved["folds"]["F1_2024_R18"]["fallback"]


def test_race_shift_replays_development_gate(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    scripts = root / "research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    study = run_path(str(scripts / "fit_pit_duration_race_shift.py"))
    saved = study["read_json"](root / "docs/verification/pit-duration-r047-v2.json")
    study["check_seal"](saved)
    assert study["run"]() == saved
    assert saved["passed"] and not saved["fresh_confirmation"]
