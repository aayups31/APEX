from pathlib import Path
from random import Random
from runpy import run_path

import pytest

from apexsim.research.evidence import read_json
from apexsim.research.pit_duration import load_pit_duration


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


def test_confirmation_does_not_treat_pit_exit_light_as_track_clear(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    scripts = root / "research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    study = run_path(str(scripts / "confirm_pit_duration_openf1.py"))
    rows = [
        {"date": "2025-01-01T12:00:00+00:00", "category": "SafetyCar", "message": "SAFETY CAR DEPLOYED"},
        {
            "date": "2025-01-01T12:01:00+00:00",
            "flag": "GREEN",
            "scope": "Track",
            "message": "GREEN LIGHT - PIT EXIT OPEN",
        },
        {"date": "2025-01-01T12:02:00+00:00", "flag": "CLEAR", "scope": "Track", "message": "TRACK CLEAR"},
    ]
    assert [green for _, green in study["status_events"](rows)] == [False, True]


def test_confirmed_distribution_replays_interval_and_seeded_draws():
    folder = Path(__file__).resolve().parents[2] / "docs/verification"
    paths = [folder / f"pit-duration-r047-{name}.json" for name in ("v1", "v2", "direct-confirmation")]
    evidence = read_json(paths[-1])
    for event, fold in evidence["result"]["folds"].items():
        circuit = evidence["events"][event]["circuit"]
        distribution = load_pit_duration(*paths, circuit, allow_pooled=True)
        left, right = Random(47), Random(47)
        assert [distribution.sample(left) for _ in range(20)] == [
            distribution.sample(right) for _ in range(20)
        ]
        assert distribution.central_interval_s() == pytest.approx(fold["candidate"]["interval_s"])
    with pytest.raises(ValueError, match="No circuit-specific"):
        load_pit_duration(*paths, "marina_bay")
    assert load_pit_duration(*paths, "marina_bay", allow_pooled=True).pooled
    with pytest.raises(ValueError, match="confirmed"):
        load_pit_duration(*paths[:-1], folder / "pit-duration-r047-openf1-confirmation.json", "monza")
