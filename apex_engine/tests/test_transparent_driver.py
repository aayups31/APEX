import numpy as np
import pytest

from apexsim.research.bicycle import BicycleState
from apexsim.research.reference_geometry import GeometryConfig, ReferenceCurve
from apexsim.research.transparent_driver import CAR, DriverMap, command, simulate_driver, speed_profile, wrap


def synthetic_map(kind="circle"):
    if kind == "circle":
        coefficients = np.array([[0., 0.], [70., 0.], [0., 70.]])
        config = GeometryConfig(1, 0.)
    else:
        coefficients = np.array([[0., 0.], [130., 0.], [0., 0.], [0., 80.], [0., 12.]])
        config = GeometryConfig(2, 0.)
    return DriverMap.from_curve(ReferenceCurve(coefficients, config, "SIMULATED_"+kind))


def test_periodic_map_projection_and_braking_envelope():
    track = synthetic_map()
    xy, _, _ = track.at(1.)
    station, lateral = track.project(xy, track.length_m-1)
    assert station == pytest.approx(track.length_m+1, abs=.001)
    assert abs(lateral) < .001
    profile = speed_profile(track, .35, 60.)
    assert np.max(profile**2-np.roll(profile, -1)**2) <= 12*track.spacing+1e-9
    assert np.max(profile**2*abs(track.curvature)-.35*CAR.mu_y*(CAR.gravity_mps2+.5*1.225*3*profile**2/CAR.mass_kg)) < 1e-9
    assert wrap(2*np.pi+.1) == pytest.approx(.1)
    with pytest.raises(ValueError, match="corridor"):
        track.project(np.array([1000., 1000.]), 0.)


def test_hand_actuator_rate_force_sign_and_capacity():
    track = synthetic_map()
    profile = speed_profile(track, .35, 60.)
    xy, heading, _ = track.at(0.)
    fast = BicycleState(*xy, heading, 40., 0., 0.)
    action, log = command(fast, track, profile, 0., 0., 0.)
    assert 0 < action.steering_rad <= .15+1e-15
    assert action.front_fx_request_n < 0 and action.rear_fx_request_n < 0
    assert abs(action.front_fx_request_n) <= log["front_capacity_n"]
    assert abs(action.rear_fx_request_n) <= log["rear_capacity_n"]
    slow = BicycleState(*xy, heading, 10., 0., 0.)
    drive, _ = command(slow, track, profile, 0., 0., 0.)
    assert drive.front_fx_request_n == 0 and drive.rear_fx_request_n > 0
    # A displaced-left vehicle receives less left steering than the centered one.
    left, _ = command(slow, track, profile, 0., 1., .1)
    center, _ = command(slow, track, profile, 0., 0., .1)
    assert left.steering_rad < center.steering_rad


@pytest.mark.parametrize("kind", ["circle", "chicane"])
@pytest.mark.parametrize("fraction", [.35, .65])
def test_complete_synthetic_lap_and_small_disturbance_recovery(kind, fraction):
    track = synthetic_map(kind)
    result, arrays = simulate_driver(track, (fraction, 60.), 15., initial_lateral=.4, initial_heading_error=.01)
    assert result["completed"], result
    assert result["passed"], result
    assert abs(arrays["lateral_m"][-1]) < .4
    assert arrays["controls"].shape == (len(arrays["states"])-1, 4)


def test_failed_run_keeps_prefix_and_cannot_pass():
    result, arrays = simulate_driver(synthetic_map(), (.35, 60.), 15., maximum_time=.2)
    assert not result["completed"] and not result["passed"] and result["failure"]
    assert len(arrays["states"]) == 3
