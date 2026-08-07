from apexsim.research.fienia_strategy import (
    DiscreteStrategyOracle,
    PaperStrategyAction,
    PaperStrategyModel,
    PaperStrategyParameters,
)
from apexsim.research.strategy_env import PaperStrategyEnv
from apexsim.sim_core.types import TyreCompound


def test_paper_strategy_state_conservation_and_pit_reset():
    model = PaperStrategyModel(PaperStrategyParameters(total_laps=4, initial_fuel_kg=8.0))
    state = model.initial_state(TyreCompound.SOFT)
    normal = PaperStrategyAction(model.p.nominal_fuel_energy_mj(), -0.5)
    state, _ = model.transition(state, normal)
    assert state.tyre_wear > 0
    assert state.fuel_energy_mj < model.p.initial_fuel_energy_mj()
    assert state.battery_mj < model.p.battery_capacity_mj

    pit = PaperStrategyAction(model.p.nominal_fuel_energy_mj(), 0.0, TyreCompound.HARD)
    state, _ = model.transition(state, pit)
    assert state.tyre_wear == 0.0
    assert state.compound == TyreCompound.HARD
    assert state.compound_changed
    assert state.outlap


def test_normalized_action_and_environment_shape():
    model = PaperStrategyModel(PaperStrategyParameters(total_laps=3, initial_fuel_kg=6.0))
    action = model.action_from_normalized(0.5, 1.0, 1)
    assert action.pit_compound == TyreCompound.SOFT
    assert action.battery_delta_mj < 0

    env = PaperStrategyEnv(model)
    observation, _ = env.reset()
    assert observation.shape == (10,)
    step = env.step((0.5, 0.0, 0))
    assert step.observation.shape == (10,)
    assert not step.truncated


def test_discrete_oracle_completes_and_changes_compound():
    parameters = PaperStrategyParameters(total_laps=5, initial_fuel_kg=10.0)
    model = PaperStrategyModel(parameters)
    oracle = DiscreteStrategyOracle(model, beam_width=96, pit_window=(1, 3))
    result = oracle.solve(TyreCompound.MEDIUM)
    assert result.state.lap == 5
    assert result.state.compound_changed
    assert len(result.actions) == 5
    assert result.state.race_time_s > 0
