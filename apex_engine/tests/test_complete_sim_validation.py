import pytest

from apexsim.examples.complete_sim_demo import build_demo
from apexsim.sim_core.validation import assert_simulation_quality, validate_simulation_telemetry


def test_demo_quality_report_passes():
    result = build_demo(seed=7, total_laps=2).run()
    report = validate_simulation_telemetry(result.telemetry, expected_cars=6)
    assert report.passed
    assert not result.laps.empty
    assert not result.stints.empty


def test_invalid_simulation_state_fails_loudly():
    result = build_demo(seed=9, total_laps=1).run()
    result.telemetry.loc[result.telemetry.index[0], "fuel_kg"] = -1.0
    report = validate_simulation_telemetry(result.telemetry, expected_cars=6)
    assert not report.passed
    with pytest.raises(RuntimeError, match="negative_fuel_rows"):
        assert_simulation_quality(report)
