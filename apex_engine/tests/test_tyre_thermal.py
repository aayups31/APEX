from math import exp

import numpy as np
import pytest

from apexsim.examples.thermal_study import replay_case
from apexsim.research.tyre_thermal import ThermalParameters, ThermalState, heat_step


def test_isolated_tread_heating_has_exact_energy_increase():
    p = ThermalParameters(coupling_w_k=0, road_w_k=0, air_w_k=0)
    step = heat_step(ThermalState(300, 310), 10, tread_w=1200, carcass_w=0, road_k=290, air_k=280, parameters=p)
    assert step.state.tread_k == pytest.approx(302)
    assert step.state.carcass_k == pytest.approx(310)
    assert step.stored_j == pytest.approx(12000)
    assert abs(step.balance_error_j) < 1e-9


def test_adiabatic_exchange_matches_exponential_and_conserves_energy():
    p = ThermalParameters(road_w_k=0, air_w_k=0)
    step = heat_step(ThermalState(360, 300), 15, tread_w=0, carcass_w=0, road_k=290, air_k=280, parameters=p)
    expected = 60*exp(-15*p.coupling_w_k*(1/p.tread_capacity_j_k+1/p.carcass_capacity_j_k))
    assert step.state.tread_k-step.state.carcass_k == pytest.approx(expected)
    assert abs(step.stored_j) < 1e-8


def test_equilibrium_and_heating_then_cooldown():
    bath = dict(road_k=300, air_k=300, carcass_w=0)
    state = ThermalState(300, 300)
    assert heat_step(state, 60, tread_w=0, **bath).state == state
    hot = heat_step(state, 60, tread_w=2000, **bath).state
    cooled = heat_step(hot, 600, tread_w=0, **bath).state
    assert hot.tread_k > hot.carcass_k > 300
    assert 300 < cooled.tread_k < hot.tread_k
    assert 300 < cooled.carcass_k < hot.carcass_k


@pytest.mark.parametrize("temperature", [0, -1, float("nan"), float("inf")])
def test_invalid_kelvin_rejected(temperature):
    with pytest.raises(ValueError, match="kelvin"):
        heat_step(ThermalState(temperature, 300), 1, tread_w=0, carcass_w=0, road_k=300, air_k=300)


def test_short_vehicle_replay_matches_independent_integrator():
    times = np.array([0., .1, .3])
    states = np.array([[0., 0., 0., 30., .3, .02]]*3)
    controls = np.array([[.02, 0., 100., 100.]]*2)
    metrics, temperatures = replay_case(times, states, controls)
    assert metrics["passed"] and temperatures.shape == (3, 2, 2)
    assert all(row[0] > 0 for row in metrics["energy_j_source_road_air_stored"])
