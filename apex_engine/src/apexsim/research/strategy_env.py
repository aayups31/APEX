"""Gym-like lap-level environment for the Fieni et al. strategy model."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from apexsim.research.fienia_strategy import PaperStrategyAction, PaperStrategyModel, PaperStrategyState
from apexsim.sim_core.types import TyreCompound


@dataclass(frozen=True)
class EnvStep:
    observation: np.ndarray
    reward: float
    terminated: bool
    truncated: bool
    info: dict


class PaperStrategyEnv:
    """Dependency-free environment with the paper's 10-value observation.

    Observation order:
    battery, fuel energy, mass, race time, compound-change flag, compound code,
    tyre wear, outlap flag, current lap time, laps remaining.
    """

    def __init__(self, model: PaperStrategyModel | None = None) -> None:
        self.model = model or PaperStrategyModel()
        self.state: PaperStrategyState | None = None

    @staticmethod
    def _compound_code(compound: TyreCompound) -> float:
        return {TyreCompound.SOFT: 1.0, TyreCompound.MEDIUM: 2.0, TyreCompound.HARD: 3.0}[compound]

    def observe(self, state: PaperStrategyState | None = None) -> np.ndarray:
        s = state or self.state
        if s is None:
            raise RuntimeError("Call reset() before observe()")
        return np.asarray(
            [
                s.battery_mj,
                s.fuel_energy_mj,
                s.car_mass_kg,
                s.race_time_s,
                float(s.compound_changed),
                self._compound_code(s.compound),
                s.tyre_wear,
                float(s.outlap),
                s.last_lap_time_s,
                float(self.model.p.total_laps - s.lap),
            ],
            dtype=np.float32,
        )

    def reset(self, initial_compound: TyreCompound = TyreCompound.MEDIUM) -> tuple[np.ndarray, dict]:
        self.state = self.model.initial_state(initial_compound)
        return self.observe(), {"state": self.state}

    def step(self, action: PaperStrategyAction | tuple[float, float, int]) -> EnvStep:
        if self.state is None:
            raise RuntimeError("Call reset() before step()")
        physical = action
        if not isinstance(action, PaperStrategyAction):
            physical = self.model.action_from_normalized(*action)
        next_state, transition = self.model.transition(self.state, physical)
        self.state = next_state
        reward = self.model.p.reward_offset_s - transition.lap_time_s
        terminated = self.model.is_done(next_state)
        if terminated and not self.model.final_state_is_legal(next_state):
            reward -= 1_000.0
        return EnvStep(
            observation=self.observe(next_state),
            reward=float(reward),
            terminated=terminated,
            truncated=False,
            info={"transition": transition, "state": next_state},
        )
