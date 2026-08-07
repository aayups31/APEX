from apexsim.sim_core.track import TrackMap
from apexsim.sim_core.types import CarParameters, CarState, Control, DriverParameters, EnvironmentState
from apexsim.sim_core.vehicle import VehicleDynamics


def test_vehicle_accelerates_and_consumes_resources():
    track = TrackMap.synthetic(length_m=3000.0, points=500, seed=2)
    car = CarParameters(reliability_per_hour=1.0)
    driver = DriverParameters("test", consistency=1.0, seed=1)
    state = CarState("car", "test", speed_mps=25.0, fuel_kg=80.0, battery_mj=4.0)
    dynamics = VehicleDynamics()
    next_state, diagnostics = dynamics.step(
        state,
        Control(throttle=1.0, ers_deploy=1.0),
        car,
        driver,
        track,
        EnvironmentState(),
        0.2,
        drs_eligible=False,
    )
    assert next_state.speed_mps > state.speed_mps
    assert next_state.fuel_kg < state.fuel_kg
    assert next_state.battery_mj < state.battery_mj
    assert diagnostics.traction_limit_n > 0
