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
from math import isfinite
from typing import Literal

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
    projection_reasons: tuple[str, ...] = ()
    wear_clipped: bool = False


class PaperStrategyModel:
    """Transparent lap-level model matching the paper's state/action topology."""

    def __init__(
        self,
        parameters: PaperStrategyParameters | None = None,
        wear_coefficients: dict[TyreCompound, TireWearCoefficients] | None = None,
        time_loss_coefficients: dict[TyreCompound, TireTimeLossCoefficients] | None = None,
    ) -> None:
        self.p = parameters or PaperStrategyParameters()
        if type(self.p.total_laps) is not int or self.p.total_laps <= 0:
            raise ValueError("total_laps must be a positive integer")
        numeric = [v for v in vars(self.p).values() if type(v) in (int, float)]
        if not all(isfinite(v) for v in numeric):
            raise ValueError("Strategy parameters must be finite")
        if min(self.p.empty_mass_kg, self.p.initial_fuel_kg, self.p.fuel_lhv_mj_per_kg) <= 0:
            raise ValueError("Mass and fuel heating value must be positive")
        if self.p.battery_capacity_mj < 0 or self.p.battery_delta_min_mj >= 0 or self.p.battery_delta_max_mj < 0:
            raise ValueError("Battery bounds require nonnegative capacity/recharge and negative deployment")
        if self.p.battery_capacity_mj > self.p.total_laps * abs(self.p.battery_delta_min_mj):
            raise ValueError("Initial battery cannot be depleted within the declared per-lap bounds")
        self.wear = dict(wear_coefficients or DEFAULT_WEAR)
        self.time_loss = dict(time_loss_coefficients or DEFAULT_TIME_LOSS)
        missing = (set(_DRY_COMPOUNDS) - self.wear.keys()) | (set(_DRY_COMPOUNDS) - self.time_loss.keys())
        if missing:
            raise ValueError(f"Missing tyre coefficients for {sorted(x.value for x in missing)}")
        for compound in _DRY_COMPOUNDS:
            coefficients = (*vars(self.wear[compound]).values(), *vars(self.time_loss[compound]).values())
            if not all(isfinite(v) for v in coefficients) or min(vars(self.wear[compound]).values()) < 0:
                raise ValueError("Tyre coefficients must be finite; wear coefficients must be nonnegative")

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
        values mean deployment. The map is affine between reversed bounds;
        asymmetric limits imply that normalized zero is not neutral energy.
        """
        if not isfinite(fuel) or not isfinite(battery):
            raise ValueError("Normalized energy actions must be finite")
        f = float(np.clip(fuel, 0.0, 1.0))
        b = float(np.clip(battery, -1.0, 1.0))
        fuel_fraction = 0.90 + 0.20 * f
        # Eq. 54/56 is affine even when deployment and recharge limits differ.
        battery_delta = (
            (self.p.battery_delta_max_mj + self.p.battery_delta_min_mj) / 2.0
            + (self.p.battery_delta_min_mj - self.p.battery_delta_max_mj) * b / 2.0
        )
        pit_map = {0: None, 1: TyreCompound.SOFT, 2: TyreCompound.MEDIUM, 3: TyreCompound.HARD}
        if type(pit_code) is not int or pit_code not in pit_map:
            raise ValueError("pit_code must be 0, 1, 2, or 3")
        return PaperStrategyAction(
            fuel_energy_mj=fuel_fraction * self.p.nominal_fuel_energy_mj(),
            battery_delta_mj=battery_delta,
            pit_compound=pit_map[pit_code],
        )

    def _validate_compound(self, compound: TyreCompound) -> None:
        if compound not in _DRY_COMPOUNDS:
            raise ValueError("The paper adaptation model supports dry compounds only")

    def validate_state(self, state: PaperStrategyState, tolerance: float = 1e-9) -> None:
        """Reject invalid or terminally unreachable states instead of hiding violations."""
        self._validate_compound(state.compound)
        if type(state.lap) is not int or not 0 <= state.lap <= self.p.total_laps:
            raise ValueError("Strategy state lap is outside the race horizon")
        if not all(isfinite(v) for v in (state.battery_mj, state.fuel_energy_mj, state.car_mass_kg,
                                        state.race_time_s, state.tyre_wear, state.last_lap_time_s)):
            raise ValueError("Strategy state must be finite")
        if not -tolerance <= state.battery_mj <= self.p.battery_capacity_mj + tolerance:
            raise ValueError("Strategy battery state is outside capacity bounds")
        if state.fuel_energy_mj < -tolerance or state.race_time_s < 0 or state.last_lap_time_s < 0:
            raise ValueError("Strategy resources/time must be nonnegative")
        expected_mass = self.p.empty_mass_kg + state.fuel_energy_mj / self.p.fuel_lhv_mj_per_kg
        if abs(state.car_mass_kg - expected_mass) > tolerance:
            raise ValueError("Strategy fuel energy and car mass are inconsistent")
        if not 0 <= state.tyre_wear <= 1.25:
            raise ValueError("Strategy tyre wear is outside the declared surrogate domain")
        remaining = self.p.total_laps - state.lap
        nominal = self.p.nominal_fuel_energy_mj()
        if not remaining * .9 * nominal - tolerance <= state.fuel_energy_mj <= remaining * 1.1 * nominal + tolerance:
            raise ValueError("Strategy fuel state is outside the backward-reachable interval")
        if state.battery_mj > remaining * abs(self.p.battery_delta_min_mj) + tolerance:
            raise ValueError("Strategy battery state is outside the backward-reachable interval")

    def _project_action(self, state: PaperStrategyState, action: PaperStrategyAction) -> PaperStrategyAction:
        self.validate_state(state)
        if not isfinite(action.fuel_energy_mj) or not isfinite(action.battery_delta_mj):
            raise ValueError("Physical energy actions must be finite")
        laps_after = max(self.p.total_laps - state.lap - 1, 0)
        nominal = self.p.nominal_fuel_energy_mj()
        min_fuel = 0.90 * nominal
        max_fuel = 1.10 * nominal

        # Backward-reachable interval: leave enough fuel for minimum allocation,
        # but not so much that maximum allocation cannot consume it by the finish.
        remaining_min = laps_after * min_fuel
        remaining_max = laps_after * max_fuel
        lower_consume = max(min_fuel, state.fuel_energy_mj - remaining_max)
        upper_consume = min(max_fuel, state.fuel_energy_mj - remaining_min)
        if upper_consume < lower_consume:
            if lower_consume - upper_consume > 1e-9:
                raise ValueError("No feasible fuel action satisfies current and terminal bounds")
            lower_consume = upper_consume  # Roundoff only; not a physical relaxation.
        fuel = float(np.clip(action.fuel_energy_mj, lower_consume, upper_consume))
        # The next-state reachable set uses laps AFTER this action. Eq. 59's
        # positive recharge bound is not deployment capacity: use abs(delta_min).
        lower_delta = max(self.p.battery_delta_min_mj, -state.battery_mj)
        upper_delta = min(self.p.battery_delta_max_mj, self.p.battery_capacity_mj - state.battery_mj,
                          laps_after * abs(self.p.battery_delta_min_mj) - state.battery_mj)
        if upper_delta < lower_delta:
            if lower_delta - upper_delta > 1e-9:
                raise ValueError("No feasible battery action satisfies current and terminal bounds")
            lower_delta = upper_delta
        delta = float(np.clip(action.battery_delta_mj, lower_delta, upper_delta))

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
        self.validate_state(state)
        if self.is_done(state):
            raise RuntimeError("Cannot transition a completed race")
        applied = self._project_action(state, action)
        nominal_time = self._nominal_lap_time(state, applied)
        tyre_loss = self.time_loss[state.compound].evaluate(state.tyre_wear)
        lap_time = nominal_time + tyre_loss
        if not isfinite(lap_time) or lap_time <= 0:
            raise ValueError("Strategy lap-time surrogate produced a nonpositive/nonfinite duration")

        next_fuel_energy = max(state.fuel_energy_mj - applied.fuel_energy_mj, 0.0)
        fuel_mass_burned = applied.fuel_energy_mj / self.p.fuel_lhv_mj_per_kg
        next_mass = max(self.p.empty_mass_kg, state.car_mass_kg - fuel_mass_burned)
        next_battery = float(np.clip(
            state.battery_mj + applied.battery_delta_mj,
            0.0,
            self.p.battery_capacity_mj,
        ))

        wear_clipped = False
        if applied.pit_compound is not None:
            next_compound = applied.pit_compound
            next_wear = 0.0
            changed = state.compound_changed or (next_compound != state.compound)
        else:
            next_compound = state.compound
            coeff = self.wear[state.compound]
            mass_ratio = state.car_mass_kg / (self.p.empty_mass_kg + self.p.initial_fuel_kg)
            next_wear = coeff.a * state.tyre_wear + coeff.b * mass_ratio + coeff.c
            bounded = float(np.clip(next_wear, 0.0, 1.25))
            wear_clipped = bounded != next_wear
            next_wear = bounded
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
            projection_reasons=tuple(name for name, changed in (
                ("fuel_input_or_reachability", applied.fuel_energy_mj != action.fuel_energy_mj),
                ("battery_input_capacity_or_reachability", applied.battery_delta_mj != action.battery_delta_mj),
            ) if changed),
            wear_clipped=wear_clipped,
        )
        self.validate_state(next_state)
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
        try:
            self.validate_state(state, tolerance=tolerance_mj)
        except ValueError:
            return False
        if state.lap != self.p.total_laps:
            return False
        if self.p.require_compound_change and not state.compound_changed:
            return False
        return 0 <= state.fuel_energy_mj <= tolerance_mj and 0 <= state.battery_mj <= tolerance_mj


@dataclass(frozen=True)
class BeamNode:
    state: PaperStrategyState
    actions: tuple[PaperStrategyAction, ...]


class DiscreteStrategyOracle:
    """Approximate beam-search benchmark; finite width supplies no optimality guarantee.

    Lossless state bucketing is available for tiny exact comparisons. Coarse
    bucketing or finite-width pruning can discard the optimal strategy.
    """

    def __init__(
        self,
        model: PaperStrategyModel,
        fuel_fractions: Iterable[float] = (0.90, 1.00, 1.10),
        battery_deltas_mj: Iterable[float] = (-1.0, 0.0, 0.5),
        beam_width: int = 256,
        pit_window: tuple[int, int] | None = None,
        state_bucketing: Literal["coarse", "exact"] = "coarse",
    ) -> None:
        self.model = model
        self.fuel_fractions = tuple(float(x) for x in fuel_fractions)
        self.battery_deltas = tuple(float(x) for x in battery_deltas_mj)
        self.beam_width = int(beam_width)
        self.pit_window = pit_window or (1, model.p.total_laps - 1)
        self.state_bucketing = state_bucketing
        self.last_search: dict = {}
        if self.beam_width <= 0:
            raise ValueError("beam_width must be positive")
        if state_bucketing not in ("coarse", "exact"):
            raise ValueError("state_bucketing must be coarse or exact")
        if not self.fuel_fractions or not self.battery_deltas or not all(
            isfinite(x) for x in (*self.fuel_fractions, *self.battery_deltas)
        ):
            raise ValueError("Action grids must be nonempty and finite")

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
        pruned = 0
        beam = [BeamNode(self.model.initial_state(initial_compound), ())]
        for lap in range(self.model.p.total_laps):
            candidates: list[BeamNode] = []
            for node in beam:
                for action in self._actions_for_lap(lap):
                    next_state, info = self.model.transition(node.state, action)
                    candidates.append(BeamNode(next_state, (*node.actions, info.applied_action)))
            # Keep diverse state buckets so the beam does not collapse only by
            # immediate race time and discard useful energy/tyre configurations.
            buckets: dict[tuple, BeamNode] = {}
            for node in sorted(candidates, key=lambda n: n.state.race_time_s):
                s = node.state
                if self.state_bucketing == "exact":
                    # Every state that affects the future: fuel/mass and outlap
                    # cannot be omitted. Time is the dominance objective.
                    key = (s.lap, s.battery_mj, s.fuel_energy_mj, s.car_mass_kg,
                           s.tyre_wear, s.compound, s.compound_changed, s.outlap)
                else:
                    key = (round(s.battery_mj * 2), round(s.tyre_wear * 10),
                           round(s.fuel_energy_mj, 6), s.compound, s.compound_changed, s.outlap)
                buckets.setdefault(key, node)
            ranked = sorted(buckets.values(), key=lambda n: n.state.race_time_s)
            pruned += max(0, len(ranked) - self.beam_width)
            beam = ranked[: self.beam_width]
        self.last_search = {"state_bucketing": self.state_bucketing, "width_pruned_states": pruned,
                            "exact_for_grid": self.state_bucketing == "exact" and pruned == 0}
        legal = [node for node in beam if self.model.final_state_is_legal(node.state)]
        if not legal:
            raise RuntimeError("Beam retained no legal terminal strategy; increase width or use exact enumeration")
        return min(legal, key=lambda n: (n.state.race_time_s, n.state.fuel_energy_mj + n.state.battery_mj))
