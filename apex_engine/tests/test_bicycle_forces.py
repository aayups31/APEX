import itertools
import math
from dataclasses import replace

import numpy as np
import pytest

from apexsim.research.bicycle import (
    BicycleControl,
    BicycleParameters,
    BicycleState,
    axle_force,
    bicycle_rhs,
    kinetic_energy_j,
)


def test_static_loads_and_hand_force_balance():
    p = BicycleParameters()
    f, r = p.axle_loads_n
    assert f == pytest.approx(4905., abs=1e-9)
    assert r == pytest.approx(3924., abs=1e-9)
    assert f+r == pytest.approx(p.mass_kg*9.81, abs=1e-9)
    assert p.front_distance_m*f == pytest.approx(p.rear_distance_m*r, abs=1e-9)
    rhs, diag = bicycle_rhs(BicycleState(vx_mps=20), BicycleControl(front_fx_request_n=900, rear_fx_request_n=1800, resistance_n=450), p)
    np.testing.assert_allclose(rhs, [20, 0, 0, 2.5, 0, 0], atol=1e-9, rtol=0)
    assert diag.kinetic_energy_rate_w == pytest.approx(45000, abs=1e-9)
    assert kinetic_energy_j(BicycleState(vx_mps=20), p) == 180000


def test_hand_ellipse_and_full_longitudinal_capacity_leave_no_lateral_grip():
    f = axle_force(.08, 1200, 1000, 20000, 2, 1)
    assert f.lateral_budget_n == pytest.approx(800, abs=1e-9)
    assert f.fy_n == pytest.approx(-800*math.tanh(2), abs=1e-9)
    assert not f.longitudinal_projected and f.lateral_demand_exceeds_budget
    for demand in (-3000, -2000, 2000, 3000):
        full = axle_force(.08, demand, 1000, 20000, 2, 1)
        assert full.fx_n == math.copysign(2000, demand)
        assert full.fy_n == full.lateral_budget_n == 0
        assert full.utilization_squared == 1
        assert full.longitudinal_projected == (abs(demand) > 2000)


def test_declared_force_grid_feasibility_dissipation_and_symmetry():
    for normal, mx, my, alpha, fraction in itertools.product(
            (500, 1000, 5000), (.7, 1.5), (.8, 1.7), (-.3, -.05, 0, .05, .3), (-2, -1, -.6, 0, .6, 1, 2)):
        f = axle_force(alpha, fraction*mx*normal, normal, 100000, mx, my)
        assert f.utilization_squared <= 1+1e-12
        assert f.fy_n*math.sin(alpha) <= 1e-9
        mirror = axle_force(-alpha, -fraction*mx*normal, normal, 100000, mx, my)
        assert mirror.fx_n == -f.fx_n and mirror.fy_n == -f.fy_n


def test_combined_braking_or_drive_monotonically_reduces_lateral_budget():
    values = [axle_force(.1, fx, 1000, 20000, 1, 1) for fx in (0, 300, 600, 900, 1000)]
    assert all(a.lateral_budget_n > b.lateral_budget_n for a, b in itertools.pairwise(values))
    assert all(abs(a.fy_n) > abs(b.fy_n) for a, b in itertools.pairwise(values))


def test_wheel_rotation_body_wrench_and_yaw_include_front_drive_force():
    p = BicycleParameters()
    state = BicycleState(vx_mps=30, vy_mps=.4, yaw_rate_radps=.08)
    control = BicycleControl(.04, 1200, -700, 300)
    rhs, d = bicycle_rhs(state, control, p)
    alpha = math.atan2(.4+1.6*.08, 30)-.04
    assert d.front.slip_rad == pytest.approx(alpha, abs=1e-12)
    fyf = d.front.fx_n*math.sin(.04)+d.front.fy_n*math.cos(.04)
    assert d.body_fx_n == pytest.approx(d.front.fx_n*math.cos(.04)-d.front.fy_n*math.sin(.04)-700-300)
    assert d.body_fy_n == pytest.approx(fyf+d.rear.fy_n)
    assert rhs[5] == pytest.approx((1.6*fyf-2*d.rear.fy_n)/1500)
    assert rhs[3] == pytest.approx(.08*.4+d.body_fx_n/900)
    assert rhs[4] == pytest.approx(-.08*30+d.body_fy_n/900)


