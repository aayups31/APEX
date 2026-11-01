from dataclasses import asdict

import numpy as np
import pytest

from apexsim.research import imitation_driver as il
from apexsim.research.bicycle import BicycleState
from apexsim.research.reference_geometry import GeometryConfig, ReferenceCurve
from apexsim.research.transparent_driver import DriverMap, command, simulate_driver, speed_profile


def synthetic_track(chicane=False):
    coefficients = (np.array([[0., 0.], [130., 0.], [0., 0.], [0., 80.], [0., 12.]]) if chicane
                    else np.array([[0., 0.], [70., 0.], [0., 70.]]))
    return DriverMap.from_curve(ReferenceCurve(coefficients, GeometryConfig(2 if chicane else 1, 0.), "SIMULATED_IMITATION"))


def test_hand_monomials_and_weighted_ridge_solution():
    x = np.zeros((2, 8))
    x[0, :2] = [2., 3.]
    matrix = il.design_matrix(x, 2)
    assert matrix.shape == (2, 45)
    assert matrix[0, 0] == 1 and matrix[0, 9] == 4 and matrix[0, 10] == 6
    rng = np.random.default_rng(17)
    x = rng.normal(size=(100, 8))
    target = .02*x[:, 0]-.01*x[:, 1]+.003
    weights = np.arange(1, 101, dtype=float)
    model = il.fit_policy(x, target, weights, 1, 1e-8)
    np.testing.assert_allclose(model["mean"], (weights/weights.sum())@x)
    predicted = np.array([il.predict_residual(model, row) for row in x])
    np.testing.assert_allclose(predicted, target, atol=2e-8, rtol=0)
    assert model["training_rows"] == 100 and model["parameters"] == 9
    with pytest.raises(ValueError, match="training-only"):
        il.fit_policy(x, target, np.zeros(100), 1, 1e-8)


def test_baseline_actions_match_accepted_r035_force_and_actuator_equations():
    track = synthetic_track(True)
    profile = speed_profile(track, .65, 60.)
    for station in (0., 50., 200.):
        xy, heading, _ = track.at(station)
        state = BicycleState(*xy, heading+.02, 30., -.1, .03)
        expected, log = command(state, track, profile, station, .4, .03)
        actual, row, _ = il.policy_command(state, track, profile, station, .4, .03, .05, "transparent")
        np.testing.assert_allclose(list(asdict(actual).values()), list(asdict(expected).values()), atol=1e-9, rtol=0)
        assert il.baseline_raw(row) == pytest.approx(log["raw_steering_rad"], abs=1e-13)


def test_local_features_are_translation_and_rotation_invariant():
    track = synthetic_track()
    station, angle = 30., .7
    xy, heading, _ = track.at(station)
    state = BicycleState(*xy, heading+.1, 30., .2, .1)
    row = il.observation(state, track, station, .2, .03, .05)
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    offset = np.array([500., -200.])
    moved = DriverMap(track.length_m, track.xy@rotation.T+offset, track.tangent@rotation.T, track.curvature.copy())
    position = xy@rotation.T+offset
    shifted = BicycleState(*position, state.heading_rad+angle, 30., .2, .1)
    np.testing.assert_allclose(il.observation(shifted, moved, station, .2, .03, .05), row, atol=1e-12)


def test_deployed_prediction_does_not_query_expert_or_training(monkeypatch):
    track = synthetic_track()
    x = np.random.default_rng(29).normal(size=(100, 8))
    model = il.fit_policy(x, np.zeros(100), np.ones(100), 1, 1e-8)

    def forbidden(*args):
        raise AssertionError("Expert/training accessed at deployment")

    monkeypatch.setattr(il, "expert_residual", forbidden)
    monkeypatch.setattr(il, "fit_policy", forbidden)
    xy, heading, _ = track.at(0.)
    action, _, log = il.policy_command(BicycleState(*xy, heading, 20., 0., 0.), track, speed_profile(track, .65, 60.), 0., 0., 0., .05, "learned", model)
    assert np.isfinite(action.steering_rad) and log["raw_residual_rad"] == 0


def test_bounded_learned_influence_and_real_actuator_projection_are_logged():
    track = synthetic_track()
    x = np.random.default_rng(31).normal(size=(100, 8))
    model = il.fit_policy(x, np.full(100, 10.), np.ones(100), 1, 1e-8)
    xy, heading, _ = track.at(0.)
    action, _, log = il.policy_command(BicycleState(*xy, heading, 20., 0., 0.), track, speed_profile(track, .65, 60.), 0., 0., 0., .05, "learned", model)
    assert log["residual_projected"] and log["bounded_residual_rad"] == .2
    assert log["steering_projected"] and action.steering_rad <= .15+1e-12


def test_new_runner_preserves_accepted_r035_baseline_trajectory():
    track = synthetic_track()
    old, path = simulate_driver(track, (.65, 60.), 15., initial_lateral=.4)
    new, replay = il.rollout_policy(track, (.65, 60.), 15., "transparent", .05, initial_lateral=.4)
    assert old["passed"] and new["passed"]
    np.testing.assert_allclose(path["states"], replay["states"], atol=1e-8, rtol=1e-8)


def test_expert_demonstration_is_genuinely_fitted_and_can_drive_synthetic_lap():
    track = synthetic_track(True)
    expert, path = il.rollout_policy(track, (.65, 60.), 15., "expert", .05, initial_lateral=.4, initial_heading=.01)
    assert expert["passed"], expert
    x = path["features"]
    target = np.array([il.expert_residual(row) for row in x])
    model = il.fit_policy(x, target, np.ones(len(x)), 2, 1e-8)
    assert model["training_weighted_mse_rad2"] < 1e-7
    learned, _ = il.rollout_policy(track, (.65, 60.), 15., "learned", .05, model, initial_lateral=.4, initial_heading=.01)
    assert learned["passed"], learned
    assert abs(learned["final_lateral_error_m"]) < .4


def test_failed_prefix_cannot_be_reported_as_complete():
    result, path = il.rollout_policy(synthetic_track(), (.65, 60.), 15., "transparent", .05, maximum_time=.2)
    assert not result["passed"] and not result["completed"] and result["failure"]
    assert path["states"].shape == (3, 6)
