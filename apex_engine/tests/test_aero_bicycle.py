from dataclasses import replace

import numpy as np
import pytest

from apexsim.research.aero_bicycle import (
    AeroParameters,
    aero_bicycle_rhs,
    integrate_aero_bicycle,
    solve_axle_loads,
)
from apexsim.research.bicycle import (
    BicycleControl,
    BicycleParameters,
    BicycleState,
    StraightPowerDragInput,
    bicycle_rhs,
    integrate_bicycle,
)
from apexsim.research.longitudinal_calibration import SpecificPowerDrag


def test_hand_aero_load_pitch_and_force_fixture():
    p, a = BicycleParameters(), AeroParameters()
    _, d = aero_bicycle_rhs(BicycleState(vx_mps=50), BicycleControl(front_fx_request_n=900, rear_fx_request_n=1800), p, a)
    assert d.loads.downforce_n == pytest.approx(4593.75, abs=1e-8)
    assert d.loads.drag_n == pytest.approx(1684.375, abs=1e-8)
    assert d.loads.front.normal_n == pytest.approx(6747.1875, abs=1e-8)
    assert d.loads.rear.normal_n == pytest.approx(6675.5625, abs=1e-8)
    assert abs(d.loads.pitch_residual_nm) < 1e-6
    assert d.wrench.body_fx_n/900 == pytest.approx(1.1284722222222223)


def test_drive_brake_balance_and_speed_squared_directions():
    p, a, state = BicycleParameters(), AeroParameters(), BicycleState(vx_mps=50)
    coast = solve_axle_loads(state, BicycleControl(), p, a)
    drive = solve_axle_loads(state, BicycleControl(rear_fx_request_n=2000), p, a)
    brake = solve_axle_loads(state, BicycleControl(rear_fx_request_n=-2000), p, a)
    assert brake.front.normal_n > coast.front.normal_n > drive.front.normal_n
    forward = solve_axle_loads(state, BicycleControl(), p, replace(a, front_downforce_fraction=.6))
    assert forward.front.normal_n > coast.front.normal_n and forward.rear.normal_n < coast.rear.normal_n
    doubled = solve_axle_loads(replace(state, vx_mps=100), BicycleControl(), p, a)
    assert doubled.drag_n == pytest.approx(4*coast.drag_n)
    assert doubled.downforce_n == pytest.approx(4*coast.downforce_n)
    # A CoG drag force has no pitch moment; do not transfer its deceleration twice.
    no_drag = solve_axle_loads(state, BicycleControl(), p, replace(a, drag_area_m2=0))
    assert coast.front.normal_n == no_drag.front.normal_n


def test_coupled_force_grid_load_sum_pitch_and_grip_constraints():
    p, a = BicycleParameters(), AeroParameters()
    for v in (10, 40, 90):
        for steering in (-.1, 0, .1):
            for fx in (-20000, -3000, 0, 3000, 20000):
                state = BicycleState(vx_mps=v, vy_mps=.2, yaw_rate_radps=.02)
                try:
                    _, d = aero_bicycle_rhs(state, BicycleControl(steering, fx, fx), p, a)
                except ValueError as exc:
                    assert "uniqueness unsupported across front saturation" in str(exc)
                    continue
                assert d.loads.front.normal_n+d.loads.rear.normal_n == pytest.approx(p.mass_kg*9.81+d.loads.downforce_n, abs=1e-7)
                assert abs(d.loads.pitch_residual_nm) <= 1e-6
                assert d.loads.load_derivative_bound < .9
                assert max(d.loads.front.utilization_squared, d.loads.rear.utilization_squared) <= 1+1e-12
                assert d.wrench.lateral_slip_power_w <= 1e-9
                assert d.wrench.kinetic_energy_rate_w == pytest.approx(d.wrench.wheel_power_w, rel=1e-10, abs=1e-6)


def test_zero_aero_height_exactly_reduces_to_r031_equations_and_trajectory():
    p, a = BicycleParameters(), AeroParameters(drag_area_m2=0, downforce_area_m2=0, cg_height_m=0)
    state, command = BicycleState(vy_mps=.2, yaw_rate_radps=.02), BicycleControl(.02, -1000, 500, 100)
    actual, _ = aero_bicycle_rhs(state, command, p, a)
    expected, _ = bicycle_rhs(state, command, p)
    np.testing.assert_allclose(actual, expected, atol=1e-10, rtol=0)
    t = np.linspace(0, 2, 21)
    loaded = integrate_aero_bicycle(state, t, [command]*20, p, a)
    original = integrate_bicycle(state, t, [command]*20, p)
    np.testing.assert_allclose(loaded.states, original.states, atol=1e-8, rtol=0)


def test_contact_loss_and_missing_uniqueness_support_abstain():
    p = BicycleParameters()
    with pytest.raises(ValueError, match="contact bracket"):
        solve_axle_loads(BicycleState(vx_mps=100), BicycleControl(rear_fx_request_n=1e6), p,
                          AeroParameters(downforce_area_m2=10, front_downforce_fraction=0, cg_height_m=.6))
    with pytest.raises(ValueError, match="uniqueness"):
        solve_axle_loads(BicycleState(), BicycleControl(), p, AeroParameters(cg_height_m=2))
    with pytest.raises(ValueError, match="front saturation boundary"):
        solve_axle_loads(BicycleState(vx_mps=90), BicycleControl(.1, 20000), p, AeroParameters())
    with pytest.raises(ValueError, match="no implicit R030"):
        solve_axle_loads(BicycleState(), StraightPowerDragInput(SpecificPowerDrag(900, .0005)), p, AeroParameters())


def test_invalid_inputs_cannot_be_silently_clipped_or_integrated():
    for kwargs in ({"cg_height_m": -1}, {"front_downforce_fraction": 1.1}, {"air_density_kgpm3": 0}, {"drag_area_m2": float("nan")}):
        with pytest.raises(ValueError, match="R032"):
            AeroParameters(**kwargs)
    with pytest.raises(ValueError, match="R032"):
        integrate_aero_bicycle(BicycleState(), np.array([0, .1]), [BicycleControl()], BicycleParameters(), AeroParameters(), max_step_s=.1)
