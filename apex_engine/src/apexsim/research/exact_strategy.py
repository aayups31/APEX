"""Bounded exhaustive oracle for the projected finite strategy grid, not MINLP."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from apexsim.research.fienia_strategy import BeamNode, PaperStrategyAction, PaperStrategyModel
from apexsim.sim_core.types import TyreCompound


@dataclass(frozen=True)
class ExactSearchResult:
    solution: BeamNode
    requested_actions: tuple[PaperStrategyAction, ...]
    terminal_sequences: int
    legal_terminal_sequences: int
    transitions: int


class ExactStrategyOracle:
    """Enumerate every requested sequence without bucketing or pruning.

    Exactness covers only this finite grid under the model's projected transitions.
    Projected aliases are counted separately. Budget failures return no solution.
    """

    def __init__(self, model: PaperStrategyModel, fuel_fractions=(.9, 1., 1.1),
                 battery_deltas_mj=(-1., 0., .5), pit_window=None, max_sequences: int = 100_000):
        self.model = model
        self.fuel_fractions = tuple(float(v) for v in fuel_fractions)
        self.battery_deltas = tuple(float(v) for v in battery_deltas_mj)
        self.pit_window = pit_window if pit_window is not None else (1, model.p.total_laps - 1)
        if type(max_sequences) is not int or max_sequences <= 0:
            raise ValueError("max_sequences must be a positive integer")
        self.max_sequences = max_sequences
        if model.p.total_laps > 8:
            raise ValueError("Exact enumeration supports at most eight laps")
        if not self.fuel_fractions or not self.battery_deltas or not all(
            isfinite(v) for v in (*self.fuel_fractions, *self.battery_deltas)
        ):
            raise ValueError("Action grids must be nonempty and finite")

    def solve(self, initial_compound=TyreCompound.MEDIUM) -> ExactSearchResult:
        # Independent Cartesian action construction, not the beam's helper.
        options = []
        sequences = 1
        for lap in range(self.model.p.total_laps):
            pits = (None, TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD) if (
                self.pit_window[0] <= lap <= self.pit_window[1]
            ) else (None,)
            grid = tuple(PaperStrategyAction(self.model.p.nominal_fuel_energy_mj() * fuel, battery, pit)
                         for fuel in self.fuel_fractions for battery in self.battery_deltas for pit in pits)
            options.append(grid)
            sequences *= len(grid)
            if sequences > self.max_sequences:
                raise ValueError(f"Exact enumeration exceeds max_sequences={self.max_sequences}; no partial optimum")
        best = None
        best_requested = ()
        terminal = legal = transitions = 0

        def visit(state, requested, applied):
            nonlocal best, best_requested, terminal, legal, transitions
            if state.lap == self.model.p.total_laps:
                terminal += 1
                if self.model.final_state_is_legal(state):
                    legal += 1
                    if best is None or state.race_time_s < best.state.race_time_s:
                        best, best_requested = BeamNode(state, applied), requested
                return
            for action in options[state.lap]:
                next_state, info = self.model.transition(state, action)
                transitions += 1
                visit(next_state, (*requested, action), (*applied, info.applied_action))

        visit(self.model.initial_state(initial_compound), (), ())
        assert terminal == sequences
        if best is None:
            raise RuntimeError("No legal terminal strategy exists on the enumerated grid")
        return ExactSearchResult(best, best_requested, terminal, legal, transitions)
