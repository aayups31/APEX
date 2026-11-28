from pathlib import Path
from runpy import run_path

import pytest

from apexsim.research.evidence import check_seal, read_json
from apexsim.research.neutralized_gaps import load_neutralization_gaps, scale_gaps
from apexsim.sim_core.types import FlagState

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/verification/r049-per-car-gaps.json"


def test_replay_preserves_order_and_switches_at_release():
    model = load_neutralization_gaps(EVIDENCE)
    before = (0.0, 1.2, 3.0, 10.0)
    for mode in (FlagState.SAFETY_CAR, FlagState.VSC):
        path = model.replay(mode, before, start_s=10, release_s=20)
        assert path.flag_at(9.99) is FlagState.GREEN
        assert path.flag_at(10) is mode
        assert path.flag_at(19.99) is mode
        assert path.flag_at(20) is FlagState.GREEN
        for gaps in (path.neutralized_s, path.first_green_lap_s):
            assert gaps[0] == 0
            assert list(gaps) == sorted(gaps)
        if mode is FlagState.VSC:
            assert path.first_green_lap_s == before
    with pytest.raises(ValueError, match="ordered gap"):
        scale_gaps((0.0, 4.0, 2.0), 0.4)
    with pytest.raises(ValueError, match="interval"):
        model.replay(FlagState.VSC, before, start_s=20, release_s=20)


def test_saved_race_holdouts_replay(monkeypatch):
    scripts = ROOT / "research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    study = run_path(str(scripts / "fit_neutralized_car_gaps.py"))
    saved = read_json(EVIDENCE)
    check_seal(saved)
    actual = study["score"](saved["races"])
    assert actual == {key: saved[key] for key in actual}
    assert actual["passed"]
    for row in actual["folds"]:
        assert row["release_s"] > row["start_s"]
        assert all(gaps[0] == 0 and gaps == sorted(gaps) for gaps in row["predicted_s"])
