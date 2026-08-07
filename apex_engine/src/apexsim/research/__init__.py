"""Paper-driven research layer for Project APEX."""

from apexsim.research.fienia_strategy import (
    DiscreteStrategyOracle,
    PaperStrategyAction,
    PaperStrategyModel,
    PaperStrategyParameters,
    PaperStrategyState,
)
from apexsim.research.registry import PaperRecord, default_registry, registry_frame
from apexsim.research.state_space_tyre import LatentTyreDegradationFilter
from apexsim.research.strategy_env import PaperStrategyEnv
from apexsim.research.tyre_energy import TyreEnergyInputs, WheelTyreEnergy, estimate_wheel_tyre_energy
from apexsim.research.tyre_forecasting import GRUTyreEnergyForecaster, RidgeTyreEnergyForecaster
from apexsim.research.unified_race import UnifiedPitAction, UnifiedRaceState, rsrl_reward

__all__ = [
    "DiscreteStrategyOracle",
    "GRUTyreEnergyForecaster",
    "LatentTyreDegradationFilter",
    "PaperRecord",
    "PaperStrategyAction",
    "PaperStrategyEnv",
    "PaperStrategyModel",
    "PaperStrategyParameters",
    "PaperStrategyState",
    "RidgeTyreEnergyForecaster",
    "TyreEnergyInputs",
    "UnifiedPitAction",
    "UnifiedRaceState",
    "WheelTyreEnergy",
    "default_registry",
    "estimate_wheel_tyre_energy",
    "registry_frame",
    "rsrl_reward",
]
