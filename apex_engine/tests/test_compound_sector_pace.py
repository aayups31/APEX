from pathlib import Path
from runpy import run_path

import numpy as np
import pytest

from apexsim.research.evidence import check_seal, read_json
from apexsim.research.green_traffic import SectorTrafficCalibration

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "research/scripts"


def test_sector_pace_uses_completed_observations_and_fixed_neighbors(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    study = run_path(str(SCRIPTS / "compound_sector_pace.py"))
    current = [810.0, 900.0, 990.0]
    reference = [90.0, 180.0, 270.0, 360.0, 450.0, 540.0]
    row = {
        "driver": 1,
        "forecast_at_s": 990.0,
        "current_history": [{"end_s": t} for t in current],
        "reference_history": [{"end_s": t} for t in reference],
    }

    def lap(t):
        return [[point, [point - 0.5, 2, t - 0.5]] for point in (t, t - 60, t - 30)]

    groups = [[lap(t) for t in seq] for seq in (current, reference[:3], reference[3:])]
    seconds = np.arange(0.0, 1100.0, 0.25)
    codes = np.where(seconds >= row["forecast_at_s"], 14, 0)
    states = study["states"]
    history = states(row, groups, (seconds, codes), 0.0)
    assert history == [["close"] * 6] * 3
    shifts, support = study["features"](history, SectorTrafficCalibration(0.3, -0.5))
    assert shifts == pytest.approx([0.6] * 3)
    assert support == [1.0] * 3

    groups[0][-1][0][1][1] = 3
    assert states(row, groups, (seconds, codes), 0.0)[0][-1] is None
    groups[0][-1][1][1][2] = 991.0
    with pytest.raises(ValueError, match="Ineligible peer timing"):
        states(row, groups, (seconds, codes), 0.0)


def test_v33_evidence_keeps_original_gate_and_rejects_candidate():
    evidence = read_json(ROOT / "docs/verification/compound-v33-development.json")
    check_seal(evidence)
    assert len(evidence["histories"]) == 393
    assert len(evidence["result"]["models"]) == 24
    assert len(evidence["result"]["failed_events"]) == 16
    assert not evidence["continue_direction"]
    assert not evidence["new_holdout_acquisition_allowed"]
