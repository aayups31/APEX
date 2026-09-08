"""Research implementation scaffold for Fieni et al. (2025).

The module preserves the paper's causal structure at lap resolution:

* battery and fuel energy states,
* fuel-mass coupling,
* compound-dependent tyre wear,
* normal/inlap/outlap lap-time maps,
* mixed continuous/discrete strategy actions,
* a Markov state suitable for optimization and reinforcement learning.

It is not a claim of numerical replication. The paper's confidential lap maps and
identified coefficients are unavailable. The defaults are transparent synthetic
surrogates that must be calibrated before any real-race conclusion is made.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np

from apexsim.sim_core.types import TyreCompound

_DRY_COMPOUNDS = (TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD)


@dataclass(frozen=True)
class TireWearCoefficients:
    """Coefficients for TW[k+1] = a*TW[k] + b*m[k]/m[0] + c."""

    a: float
    b: float
    c: float


@dataclass(frozen=True)
class TireTimeLossCoefficients:
    """Smooth surrogate for the paper's twice-differentiable N_j(TW) map."""

    fresh_loss_s: float
    linear_s: float
    quadratic_s: float
    cubic_s: float = 0.0

    def evaluate(self, wear: float) -> float:
        w = float(np.clip(wear, 0.0, 1.25))
        return float(self.fresh_loss_s + self.linear_s * w + self.quadratic_s * w**2 + self.cubic_s * w**3)


@dataclass(frozen=True)
class PaperStrategyParameters:
    total_laps: int = 57
    empty_mass_kg: float = 800.0
    initial_fuel_kg: float = 105.0
    fuel_lhv_mj_per_kg: float = 43.0
    battery_capacity_mj: float = 4.0
    battery_delta_min_mj: float = -1.25  # negative means deployment
    battery_delta_max_mj: float = 0.75   # positive means recharge
    nominal_lap_time_s: float = 92.5
    pit_inlap_penalty_s: float = 11.5
    pit_outlap_penalty_s: float = 15.0
    consecutive_pit_penalty_s: float = 26.5
    mass_time_s_per_kg: float = 0.028
    fuel_energy_time_s_per_fraction: float = 0.70
    battery_deploy_time_s_per_mj: float = 0.42
    battery_recharge_time_s_per_mj: float = 0.32
    reward_offset_s: float = 130.0
    require_compound_change: bool = True

    def nominal_fuel_energy_mj(self) -> float:
        return self.initial_fuel_kg * self.fuel_lhv_mj_per_kg / self.total_laps

    def initial_fuel_energy_mj(self) -> float:
        return self.initial_fuel_kg * self.fuel_lhv_mj_per_kg


DEFAULT_WEAR: dict[TyreCompound, TireWearCoefficients] = {
    TyreCompound.SOFT: TireWearCoefficients(a=1.035, b=0.0045, c=0.0100),
    TyreCompound.MEDIUM: TireWearCoefficients(a=1.026, b=0.0035, c=0.0070),
    TyreCompound.HARD: TireWearCoefficients(a=1.019, b=0.0028, c=0.0045),
}

DEFAULT_TIME_LOSS: dict[TyreCompound, TireTimeLossCoefficients] = {
    TyreCompound.SOFT: TireTimeLossCoefficients(0.0, 0.25, 3.0, 7.0),
    TyreCompound.MEDIUM: TireTimeLossCoefficients(0.85, 0.18, 2.2, 5.0),
    TyreCompound.HARD: TireTimeLossCoefficients(1.75, 0.12, 1.5, 3.2),
}


@dataclass(frozen=True)
class PaperStrategyState:
    lap: int
    battery_mj: float
    fuel_energy_mj: float
    car_mass_kg: float
    race_time_s: float
    compound_changed: bool
    compound: TyreCompound
    tyre_wear: float
    outlap: bool
    last_lap_time_s: float = 0.0

    @property
    def done(self) -> bool:
        return False  # model owns total_laps; use PaperStrategyModel.is_done


@dataclass(frozen=True)
class PaperStrategyAction:
    """One lap-level strategy action.

    fuel_energy_mj is positive consumption. battery_delta_mj is the change in
    stored battery energy: negative deploys energy; positive recharges it.
    """

    fuel_energy_mj: float
    battery_delta_mj: float
    pit_compound: TyreCompound | None = None