def test_left_right_mirror_and_initial_positive_steering_response():
    p = BicycleParameters()
    state = BicycleState(3, 2, .2, 30, .4, .08)
    ctrl = BicycleControl(.04, 1200, -700, 300)
    rhs, d = bicycle_rhs(state, ctrl, p)
    other, mirror = bicycle_rhs(replace(state, y_m=-2, heading_rad=-.2, vy_mps=-.4, yaw_rate_radps=-.08), replace(ctrl, steering_rad=-.04), p)
    np.testing.assert_allclose(other, rhs*np.array([1, -1, -1, 1, -1, -1]), atol=1e-12)
    assert mirror.front.fy_n == -d.front.fy_n
    initial, _ = bicycle_rhs(BicycleState(), BicycleControl(.01), p)
    assert initial[4] > 0 and initial[5] > 0


def test_rigid_body_power_equals_independent_wheel_work():
    p = BicycleParameters()
    for delta in (-.1, 0, .1):
        state = BicycleState(vx_mps=40, vy_mps=.5, yaw_rate_radps=.1)
        ctrl = BicycleControl(delta, 2000, -1000, 600)
        rhs, d = bicycle_rhs(state, ctrl, p)
        wheel_vxf = 40*math.cos(delta)+(.5+1.6*.1)*math.sin(delta)
        wheel_vyf = -40*math.sin(delta)+(.5+1.6*.1)*math.cos(delta)
        work = d.front.fx_n*wheel_vxf+d.front.fy_n*wheel_vyf+d.rear.fx_n*40+d.rear.fy_n*(.5-2*.1)-600*40
        energy = 900*(40*rhs[3]+.5*rhs[4])+1500*.1*rhs[5]
        assert energy == pytest.approx(work, abs=1e-7, rel=1e-10)
        assert d.wheel_power_w == pytest.approx(work, abs=1e-7)
        assert d.lateral_slip_power_w <= 1e-9


def test_higher_stiffness_and_load_increase_force_within_the_prior_model():
    base = axle_force(.01, 0, 1000, 20000, 1, 1)
    assert abs(axle_force(.01, 0, 1000, 40000, 1, 1).fy_n) > abs(base.fy_n)
    assert abs(axle_force(.01, 0, 2000, 20000, 1, 1).fy_n) > abs(base.fy_n)
    assert axle_force(0, 0, 1000, 20000, 1, 1).fy_n == 0


def test_invalid_parameters_controls_and_states_abstain_without_clipping():
    for kwargs in ({"mass_kg": 0}, {"mu_y": -1}, {"front_stiffness_nprad": float("nan")},
                   {"min_vx_mps": 120}, {"max_sideslip_rad": 2}):
        with pytest.raises(ValueError, match="parameters"):
            BicycleParameters(**kwargs)
    for kwargs in ({"resistance_n": -1}, {"front_fx_request_n": float("inf")}):
        with pytest.raises(ValueError, match="controls"):
            BicycleControl(**kwargs)
    for state in (BicycleState(vx_mps=0), BicycleState(vy_mps=30), BicycleState(yaw_rate_radps=3), BicycleState(x_m=float("nan"))):
        with pytest.raises(ValueError, match="support"):
            bicycle_rhs(state, BicycleControl(), BicycleParameters())
    with pytest.raises(ValueError, match="steering"):
        bicycle_rhs(BicycleState(), BicycleControl(.5), BicycleParameters())
    with pytest.raises(ValueError, match="six finite"):
        BicycleState.from_array(np.zeros(5))
    with pytest.raises(ValueError, match="axle"):
        axle_force(.1, 0, 0, 20000, 1, 1)
    p = BicycleParameters(max_axle_slip_rad=.01)
    with pytest.raises(ValueError, match="axle support"):
        bicycle_rhs(BicycleState(), BicycleControl(.1), p)
