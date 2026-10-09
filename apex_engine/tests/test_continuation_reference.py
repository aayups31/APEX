from dataclasses import replace

import numpy as np
import pytest

from apexsim.research.continuation_reference import resource_vertices, tiny_continuation_reference
from apexsim.research.continuous_reference import tiny_continuous_reference
from apexsim.research.fienia_strategy import PaperStrategyModel, TireWearCoefficients
from apexsim.research.sac_env import DRY, StrategyLearningEnv, sac_task_model
from apexsim.research.smooth_lap import LapMode, SmoothLapMap
from apexsim.research.strategy_disturbances import apply_wear_shock
from apexsim.sim_core.types import TyreCompound


@pytest.mark.parametrize("compound", DRY)
def test_reset_parity(compound):
    model = sac_task_model()
    result = tiny_continuation_reference(model, model.initial_state(compound))
    old = tiny_continuous_reference(model, compound)
    assert result.remaining_time_s == pytest.approx(old.race_time_s, abs=1e-10)
    assert result.pit_plan == old.pit_plan


def test_partially_spent_battery_vertices():
    vertices = resource_vertices(np.full(2, -1.), np.full(2, .5), -.4, .4, 1.)
    assert np.array(vertices) == pytest.approx(np.array([[-.4, 0.], [.5, -.9]]))
    for vertex in vertices:
        assert np.all(.4 + np.cumsum(vertex) >= -1e-9)
        assert np.all(.4 + np.cumsum(vertex) <= 1 + 1e-9)


def test_one_lap_hand_cost_retains_observed_state():
    model = sac_task_model()
    initial = model.initial_state(TyreCompound.SOFT)
    nominal = model.p.nominal_fuel_energy_mj()
    state = replace(initial, lap=2, fuel_energy_mj=.95 * nominal, car_mass_kg=801.9,
                    battery_mj=.4, tyre_wear=.2, compound_changed=True, outlap=True,
                    race_time_s=200., last_lap_time_s=100.)
    result = tiny_continuation_reference(model, state)
    battery = .37 * (-.4) - .05 * (np.sqrt(.4**2 + .01**2) - .01)
    expected = 92.5 + .028 * 1.9 - .7 * (-.05) + .25 * .2 + 3 * .2**2 + 7 * .2**3 + 15 + battery
    assert result.remaining_time_s == pytest.approx(expected, abs=1e-10)
    assert result.fuel_fractions == pytest.approx((.95,))
    assert result.battery_deltas_mj == pytest.approx((-.4,))
    assert result.pit_plan == (None,)
    with pytest.raises(ValueError, match="legal"):
        tiny_continuation_reference(model, replace(state, compound_changed=False))


def test_two_lap_hand_optimum_uses_original_fuel_allocation():
    model = sac_task_model()
    model = PaperStrategyModel(replace(model.p, battery_recharge_time_s_per_mj=.42), model.wear)
    state = replace(model.initial_state(TyreCompound.SOFT), lap=1, battery_mj=.4,
                    fuel_energy_mj=1.95 * 86, car_mass_kg=803.9, compound_changed=True)
    result = tiny_continuation_reference(model, state)
    assert result.fuel_fractions == pytest.approx((1.05, .9))
    expected = 185 + .028 * (3.9 + 1.8) + .035 - .42 * .4 + .25 * .01 + 3 * .01**2 + 7 * .01**3
    assert result.remaining_time_s == pytest.approx(expected, abs=1e-10)
    assert result.pit_plan == (None, None)


def test_unsupported_family_budget_and_terminal_rejected():
    model = sac_task_model()
    state = model.initial_state()
    with pytest.raises(ValueError, match="budget"):
        tiny_continuation_reference(model, state, max_candidates=1)
    with pytest.raises(ValueError, match="remaining"):
        tiny_continuation_reference(model, replace(state, lap=3, fuel_energy_mj=0,
                                                  battery_mj=0, car_mass_kg=800))
    mass_wear = {c: TireWearCoefficients(1, .001, .01) for c in DRY}
    with pytest.raises(ValueError, match="mass-independent"):
        tiny_continuation_reference(PaperStrategyModel(model.p, mass_wear), state)
    convex = PaperStrategyModel(replace(model.p, battery_recharge_time_s_per_mj=.5), model.wear)
    with pytest.raises(ValueError, match="concave"):
        tiny_continuation_reference(convex, state)
    with pytest.raises(ValueError, match="finite"):
        tiny_continuation_reference(model, replace(state, tyre_wear=float("nan")))


def test_initial_shock_advances_soft_stop():
    model = sac_task_model()
    state = model.initial_state(TyreCompound.SOFT)
    nominal = tiny_continuation_reference(model, state)
    disturbed = tiny_continuation_reference(model, replace(state, tyre_wear=.6))
    assert nominal.pit_plan[0] is None
    assert disturbed.pit_plan[0] == TyreCompound.MEDIUM