@dataclass(frozen=True)
class TransitionInfo:
    requested_action: PaperStrategyAction
    applied_action: PaperStrategyAction
    lap_time_s: float
    tyre_time_loss_s: float
    nominal_time_s: float
    action_projected: bool


class PaperStrategyModel:
    """Transparent lap-level model matching the paper's state/action topology."""

    def __init__(
        self,
        parameters: PaperStrategyParameters | None = None,
        wear_coefficients: dict[TyreCompound, TireWearCoefficients] | None = None,
        time_loss_coefficients: dict[TyreCompound, TireTimeLossCoefficients] | None = None,
    ) -> None:
        self.p = parameters or PaperStrategyParameters()
        if self.p.total_laps <= 0:
            raise ValueError("total_laps must be positive")
        self.wear = dict(wear_coefficients or DEFAULT_WEAR)
        self.time_loss = dict(time_loss_coefficients or DEFAULT_TIME_LOSS)
        missing = set(_DRY_COMPOUNDS) - self.wear.keys()
        if missing:
            raise ValueError(f"Missing wear coefficients for {sorted(x.value for x in missing)}")

    def initial_state(self, compound: TyreCompound = TyreCompound.MEDIUM) -> PaperStrategyState:
        self._validate_compound(compound)
        return PaperStrategyState(
            lap=0,
            battery_mj=self.p.battery_capacity_mj,
            fuel_energy_mj=self.p.initial_fuel_energy_mj(),
            car_mass_kg=self.p.empty_mass_kg + self.p.initial_fuel_kg,
            race_time_s=0.0,
            compound_changed=False,
            compound=compound,
            tyre_wear=0.0,
            outlap=False,
            last_lap_time_s=0.0,
        )

    def is_done(self, state: PaperStrategyState) -> bool:
        return state.lap >= self.p.total_laps

    def action_from_normalized(
        self,
        fuel: float,
        battery: float,
        pit_code: int = 0,
    ) -> PaperStrategyAction:
        """Map the paper's normalized action to physical units.

        ``fuel`` is clipped to [0, 1] and mapped to [90%, 110%] of nominal
        fuel allocation. ``battery`` is clipped to [-1, 1]; positive normalized
        values mean deployment, matching the paper, and are mapped to a negative
        stored-energy delta in this implementation.
        """
        f = float(np.clip(fuel, 0.0, 1.0))
        b = float(np.clip(battery, -1.0, 1.0))
        fuel_fraction = 0.90 + 0.20 * f
        if b >= 0.0:
            battery_delta = -b * abs(self.p.battery_delta_min_mj)
        else:
            battery_delta = -b * self.p.battery_delta_max_mj
        pit_map = {0: None, 1: TyreCompound.SOFT, 2: TyreCompound.MEDIUM, 3: TyreCompound.HARD}
        if pit_code not in pit_map:
            raise ValueError("pit_code must be 0, 1, 2, or 3")
        return PaperStrategyAction(
            fuel_energy_mj=fuel_fraction * self.p.nominal_fuel_energy_mj(),
            battery_delta_mj=battery_delta,
            pit_compound=pit_map[pit_code],
        )

    def _validate_compound(self, compound: TyreCompound) -> None:
        if compound not in _DRY_COMPOUNDS:
            raise ValueError("The paper replication model supports dry compounds only")

    def _project_action(self, state: PaperStrategyState, action: PaperStrategyAction) -> PaperStrategyAction:
        laps_after = max(self.p.total_laps - state.lap - 1, 0)
        nominal = self.p.nominal_fuel_energy_mj()
        min_fuel = 0.90 * nominal
        max_fuel = 1.10 * nominal

        requested_fuel = float(np.clip(action.fuel_energy_mj, min_fuel, max_fuel))
        # Backward-reachable interval: leave enough fuel for minimum allocation,
        # but not so much that maximum allocation cannot consume it by the finish.
        remaining_min = laps_after * min_fuel
        remaining_max = laps_after * max_fuel
        lower_consume = max(min_fuel, state.fuel_energy_mj - remaining_max)
        upper_consume = min(max_fuel, state.fuel_energy_mj - remaining_min)
        if upper_consume < lower_consume:
            upper_consume = lower_consume
        fuel = float(np.clip(requested_fuel, lower_consume, upper_consume))
        fuel = min(fuel, state.fuel_energy_mj)

        requested_delta = float(np.clip(
            action.battery_delta_mj,
            self.p.battery_delta_min_mj,
            self.p.battery_delta_max_mj,
        ))
        delta = requested_delta
        delta = min(delta, self.p.battery_capacity_mj - state.battery_mj)
        delta = max(delta, -state.battery_mj)
        # Ensure remaining deployment capacity can empty the battery by race end.
        max_energy_that_can_remain = laps_after * abs(self.p.battery_delta_min_mj)
        next_battery = state.battery_mj + delta
        if next_battery > max_energy_that_can_remain and laps_after > 0:
            delta -= next_battery - max_energy_that_can_remain
        if laps_after == 0:
            delta = -state.battery_mj
        delta = float(np.clip(delta, -state.battery_mj, self.p.battery_capacity_mj - state.battery_mj))

        pit = action.pit_compound
        if pit is not None:
            self._validate_compound(pit)
        return PaperStrategyAction(fuel, delta, pit)

    def _nominal_lap_time(self, state: PaperStrategyState, action: PaperStrategyAction) -> float:
        fuel_fraction = action.fuel_energy_mj / max(self.p.nominal_fuel_energy_mj(), 1e-9)
        mass_penalty = self.p.mass_time_s_per_kg * (state.car_mass_kg - self.p.empty_mass_kg)
        fuel_benefit = self.p.fuel_energy_time_s_per_fraction * (fuel_fraction - 1.0)
        if action.battery_delta_mj < 0.0:
            battery_term = self.p.battery_deploy_time_s_per_mj * action.battery_delta_mj
        else:
            battery_term = self.p.battery_recharge_time_s_per_mj * action.battery_delta_mj

        pit_now = action.pit_compound is not None
        if pit_now and state.outlap:
            pit_penalty = self.p.consecutive_pit_penalty_s
        elif pit_now:
            pit_penalty = self.p.pit_inlap_penalty_s
        elif state.outlap:
            pit_penalty = self.p.pit_outlap_penalty_s
        else:
            pit_penalty = 0.0
        return float(self.p.nominal_lap_time_s + mass_penalty - fuel_benefit + battery_term + pit_penalty)

    def transition(self, state: PaperStrategyState, action: PaperStrategyAction) -> tuple[PaperStrategyState, TransitionInfo]:
        if self.is_done(state):
            raise RuntimeError("Cannot transition a completed race")
        applied = self._project_action(state, action)
        nominal_time = self._nominal_lap_time(state, applied)
        tyre_loss = self.time_loss[state.compound].evaluate(state.tyre_wear)
        lap_time = nominal_time + tyre_loss

        next_fuel_energy = max(state.fuel_energy_mj - applied.fuel_energy_mj, 0.0)
        fuel_mass_burned = applied.fuel_energy_mj / self.p.fuel_lhv_mj_per_kg
        next_mass = max(self.p.empty_mass_kg, state.car_mass_kg - fuel_mass_burned)
        next_battery = float(np.clip(
            state.battery_mj + applied.battery_delta_mj,
            0.0,
            self.p.battery_capacity_mj,
        ))

        if applied.pit_compound is not None:
            next_compound = applied.pit_compound
            next_wear = 0.0
            changed = state.compound_changed or (next_compound != state.compound)
        else:
            next_compound = state.compound
            coeff = self.wear[state.compound]
            mass_ratio = state.car_mass_kg / (self.p.empty_mass_kg + self.p.initial_fuel_kg)
            next_wear = coeff.a * state.tyre_wear + coeff.b * mass_ratio + coeff.c
            next_wear = float(np.clip(next_wear, 0.0, 1.25))
            changed = state.compound_changed

        next_state = PaperStrategyState(
            lap=state.lap + 1,
            battery_mj=next_battery,
            fuel_energy_mj=next_fuel_energy,
            car_mass_kg=next_mass,
            race_time_s=state.race_time_s + lap_time,
            compound_changed=changed,
            compound=next_compound,
            tyre_wear=next_wear,
            outlap=applied.pit_compound is not None,
            last_lap_time_s=lap_time,
        )
        info = TransitionInfo(
            requested_action=action,
            applied_action=applied,
            lap_time_s=lap_time,
            tyre_time_loss_s=tyre_loss,
            nominal_time_s=nominal_time,
            action_projected=applied != action,
        )
        return next_state, info

    def rollout(
        self,
        actions: Sequence[PaperStrategyAction],
        initial_compound: TyreCompound = TyreCompound.MEDIUM,
    ) -> tuple[list[PaperStrategyState], list[TransitionInfo]]:
        state = self.initial_state(initial_compound)
        states = [state]
        infos: list[TransitionInfo] = []
        for action in actions:
            if self.is_done(state):
                break
            state, info = self.transition(state, action)
            states.append(state)
            infos.append(info)
        return states, infos

    def final_state_is_legal(self, state: PaperStrategyState, tolerance_mj: float = 1e-6) -> bool:
        if not self.is_done(state):
            return False
        if self.p.require_compound_change and not state.compound_changed:
            return False
        return state.fuel_energy_mj <= tolerance_mj and state.battery_mj <= tolerance_mj


