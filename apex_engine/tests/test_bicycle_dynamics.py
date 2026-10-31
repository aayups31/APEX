from dataclasses import replace

import numpy as np
import pytest
from scipy.linalg import expm

from apexsim.research.bicycle import (
    BicycleControl,
    BicycleParameters,
    BicycleState,
    StraightPowerDragInput,
    bicycle_rhs,
    integrate_bicycle,
    kinetic_energy_j,
    lateral_linear_system,
)
from apexsim.research.longitudinal_calibration import SpecificPowerDrag, integrate_speed


def test_constant_force_straight_matches_analytical_position_and_speed():
    p = BicycleParameters()
    t = np.array([0, .17, .43, 1.1, 2.])
    result = integrate_bicycle(BicycleState(vx_mps=20), t, [BicycleControl(rear_fx_request_n=1800)]*4, p)
    np.testing.assert_allclose(result.states[:, 0], 20*t+t*t, atol=1e-9, rtol=0)
    np.testing.assert_allclose(result.states[:, 3], 20+2*t, atol=1e-9, rtol=0)
    np.testing.assert_array_equal(result.states[:, [1, 2, 4, 5]], np.zeros((5, 4)))


def test_analytical_linear_jacobian_matches_finite_difference_nonlinear_rhs():
    p, v, eps = BicycleParameters(), 40., 1e-6
    a, b = lateral_linear_system(v, p)
    measured = np.zeros((2, 2))
    for j, name in enumerate(("vy_mps", "yaw_rate_radps")):
        plus, _ = bicycle_rhs(replace(BicycleState(vx_mps=v), **{name: eps}), BicycleControl(), p)
        minus, _ = bicycle_rhs(replace(BicycleState(vx_mps=v), **{name: -eps}), BicycleControl(), p)
        measured[:, j] = (plus[[4, 5]]-minus[[4, 5]])/(2*eps)
    np.testing.assert_allclose(a, measured, atol=1e-5, rtol=0)
    plus, _ = bicycle_rhs(BicycleState(vx_mps=v), BicycleControl(eps), p)
    minus, _ = bicycle_rhs(BicycleState(vx_mps=v), BicycleControl(-eps), p)
    np.testing.assert_allclose(b, (plus[[4, 5]]-minus[[4, 5]])/(2*eps), atol=1e-5, rtol=0)


def test_default_small_angle_stability_and_deliberate_oversteer_instability():
    p = BicycleParameters()
    for v in (5, 10, 20, 40, 70, 100, 110):
        a, _ = lateral_linear_system(v, p)
        assert np.max(np.linalg.eigvals(a).real) < 0
    unstable = replace(p, front_stiffness_nprad=200000, rear_stiffness_nprad=50000)
    assert np.max(np.linalg.eigvals(lateral_linear_system(40, unstable)[0]).real) > 0


def test_small_angle_transient_matches_analytical_matrix_exponential():
    p, delta = BicycleParameters(), 1e-4
    t = np.linspace(0, 4, 41)
    for v in (20, 40, 70):
        a, b = lateral_linear_system(v, p)
        equilibrium = -np.linalg.solve(a, b*delta)
        exact = np.array([(np.eye(2)-expm(a*time))@equilibrium for time in t])
        path = integrate_bicycle(BicycleState(vx_mps=v), t, [BicycleControl(delta)]*40, p)
        np.testing.assert_allclose(path.states[:, [4, 5]], exact, atol=1e-6, rtol=.01)


def test_open_loop_disturbance_decays_and_unforced_energy_cannot_increase():
    p, initial = BicycleParameters(), BicycleState(vx_mps=40, vy_mps=.2, yaw_rate_radps=.02)
    t = np.linspace(0, 6, 61)
    path = integrate_bicycle(initial, t, [BicycleControl()]*60, p)
    assert abs(path.states[-1, 4]) < .1*abs(initial.vy_mps)
    assert abs(path.states[-1, 5]) < .1*abs(initial.yaw_rate_radps)
    energies = [kinetic_energy_j(BicycleState.from_array(s), p) for s in path.states]
    assert np.max(np.diff(energies)) <= 1e-6
    assert path.integration_checks["maximum_power_balance_error_w"] < 1e-7


