"""Portable race-state/action interface inspired by Thomas et al. (2026)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import numpy as np

from apexsim.sim_core.types import TyreCompound


class UnifiedPitAction(IntEnum):
    NO_PIT = 0
    PIT_SOFT = 1
    PIT_MEDIUM = 2
    PIT_HARD = 3

    @property
    def compound(self) -> TyreCompound | None:
        return {
            UnifiedPitAction.NO_PIT: None,
            UnifiedPitAction.PIT_SOFT: TyreCompound.SOFT,
            UnifiedPitAction.PIT_MEDIUM: TyreCompound.MEDIUM,
            UnifiedPitAction.PIT_HARD: TyreCompound.HARD,
        }[self]


@dataclass(frozen=True)
class UnifiedRaceState:
    terminal: bool
    track_id: int
    safety_car: bool
    position: int
    race_progress: float
    current_compound: TyreCompound
    tyre_degradation_s: float
    soft_sets_remaining: int
    medium_sets_remaining: int
    hard_sets_remaining: int
    gap_ahead_s: float
    gap_behind_s: float
    gap_leader_s: float
    last_lap_relative_s: float
    valid_finish: bool

    def vector(self) -> np.ndarray:
        compound_code = {TyreCompound.SOFT: 0, TyreCompound.MEDIUM: 1, TyreCompound.HARD: 2}.get(self.current_compound, 3)
        return np.asarray(
            [
                float(self.terminal),
                float(self.track_id),
                float(self.safety_car),
                float(self.position),
                float(np.clip(self.race_progress, 0.0, 1.0)),
                float(compound_code),
                float(self.tyre_degradation_s),
                float(self.soft_sets_remaining),
                float(self.medium_sets_remaining),
                float(self.hard_sets_remaining),
                float(self.gap_ahead_s),
                float(self.gap_behind_s),
                float(self.gap_leader_s),
                float(self.last_lap_relative_s),
                float(self.valid_finish),
            ],
            dtype=np.float32,
        )


F1_POINTS = np.asarray([25, 18, 15, 12, 10, 8, 6, 4, 2, 1], dtype=float)


def rsrl_reward(state: UnifiedRaceState, action: UnifiedPitAction, next_state: UnifiedRaceState) -> float:
    """Reward topology used by the RSRL paper, with explicit validity checks."""
    available = {
        UnifiedPitAction.PIT_SOFT: state.soft_sets_remaining,
        UnifiedPitAction.PIT_MEDIUM: state.medium_sets_remaining,
        UnifiedPitAction.PIT_HARD: state.hard_sets_remaining,
    }
    if action in available and available[action] <= 0:
        return -1000.0
    if next_state.terminal and not next_state.valid_finish:
        return -1000.0
    if action != UnifiedPitAction.NO_PIT and state.valid_finish:
        return -10.0
    if next_state.terminal:
        return float(100.0 * F1_POINTS[next_state.position - 1]) if 1 <= next_state.position <= 10 else 0.0
    return 1.0
