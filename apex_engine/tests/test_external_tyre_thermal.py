from pathlib import Path
from runpy import run_path

import numpy as np

from apexsim.research.evidence import check_seal, read_json

ROOT = Path(__file__).resolve().parents[2]


def test_external_thermal_features_are_causal_and_split_unsupported_history(monkeypatch):
    scripts = ROOT / "research/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    study = run_path(str(scripts / "compound_external_thermal.py"))
    clock = np.arange(180) * 0.25
    controls = np.zeros((len(clock), len(study["CONTROL_COLUMNS"])))
    controls[:, 0] = 15.0
    controls[:, -2] = clock * 15.0
    controls[80:, 0] = 30
    prefix = study["view"](controls[:80])[2]
    full = study["view"](controls)[2]
    for arm in study["ARMS"]:
        np.testing.assert_array_equal(full[arm][:80], prefix[arm])

    valid = np.r_[np.ones(70, dtype=bool), np.zeros(15, dtype=bool), np.ones(95, dtype=bool)]
    first, second = study["intervals"](clock[valid], controls[valid])
    assert (len(first), len(second)) == (70, 95)


def test_masked_thermal_pilot_uses_disjoint_sessions_and_preserves_r041_gate():
    report = read_json(ROOT / "docs/verification/compound-v34-external-thermal.json")
    check_seal(report)
    transfers = report["transfers"]
    october = set(transfers["november_to_october"]["hybrid"]["runs"])
    november = set(transfers["october_to_november"]["hybrid"]["runs"])
    assert (len(october), len(november)) == (8, 12)
    assert not october & november
    assert not report["r041_development_qualified"]
    for transfer in transfers.values():
        anchored = transfer["hybrid_with_measured_initial_temperature"]
        persistence = transfer["measured_initial_persistence"]
        assert anchored["equal_run_mae_c"] < persistence["equal_run_mae_c"]
        assert all(anchored["runs"][run]["samples"] == m["samples"] for run, m in persistence["runs"].items())