def test_rk4_refinement_preserves_mirror_and_combined_grip():
    p, t = BicycleParameters(), np.linspace(0, 3, 31)
    command = BicycleControl(.02, -1000, -500)
    results = [integrate_bicycle(BicycleState(vx_mps=40), t, [command]*30, p, max_step_s=h) for h in (.02, .01, .005)]
    assert np.max(abs(results[1].states-results[2].states)) < 1e-4
    assert np.max(abs(results[0].states-results[2].states)) < 1e-4
    mirror = integrate_bicycle(BicycleState(vx_mps=40), t, [replace(command, steering_rad=-.02)]*30, p)
    np.testing.assert_allclose(mirror.states, results[1].states*np.array([1, -1, -1, 1, -1, -1]), atol=1e-10)
    assert results[1].integration_checks["maximum_utilization_squared"] <= 1+1e-12


def test_r030_adapter_preserves_power_law_and_reports_grip_limitation():
    model = SpecificPowerDrag(557.5166868553622, .0008020051840913403)
    p, state, command = BicycleParameters(mu_x=8), BicycleState(vx_mps=50), StraightPowerDragInput(model)
    rhs, d = bicycle_rhs(state, command.at(state, p), p)
    assert rhs[3] == pytest.approx(model.acceleration(50, 1, 0), abs=1e-10)
    assert not d.rear.longitudinal_projected
    t = np.linspace(0, 2, 21)
    path = integrate_bicycle(state, t, [command]*20, p)
    reference = integrate_speed(50, t, np.ones(21), np.zeros(21), model.acceleration, max_step_s=.01)
    np.testing.assert_allclose(path.states[:, 3], reference, atol=1e-6, rtol=0)
    prior = BicycleParameters()
    limited, diag = bicycle_rhs(state, command.at(state, prior), prior)
    assert diag.rear.longitudinal_projected and limited[3] < rhs[3]
    with pytest.raises(ValueError, match="straight"):
        command.at(replace(state, vy_mps=.1), p)
    with pytest.raises(ValueError, match="straight"):
        command.at(replace(state, vx_mps=39), p)
    with pytest.raises(ValueError, match="full-throttle"):
        StraightPowerDragInput(model, .5)


def test_bad_time_commands_budget_and_intermediate_domain_reject():
    p, initial = BicycleParameters(), BicycleState(vx_mps=5.001)
    for times, commands, kwargs in (([0, 0], [BicycleControl()], {}), ([0, 1], [], {}),
                                    ([0, float("nan")], [BicycleControl()], {}),
                                    ([0, 1], [BicycleControl()], {"max_step_s": .1}),
                                    ([0, 1], [BicycleControl()], {"max_substeps": True}),
                                    ([0, 1], [BicycleControl()], {"max_substeps": 2})):
        with pytest.raises(ValueError, match="R031"):
            integrate_bicycle(initial, np.array(times), commands, p, **kwargs)
    with pytest.raises(ValueError, match="support; no state clipping"):
        integrate_bicycle(initial, np.array([0, .1]), [BicycleControl(rear_fx_request_n=-1000)], p)


def test_projection_diagnostics_include_all_rk_stages_and_endpoints():
    path = integrate_bicycle(BicycleState(vx_mps=30), np.array([0, .1]),
                             [BicycleControl(rear_fx_request_n=10000)], BicycleParameters(), max_step_s=.01)
    checks = path.integration_checks
    assert checks["stage_evaluations"] == 50
    assert checks["projected_axle_requests"] == 50
    assert checks["maximum_fx_projection_n"] == pytest.approx(10000-1.5*3924)
    assert checks["maximum_utilization_squared"] == 1
