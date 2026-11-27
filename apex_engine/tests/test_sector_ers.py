import pytest

from apexsim.examples.sector_ers_study import BATTERY, DISTURBED, HARVEST, NOMINAL, VERSION, run_study
from apexsim.research.evidence import read_json, verify_inventory
from apexsim.research.sector_ers import (
    InfeasibleEnergyPlan,
    advance,
    feedback_step,
)


def test_wheel_work_and_conversion_loss_reconcile():
    deployed = advance(BATTERY, 1, NOMINAL[0], -0.5)
    assert deployed.charge_mj == 0.5
    assert deployed.wheel_work_mj == 0.4
    assert deployed.conversion_loss_mj == pytest.approx(0.1)
    harvested = advance(BATTERY, deployed.charge_mj, HARVEST, 0.5)
    assert harvested.charge_mj == 1
    assert harvested.wheel_work_mj == -0.625
    assert harvested.conversion_loss_mj == 0.125
    with pytest.raises(ValueError, match="sector opportunity"):
        advance(BATTERY, 1, DISTURBED[1], 0.5)
    with pytest.raises(ValueError, match="battery bounds"):
        advance(BATTERY, 1.8, HARVEST, 0.5)
    with pytest.raises(InfeasibleEnergyPlan):
        feedback_step(BATTERY, 0.5, NOMINAL[-1], ())


def test_sector_study_saves_replayed_constraints_and_disturbance(tmp_path):
    output = tmp_path / "ers"
    summary = run_study(output)
    assert summary["passed"]
    assert verify_inventory(output, VERSION)["summary_sha256"] == summary["content_sha256"]
    traces = read_json(output / "trajectories.json")
    for key in ("nominal", "nominal_feedback", "disturbed_feedback", "disturbed_open_loop"):
        steps = traces[key]["trace"]
        charge = 1.0
        for step in steps:
            assert step["prior_charge_mj"] == charge
            charge += step["storage_delta_mj"]
            assert step["charge_mj"] == charge
            assert 0 <= charge <= 2
    assert summary["disturbed_feedback_terminal_mj"] == 1.0
    assert summary["disturbed_open_loop_terminal_mj"] == 0.875
