import numpy as np
import pytest

from apexsim.research.closed_loop import lap_metrics, physical_gate, recovery_metrics, run_continuous
from apexsim.research.imitation_driver import rollout_policy
from apexsim.research.reference_geometry import GeometryConfig, ReferenceCurve
from apexsim.research.transparent_driver import DriverMap


@pytest.fixture(scope="module")
def track():
    return DriverMap.from_curve(ReferenceCurve(np.array([[0., 0.], [25., 0.], [0., 25.]]), GeometryConfig(1, 0.), "SIMULATED"))


def test_seams_preserve_full_first_lap_and_actuator_memory(track):
    old, reference = rollout_policy(track, (.65, 60.), 10., "transparent", .1)
    result, arrays = run_continuous(track, (.65, 60.), 10., "transparent", .1, None, laps=3)
    assert old["passed"] and result["passed"] and result["state_resets"] == 0
    assert len(result["seam_states"]) == 3 and arrays["station_m"][-1] >= 3*track.length_m
    for key in ("time_s", "states", "station_m", "lateral_m", "controls", "features"):
        np.testing.assert_allclose(arrays[key][:len(reference[key])], reference[key], atol=1e-11)
    assert np.all(np.diff(arrays["station_m"]) > 0)
    assert max(abs(np.diff(arrays["controls"][:, 0]))) <= .15+1e-14


def test_station_weighted_metrics_do_not_repeat_a_reset_lap(track):
    station = np.linspace(0, 3*track.length_m, 6001)
    values = {"station_m": station, "time_s": station/10, "lateral_m": station/track.length_m}
    rows = lap_metrics(track, values, 3)
    assert len(rows) == 3 and rows[2]["maximum_error_m"] == pytest.approx(3)
    assert rows[0]["rmse_m"] == pytest.approx(np.sqrt(np.mean(np.linspace(0, 1, 2001)**2)))
    assert rows[2]["rmse_m"] > rows[0]["rmse_m"]


def test_recovery_requires_both_pulses_and_a_sustained_window():
    t = np.arange(0, 25.1, .1)
    nominal = {"station_m": t*10, "lateral_m": np.zeros(len(t))}
    lateral = np.zeros(len(t))
    lateral[20:70] = .3
    lateral[150:180] = .3
    values = {"time_s": t, "station_m": t*10, "lateral_m": lateral}
    events = {"events": [{"start_index": 20, "end_index": 25}, {"start_index": 150, "end_index": 155}]}
    rows = recovery_metrics(events, values, nominal)
    assert [r["recovery_s"] for r in rows] == pytest.approx([4.5, 2.5])
    lateral[180:] = .3
    assert not recovery_metrics(events, values, nominal)[1]["passed"]


def test_action_disturbances_recur_across_seams_without_state_jumps(track):
    base, nominal = run_continuous(track, (.65, 60.), 10., "transparent", .1, None, laps=3)
    result, arrays = run_continuous(track, (.65, 60.), 10., "transparent", .1, None, laps=3, scenario="pulse_right")
    assert base["passed"] and result["passed"] and len(result["events"]) == 2
    assert all(e["amplitude_rad"] < 0 for e in result["events"])
    assert all(r["passed"] for r in recovery_metrics(result, arrays, nominal))
    assert np.max(np.linalg.norm(np.diff(arrays["states"][:, :2], axis=0), axis=1)) < 10


def test_explicit_abstention_stops_before_any_dynamics(track):
    def stop(*args):
        return None, {"mode": "abstain", "reason": "UNTRUSTED_STATE"}
    result, arrays = run_continuous(track, (.65, 60.), 10., "transparent", .1, None, laps=3, controller=stop)
    assert result["abstained"] and not result["completed"] and not result["passed"]
    assert result["failure"] == "UNTRUSTED_STATE" and arrays["controls"].shape == (0, 4)
    assert arrays["states"].shape == (1, 6) and len(result["decisions"]) == 1


def test_physical_gate_rejects_missing_or_failed_invariants():
    valid = {"maximum_utilization_squared": 1., "minimum_contact_load_n": 1.,
             "maximum_pitch_residual_nm": 0., "maximum_power_balance_error_w": 0.}
    assert physical_gate(valid) and not physical_gate({})
    for key, value in (("maximum_utilization_squared", 1.1), ("minimum_contact_load_n", 0),
                       ("maximum_pitch_residual_nm", .01), ("maximum_power_balance_error_w", .01)):
        assert not physical_gate(dict(valid, **{key: value}))


def test_invalid_horizon_and_scenario_are_not_silently_substituted(track):
    with pytest.raises(ValueError, match="horizon"):
        run_continuous(track, (.65, 60.), 10., "transparent", .1, None, laps=1)
    with pytest.raises(ValueError, match="disturbance"):
        run_continuous(track, (.65, 60.), 10., "transparent", .1, None, scenario="unknown")
