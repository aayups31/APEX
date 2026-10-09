"""R017 learning wrapper with the R016 domain and R015 objective; no fitted data."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite, sqrt

import numpy as np
from numpy.typing import ArrayLike

from apexsim.research.fienia_strategy import (
    PaperStrategyAction,
    PaperStrategyModel,
    PaperStrategyParameters,
    PaperStrategyState,
    TireWearCoefficients,
    TransitionInfo,
)
from apexsim.research.strategy_env import PaperStrategyEnv
from apexsim.sim_core.types import TyreCompound

DRY = (TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD)


def sac_task_model() -> PaperStrategyModel:
    """Frozen three-lap synthetic task; compatible with the independent tiny reference."""
    return PaperStrategyModel(PaperStrategyParameters(total_laps=3, initial_fuel_kg=6, battery_capacity_mj=1,
                                                     battery_delta_min_mj=-1, battery_delta_max_mj=.5),
                              wear_coefficients={c: TireWearCoefficients(1., 0., .01) for c in DRY})


@dataclass(frozen=True)
class LearningStep:
    observation: np.ndarray
    reward: float
    terminated: bool
    mask: np.ndarray
    transition: TransitionInfo
    smooth_lap_time_s: float


class StrategyLearningEnv:
    """Ten normalized state fields, energy in [-1,1]^2, pit codes 0..3.

    Smooth times replace elapsed/last-lap time in the learning observation only.
    Physical resource projection and pit masks enforce constraints, not learned legality.
    """

    def __init__(self, model: PaperStrategyModel | None = None, pit_window: tuple[int, int] = (0, 1),
                 battery_smoothing_mj: float = .01) -> None:
        self.model = model or sac_task_model()
        n = self.model.p.total_laps
        p = self.model.p
        pace = (p.nominal_lap_time_s, p.mass_time_s_per_kg, p.fuel_energy_time_s_per_fraction,
                p.battery_deploy_time_s_per_mj, p.battery_recharge_time_s_per_mj,
                p.pit_inlap_penalty_s, p.pit_outlap_penalty_s, p.consecutive_pit_penalty_s,
                *(v for c in self.model.time_loss.values() for v in vars(c).values()))
        if not all(isfinite(v) and v >= 0 for v in pace) or p.nominal_lap_time_s <= 0:
            raise ValueError("Learning maps require positive nominal time and nonnegative finite pace coefficients")
        if (n > 8 or len(pit_window) != 2 or any(type(i) is not int for i in pit_window)
                or not 0 <= pit_window[0] <= pit_window[1] < n - 1):
            raise ValueError("Learning pit window must precede the final lap in a horizon <=8")
        if not isfinite(battery_smoothing_mj) or battery_smoothing_mj <= 0:
            raise ValueError("Learning smoothing must be finite and positive")
        self.window, self.eps = pit_window, battery_smoothing_mj
        self.base = PaperStrategyEnv(self.model)
        self.smooth_time_s = self.last_smooth_lap_s = 0.

    @property
    def state(self) -> PaperStrategyState:
        if self.base.state is None:
            raise RuntimeError("Call reset before accessing learning state")
        return self.base.state

    def observe(self) -> np.ndarray:
        s, p = self.state, self.model.p
        # Avoid converting large physical quantities to float32 before centering/scaling.
        values = [s.battery_mj / max(p.battery_capacity_mj, 1.),
                  s.fuel_energy_mj / p.initial_fuel_energy_mj(),
                  (s.car_mass_kg - p.empty_mass_kg) / p.initial_fuel_kg,
                  self.smooth_time_s / (p.total_laps * p.nominal_lap_time_s),
                  float(s.compound_changed), self.base._compound_code(s.compound) / 3.,
                  s.tyre_wear / 1.25, float(s.outlap), self.last_smooth_lap_s / p.nominal_lap_time_s,
                  (p.total_laps - s.lap) / p.total_laps]
        observation = np.array(values, dtype=np.float32)
        if not np.isfinite(observation).all():
            raise ValueError("Learning observation is nonfinite")
        return observation

    def action_mask(self) -> np.ndarray:
        s = self.state
        mask = np.array([True, False, False, False])
        if self.window[0] <= s.lap <= self.window[1]:
            mask[:] = True
            if self.model.p.require_compound_change and not s.compound_changed and s.lap == self.window[1]:
                mask[0] = False
                mask[int(self.base._compound_code(s.compound))] = False
        return mask

    def reset(self, initial_compound: TyreCompound = TyreCompound.MEDIUM) -> tuple[np.ndarray, np.ndarray]:
        if not isinstance(initial_compound, TyreCompound) or initial_compound not in DRY:
            raise ValueError("Learning task requires a dry TyreCompound")
        self.base.reset(initial_compound)
        self.smooth_time_s = self.last_smooth_lap_s = 0.
        return self.observe(), self.action_mask()

    def step(self, energy: ArrayLike, pit_code: int) -> LearningStep:
        s, p = self.state, self.model.p
        if self.model.is_done(s):
            raise RuntimeError("Cannot step a terminated learning episode")
        energy = np.asarray(energy, dtype=float)
        if energy.shape != (2,) or not np.isfinite(energy).all() or np.any(abs(energy) > 1):
            raise ValueError("Learning energy action must be two finite values in [-1,1]")
        if type(pit_code) is not int or not 0 <= pit_code < 4 or not self.action_mask()[pit_code]:
            raise ValueError("Learning pit choice violates the discrete constraint mask")
        action = self.model.action_from_normalized((energy[0] + 1) / 2, energy[1], pit_code)
        state, transition = self.model.transition(s, action)
        if transition.wear_clipped:
            raise ValueError("Learning transition requires unsupported tyre-wear clipping")
        d = transition.applied_action.battery_delta_mj
        correction = ((p.battery_recharge_time_s_per_mj - p.battery_deploy_time_s_per_mj) / 2
                      * (sqrt(d * d + self.eps * self.eps) - self.eps - abs(d)))
        smooth = transition.lap_time_s + correction
        if not isfinite(smooth) or smooth <= 0:
            raise ValueError("Learning smooth lap cost is invalid")
        terminated = self.model.is_done(state)
        if terminated and not self.model.final_state_is_legal(state):
            raise ValueError("Learning episode violates terminal legality")
        self.base.state = state
        self.smooth_time_s += smooth
        self.last_smooth_lap_s = smooth
        return LearningStep(self.observe(), p.nominal_lap_time_s - smooth, terminated, self.action_mask(), transition, smooth)

    def metadata(self) -> dict:
        return {"schema_version": "apex-sac-env-v1", "classification": "ADAPTATION",
                "parameters": asdict(self.model.p), "pit_window": list(self.window), "battery_smoothing_mj": self.eps,
                "wear": {k.value: asdict(v) for k, v in self.model.wear.items()},
                "time_loss": {k.value: asdict(v) for k, v in self.model.time_loss.items()},
                "observation": "ten normalized paper state fields; smooth elapsed/last-lap times",
                "reward": "nominal_lap_time_s - smooth_lap_time_s; gamma=1, finite horizon",
                "legality": "energy reachability projection plus explicit pit/required-change masks; not learned"}

    def physical_to_energy(self, action: PaperStrategyAction) -> np.ndarray:
        """Inverse of the starter's normalized control map, for matched rule evaluation."""
        p = self.model.p
        fuel = (action.fuel_energy_mj / p.nominal_fuel_energy_mj() - 1) / .1
        midpoint = (p.battery_delta_max_mj + p.battery_delta_min_mj) / 2
        halfspan = (p.battery_delta_max_mj - p.battery_delta_min_mj) / 2
        energy = np.array([fuel, (midpoint - action.battery_delta_mj) / halfspan])
        if not np.isfinite(energy).all() or np.any(abs(energy) > 1 + 1e-12):
            raise ValueError("Physical rule action is outside the normalized energy domain")
        # Inverse-map roundoff only: .1/ .1 can land a few ulps outside a bound.
        return np.clip(energy, -1., 1.)