@pytest.mark.parametrize("compound", DRY)
@pytest.mark.parametrize("dose", [0., .6, 1.])
def test_observed_continuation_replays_against_independent_smooth_map(compound, dose):
    pytest.importorskip("casadi")
    env = StrategyLearningEnv()
    env.reset(compound)
    env.step(np.array([0., 0.]), 0)
    apply_wear_shock(env, dose)
    result = tiny_continuation_reference(env.model, env.state)
    before_time = env.smooth_time_s
    lap_map = SmoothLapMap(env.model.p, env.model.time_loss, env.eps)
    replay_cost = 0.
    for action in result.actions:
        state = env.state
        mode = (LapMode.OUT_INLAP if state.outlap else LapMode.INLAP) if action.pit_compound else (
            LapMode.OUTLAP if state.outlap else LapMode.NORMAL)
        expected = float(lap_map.functions(state.compound, mode).value(
            [action.fuel_energy_mj, action.battery_delta_mj, state.car_mass_kg, state.tyre_wear]))
        pit_code = 0 if action.pit_compound is None else DRY.index(action.pit_compound) + 1
        step = env.step(env.physical_to_energy(action), pit_code)
        assert not step.transition.wear_clipped
        assert step.smooth_lap_time_s == pytest.approx(expected, abs=1e-8)
        assert step.transition.applied_action.fuel_energy_mj == pytest.approx(action.fuel_energy_mj, abs=1e-7)
        assert step.transition.applied_action.battery_delta_mj == pytest.approx(action.battery_delta_mj, abs=1e-7)
        replay_cost += expected
    assert replay_cost == pytest.approx(result.remaining_time_s, abs=1e-8)
    assert env.smooth_time_s - before_time == pytest.approx(result.remaining_time_s, abs=1e-8)
    assert env.model.final_state_is_legal(env.state)


def test_wear_infeasible_plans_are_excluded_without_clipping():
    model = sac_task_model()
    state = replace(model.initial_state(TyreCompound.SOFT), tyre_wear=1.245)
    result = tiny_continuation_reference(model, state)
    assert result.excluded_wear_plans > 0
    assert result.pit_plan[0] is not None
    with pytest.raises(ValueError, match="unclipped"):
        tiny_continuation_reference(model, state, pit_window=(0, -1))


@pytest.mark.parametrize("budget", [0, -1, True, 1.5])
def test_invalid_budget(budget):
    model = sac_task_model()
    with pytest.raises(ValueError, match="budget"):
        tiny_continuation_reference(model, model.initial_state(), max_candidates=budget)


def test_resource_input_validation():
    for lower, upper, total in [([0.], [1., 2.], 0.), ([2.], [1.], 0.),
                                ([float("nan")], [1.], 0.), ([0.], [1.], 2.)]:
        with pytest.raises(ValueError):
            resource_vertices(np.array(lower), np.array(upper), total)
    with pytest.raises(ValueError, match="together"):
        resource_vertices(np.array([0.]), np.array([1.]), 0., battery_initial=0.)


@pytest.mark.parametrize("compound", DRY)
def test_fixed_plan_cost_monotonic_and_causal_continuation_no_worse(compound):
    model = sac_task_model()
    nominal = tiny_continuation_reference(model, model.initial_state(compound))
    costs = []
    for dose in (0., .6, 1.):
        env = StrategyLearningEnv()
        env.reset(compound)
        first = nominal.actions[0]
        code = 0 if first.pit_compound is None else DRY.index(first.pit_compound) + 1
        env.step(env.physical_to_energy(first), code)
        apply_wear_shock(env, dose)
        reference = tiny_continuation_reference(model, env.state)
        prefix = env.smooth_time_s
        for action in nominal.actions[1:]:
            code = 0 if action.pit_compound is None else DRY.index(action.pit_compound) + 1
            env.step(env.physical_to_energy(action), code)
        assert reference.remaining_time_s <= env.smooth_time_s - prefix + 1e-8
        costs.append(env.smooth_time_s)
    assert costs[0] <= costs[1] <= costs[2]


def test_wear_intervention_only_changes_wear():
    env = StrategyLearningEnv()
    with pytest.raises(RuntimeError, match="reset"):
        apply_wear_shock(env, .6)
    env.reset()
    before, observation = env.state, env.observe().copy()
    apply_wear_shock(env, .6)
    assert env.state == replace(before, tyre_wear=.6)
    assert env.smooth_time_s == env.last_smooth_lap_s == 0
    np.testing.assert_array_equal(np.delete(env.observe(), 6), np.delete(observation, 6))
    assert env.observe()[6] == pytest.approx(.6 / 1.25)
    before = env.state
    for dose in (-1, float("nan"), float("inf"), True, 1., "0.1"):
        with pytest.raises(ValueError):
            apply_wear_shock(env, dose)
        assert env.state is before
    apply_wear_shock(env, 0.)
    assert env.state == before


def test_wear_intervention_after_step_keeps_history_and_rejects_terminal():
    env = StrategyLearningEnv()
    env.reset()
    env.step(np.array([0., 0.]), 1)
    before, elapsed, last = env.state, env.smooth_time_s, env.last_smooth_lap_s
    apply_wear_shock(env, .6)
    assert env.state == replace(before, tyre_wear=.6)
    assert (env.smooth_time_s, env.last_smooth_lap_s) == (elapsed, last)
    env.step(np.array([0., 0.]), 0)
    env.step(np.array([0., 0.]), 0)
    before = env.state
    with pytest.raises(ValueError, match="terminal"):
        apply_wear_shock(env, 0.)
    assert env.state is before
