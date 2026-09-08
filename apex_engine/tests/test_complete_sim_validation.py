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


@pytest.mark.parametrize(
    ("column", "value", "capacity", "diagnostic"),
    [
        ("battery_mj", 5.0, 4.0, "invalid_battery_rows"),
        ("throttle", 1.1, None, "invalid_control_rows"),
        ("position", 0, None, "invalid_position_rows"),
    ],
)
def test_quality_report_names_broken_contract(column, value, capacity, diagnostic):
    telemetry = build_demo(seed=10, total_laps=1).run().telemetry
    telemetry.loc[telemetry.index[0], column] = value
    report = validate_simulation_telemetry(
        telemetry,
        expected_cars=6,
        battery_capacity_mj=capacity,
    )
    with pytest.raises(RuntimeError, match=diagnostic):
        assert_simulation_quality(report)


def test_duplicate_race_positions_fail_the_quality_gate():
    telemetry = build_demo(seed=11, total_laps=1).run().telemetry
    first_time = telemetry.time_s.min()
    first_rows = telemetry.index[telemetry.time_s == first_time]
    telemetry.loc[first_rows[1], "position"] = telemetry.loc[first_rows[0], "position"]
    report = validate_simulation_telemetry(telemetry, expected_cars=6)
    with pytest.raises(RuntimeError, match="duplicate_position_rows"):
        assert_simulation_quality(report)


def test_resource_capacity_violation_is_reported():
    telemetry = build_demo(seed=13, total_laps=1).run().telemetry
    telemetry.loc[telemetry.index[0], "fuel_kg"] = 111.0
    report = validate_simulation_telemetry(telemetry, fuel_capacity_kg=110.0)
    with pytest.raises(RuntimeError, match="excess_fuel_rows"):
        assert_simulation_quality(report)
