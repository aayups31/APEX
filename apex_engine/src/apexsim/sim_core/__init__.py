"""APEX complete-simulation vertical slice.

The original :mod:`apexsim` package focuses on learned telemetry forecasting.
This subpackage adds the deterministic and stochastic race-simulation layer
that the world model can later correct with learned residuals.
"""

from apexsim.sim_core.driver import ReferenceDriverPolicy
from apexsim.sim_core.race import RaceResult, RaceSimulator
from apexsim.sim_core.strategy import MonteCarloStrategyPlanner
from apexsim.sim_core.track import TrackMap
from apexsim.sim_core.types import (
    CarParameters,
    CarState,
    Control,
    DriverParameters,
    EnvironmentState,
    FlagState,
    PaceMode,
    PitStopPlan,
    RaceControlEvent,
    RaceEntry,
    SimulationConfig,
    TyreCompound,
    WeatherKeyframe,
)
from apexsim.sim_core.vehicle import VehicleDynamics

__all__ = [
    "CarParameters",
    "CarState",
    "Control",
    "DriverParameters",
    "EnvironmentState",
    "FlagState",
    "MonteCarloStrategyPlanner",
    "PaceMode",
    "PitStopPlan",
    "RaceControlEvent",
    "RaceEntry",
    "RaceResult",
    "RaceSimulator",
    "ReferenceDriverPolicy",
    "SimulationConfig",
    "TrackMap",
    "TyreCompound",
    "VehicleDynamics",
    "WeatherKeyframe",
]