@dataclass(frozen=True)
class BeamNode:
    state: PaperStrategyState
    actions: tuple[PaperStrategyAction, ...]


class DiscreteStrategyOracle:
    """A reproducible beam-search oracle for starter experiments.

    This is deliberately labelled *oracle*, not MINLP replication. It discretizes
    the paper action space and supplies a strong target for unit tests, imitation
    learning, and RL-regret measurements before CasADi/BONMIN is introduced.
    """

    def __init__(
        self,
        model: PaperStrategyModel,
        fuel_fractions: Iterable[float] = (0.90, 1.00, 1.10),
        battery_deltas_mj: Iterable[float] = (-1.0, 0.0, 0.5),
        beam_width: int = 256,
        pit_window: tuple[int, int] | None = None,
    ) -> None:
        self.model = model
        self.fuel_fractions = tuple(float(x) for x in fuel_fractions)
        self.battery_deltas = tuple(float(x) for x in battery_deltas_mj)
        self.beam_width = int(beam_width)
        self.pit_window = pit_window or (1, model.p.total_laps - 1)
        if self.beam_width <= 0:
            raise ValueError("beam_width must be positive")

    def _actions_for_lap(self, lap: int) -> list[PaperStrategyAction]:
        nominal = self.model.p.nominal_fuel_energy_mj()
        pit_options: tuple[TyreCompound | None, ...]
        pit_options = (None, *_DRY_COMPOUNDS) if self.pit_window[0] <= lap <= self.pit_window[1] else (None,)
        return [
            PaperStrategyAction(nominal * f, b, pit)
            for f in self.fuel_fractions
            for b in self.battery_deltas
            for pit in pit_options
        ]

    def solve(self, initial_compound: TyreCompound = TyreCompound.MEDIUM) -> BeamNode:
        beam = [BeamNode(self.model.initial_state(initial_compound), ())]
        for lap in range(self.model.p.total_laps):
            candidates: list[BeamNode] = []
            for node in beam:
                for action in self._actions_for_lap(lap):
                    next_state, info = self.model.transition(node.state, action)
                    candidates.append(BeamNode(next_state, (*node.actions, info.applied_action)))
            # Keep diverse state buckets so the beam does not collapse only by
            # immediate race time and discard useful energy/tyre configurations.
            buckets: dict[tuple[int, int, str, bool], BeamNode] = {}
            for node in sorted(candidates, key=lambda n: n.state.race_time_s):
                key = (
                    round(node.state.battery_mj * 2),
                    round(node.state.tyre_wear * 10),
                    node.state.compound.value,
                    node.state.compound_changed,
                )
                buckets.setdefault(key, node)
            beam = sorted(buckets.values(), key=lambda n: n.state.race_time_s)[: self.beam_width]
        legal = [node for node in beam if self.model.final_state_is_legal(node.state)]
        if not legal:
            # The discretized grid can miss exact zero-energy endpoints. Return
            # the best rule-compliant state while exposing residual energy.
            legal = [node for node in beam if (node.state.compound_changed or not self.model.p.require_compound_change)]
        if not legal:
            raise RuntimeError("No feasible strategy found by the discrete oracle")
        return min(legal, key=lambda n: (n.state.race_time_s, n.state.fuel_energy_mj + n.state.battery_mj))
