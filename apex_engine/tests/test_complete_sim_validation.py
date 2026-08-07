from apexsim.examples.complete_sim_demo import build_demo
from apexsim.sim_core.validation import validate_simulation_telemetry


def test_demo_quality_report_passes():
    result = build_demo(seed=7, total_laps=2).run()
    report = validate_simulation_telemetry(result.telemetry, expected_cars=6)
    assert report.passed
    assert not result.laps.empty
    assert not result.stints.empty
