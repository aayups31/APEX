from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any


class TyreCompound(str, Enum):
    SOFT = "SOFT"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    INTERMEDIATE = "INTERMEDIATE"
    WET = "WET"


class PaceMode(str, Enum):
    CONSERVE = "CONSERVE"
    HOLD = "HOLD"
    PUSH = "PUSH"
    ATTACK = "ATTACK"
    QUALIFY = "QUALIFY"


class FlagState(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    VSC = "VSC"
    SAFETY_CAR = "SAFETY_CAR"
    RED = "RED"


@dataclass(frozen=True)
class CarParameters:
    """Public-data-calibratable, intentionally simplified car parameters.

    These are not claimed to be confidential team parameters. They are a compact
    semi-empirical parameterization that can be fit from public telemetry.
    """

    name: str = "generic_2025"
    dry_mass_kg: float = 800.0
    max_power_kw: float = 740.0
    max_brake_force_n: float = 28_000.0
    drag_area_m2: float = 1.05
    downforce_area_m2: float = 3.2
    rolling_resistance_coeff: float = 0.015
    drivetrain_efficiency: float = 0.92
    fuel_capacity_kg: float = 110.0
    fuel_burn_kg_per_km: float = 0.028
    ers_capacity_mj: float = 4.0
    ers_max_deploy_kw: float = 120.0
    ers_max_harvest_kw: float = 120.0
    pit_speed_limit_mps: float = 22.22
    pit_stationary_time_s: float = 2.6
    reliability_per_hour: float = 0.998
    dirty_air_downforce_loss_max: float = 0.18
    drs_drag_reduction: float = 0.16


@dataclass(frozen=True)
class DriverParameters:
    name: str
    aggression: float = 0.65
    consistency: float = 0.92
    tyre_management: float = 0.70
    wet_skill: float = 0.70
    overtaking: float = 0.65
    defending: float = 0.60
    reaction_s: float = 0.20
    pace_offset: float = 0.0
    error_rate_per_hour: float = 0.05
    seed: int = 0


@dataclass(frozen=True)
class Control:
    throttle: float = 0.0
    brake: float = 0.0
    steering: float = 0.0
    ers_deploy: float = 0.0
    drs: bool = False

    def clipped(self) -> Control:
        return Control(
            throttle=min(max(float(self.throttle), 0.0), 1.0),
            brake=min(max(float(self.brake), 0.0), 1.0),
            steering=min(max(float(self.steering), -1.0), 1.0),
            ers_deploy=min(max(float(self.ers_deploy), 0.0), 1.0),
            drs=bool(self.drs),
        )


@dataclass(frozen=True)
class EnvironmentState:
    air_temp_c: float = 25.0
    track_temp_c: float = 35.0
    rain_intensity: float = 0.0
    standing_water: float = 0.0
    wind_speed_mps: float = 2.0
    wind_direction_rad: float = 0.0
    surface_grip: float = 1.0
    flag: FlagState = FlagState.GREEN


@dataclass
class CarState:
    car_id: str
    driver_id: str
    time_s: float = 0.0
    lap: int = 1
    s_m: float = 0.0
    speed_mps: float = 0.0
    fuel_kg: float = 100.0
    battery_mj: float = 4.0
    tyre_compound: TyreCompound = TyreCompound.MEDIUM
    tyre_age_laps: float = 0.0
    tyre_health: float = 1.0
    tyre_temp_c: float = 90.0
    damage: float = 0.0
    in_pit: bool = False
    pit_timer_s: float = 0.0
    pending_compound: TyreCompound | None = None
    retired: bool = False
    finished: bool = False
    total_distance_m: float = 0.0
    last_lap_time_s: float | None = None
    current_lap_start_s: float = 0.0
    position: int = 0
    gap_ahead_m: float | None = None
    gap_to_leader_s: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def clone(self, **changes: Any) -> CarState:
        metadata = changes.pop("metadata", dict(self.metadata))
        return replace(self, metadata=dict(metadata), **changes)


@dataclass(frozen=True)
class PitStopPlan:
    lap: int
    compound: TyreCompound
    minimum_lap: int | None = None
    maximum_lap: int | None = None

    def should_trigger(self, current_lap: int) -> bool:
        lo = self.minimum_lap if self.minimum_lap is not None else self.lap
        hi = self.maximum_lap if self.maximum_lap is not None else self.lap
        return lo <= current_lap <= hi


@dataclass
class RaceEntry:
    car_id: str
    driver: DriverParameters
    car: CarParameters = field(default_factory=CarParameters)
    initial_compound: TyreCompound = TyreCompound.MEDIUM
    strategy: list[PitStopPlan] = field(default_factory=list)
    pace_mode: PaceMode = PaceMode.HOLD
    grid_position: int = 1


@dataclass(frozen=True)
class RaceControlEvent:
    start_s: float
    end_s: float
    flag: FlagState
    description: str = ""


@dataclass(frozen=True)
class WeatherKeyframe:
    time_s: float
    air_temp_c: float = 25.0
    track_temp_c: float = 35.0
    rain_intensity: float = 0.0
    standing_water: float = 0.0
    surface_grip: float = 1.0
    wind_speed_mps: float = 2.0
    wind_direction_rad: float = 0.0


@dataclass(frozen=True)
class SimulationConfig:
    dt_s: float = 0.20
    total_laps: int = 10
    random_seed: int = 42
    drs_enabled_from_lap: int = 3
    drs_detection_gap_s: float = 1.0
    minimum_follow_gap_m: float = 7.0
    pit_entry_window_m: float = 130.0
    pit_lane_time_loss_s: float = 18.0
    yellow_speed_factor: float = 0.72
    vsc_speed_factor: float = 0.62
    safety_car_speed_factor: float = 0.46
    max_simulation_time_s: float = 18_000.0
    telemetry_stride: int = 1


@dataclass(frozen=True)
class StepDiagnostics:
    acceleration_mps2: float
    longitudinal_force_n: float
    traction_limit_n: float
    drag_n: float
    rolling_resistance_n: float
    downforce_n: float
    lateral_acceleration_mps2: float
    effective_grip: float
    tyre_wear_delta: float
    fuel_burn_kg: float
    battery_delta_mj: float
    speed_limit_mps: float
    dirty_air_factor: float
    drs_active: bool
