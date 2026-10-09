"""Independent scalar vertex reference from an observed, partially spent state."""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from math import sqrt

import numpy as np

from apexsim.research.fienia_strategy import PaperStrategyAction, PaperStrategyModel, PaperStrategyState
from apexsim.sim_core.types import TyreCompound


@dataclass(frozen=True)
class ContinuationResult:
    remaining_time_s: float
    actions: tuple[PaperStrategyAction, ...]
    fuel_fractions: tuple[float, ...]
    battery_deltas_mj: tuple[float, ...]
    pit_plan: tuple[TyreCompound | None, ...]
    evaluated_candidates: int
    fuel_vertices: int
    battery_vertices: int
    excluded_wear_plans: int
    certificate_family: str = "AFFINE_FUEL_CONCAVE_BATTERY_MASS_INDEPENDENT_WEAR"


def resource_vertices(lower: np.ndarray, upper: np.ndarray, total: float,
                      battery_initial: float | None = None,
                      battery_capacity: float | None = None) -> tuple[np.ndarray, ...]:
    """Enumerate a bounded resource polytope, including actual battery prefix levels."""
    lower, upper = np.asarray(lower, dtype=float), np.asarray(upper, dtype=float)
    if (lower.ndim != 1 or upper.shape != lower.shape or not 1 <= len(lower) <= 3
            or not np.isfinite(lower).all() or not np.isfinite(upper).all()
            or not np.isfinite(total) or np.any(lower > upper)):
        raise ValueError("Invalid resource bounds")
    if (battery_initial is None) != (battery_capacity is None):
        raise ValueError("Battery initial level and capacity must be supplied together")
    if battery_initial is not None and (
            not np.isfinite([battery_initial, battery_capacity]).all()
            or not 0 <= battery_initial <= battery_capacity):
        raise ValueError("Invalid battery initial level")
    n = len(lower)
    rows, rhs = list(np.eye(n)) + list(-np.eye(n)), [*upper, *(-lower)]
    if battery_initial is not None:
        for i in range(1, n):
            prefix = np.array([1.] * i + [0.] * (n - i))
            rows.extend((prefix, -prefix))
            rhs.extend((battery_capacity - battery_initial, battery_initial))
    a, b = np.asarray(rows), np.asarray(rhs)
    found = {}
    for active in itertools.combinations(range(len(rows)), n - 1):
        matrix = np.vstack([np.ones(n), a[list(active)]])
        if np.linalg.matrix_rank(matrix) != n:
            continue
        point = np.linalg.solve(matrix, np.array([total, *b[list(active)]]))
        if np.max(a @ point - b) <= 1e-9 and abs(point.sum() - total) <= 1e-9:
            found[tuple(np.round(point, 12))] = point
    if not found:
        raise ValueError("Continuation resource polytope is empty")
    return tuple(found[key] for key in sorted(found))


def tiny_continuation_reference(model: PaperStrategyModel, state: PaperStrategyState,
                                pit_window: tuple[int, int] | None = None,
                                battery_smoothing_mj: float = .01,
                                max_candidates: int = 5000) -> ContinuationResult:
    """Exhaust the restricted family without transitions, projection or optimizer graphs."""
    model.validate_state(state)
    p, n = model.p, model.p.total_laps - state.lap
    if not 1 <= n <= 3 or any(c.b != 0 for c in model.wear.values()):
        raise ValueError("Continuation requires 1..3 remaining laps and mass-independent wear")
    if p.battery_recharge_time_s_per_mj > p.battery_deploy_time_s_per_mj:
        raise ValueError("Continuation requires a concave or linear battery objective")
    if not np.isfinite(battery_smoothing_mj) or battery_smoothing_mj <= 0:
        raise ValueError("Continuation smoothing must be finite and positive")
    if type(max_candidates) is not int or max_candidates <= 0:
        raise ValueError("Candidate budget must be a positive integer")
    window = pit_window if pit_window is not None else (0, p.total_laps - 2)
    if (len(window) != 2 or any(type(v) is not int for v in window) or window[0] < 0
            or window[1] >= p.total_laps - 1 or window[1] < window[0] - 1):
        raise ValueError("Continuation pit window must precede the final lap or be empty")
    if state.battery_mj < 0 or state.fuel_energy_mj < 0:
        raise ValueError("Continuation resources must be nonnegative")
    nominal = p.nominal_fuel_energy_mj()
    fuels = resource_vertices(np.full(n, .9), np.full(n, 1.1), state.fuel_energy_mj / nominal)
    batteries = resource_vertices(np.full(n, p.battery_delta_min_mj),
                                  np.full(n, p.battery_delta_max_mj), -state.battery_mj,
                                  state.battery_mj, p.battery_capacity_mj)
    dry = (TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD)
    options = [(None, *dry) if window[0] <= i <= window[1] else (None,)
               for i in range(state.lap, p.total_laps)]
    raw_count = len(fuels) * len(batteries) * int(np.prod([len(o) for o in options]))
    if raw_count > max_candidates:
        raise ValueError(f"Continuation candidate budget exceeded: {raw_count} > {max_candidates}")
    best, candidates, excluded = None, 0, 0
    for plan in itertools.product(*options):
        compound, wear, outlap, changed = state.compound, state.tyre_wear, state.outlap, state.compound_changed
        tyre_costs, penalties, valid = [], [], True
        for pit in plan:
            if not 0 <= wear <= 1.25:
                valid = False
                break
            c = model.time_loss[compound]
            tyre_costs.append(c.fresh_loss_s + c.linear_s * wear + c.quadratic_s * wear**2 + c.cubic_s * wear**3)
            penalties.append((p.consecutive_pit_penalty_s if outlap else p.pit_inlap_penalty_s)
                             if pit is not None else (p.pit_outlap_penalty_s if outlap else 0.))
            if pit is not None:
                changed = changed or pit != compound
                compound, wear = pit, 0.
            else:
                wear = model.wear[compound].a * wear + model.wear[compound].c
            outlap = pit is not None
        if not valid or not 0 <= wear <= 1.25:
            excluded += 1
            continue
        if p.require_compound_change and not changed:
            continue
        for ratios, deltas in itertools.product(fuels, batteries):
            mass, objective = state.car_mass_kg, 0.
            for i, (ratio, delta) in enumerate(zip(ratios, deltas, strict=True)):
                battery = ((p.battery_deploy_time_s_per_mj + p.battery_recharge_time_s_per_mj) * delta / 2
                           + (p.battery_recharge_time_s_per_mj - p.battery_deploy_time_s_per_mj)
                           * (sqrt(delta**2 + battery_smoothing_mj**2) - battery_smoothing_mj) / 2)
                objective += (p.nominal_lap_time_s + p.mass_time_s_per_kg * (mass - p.empty_mass_kg)
                              - p.fuel_energy_time_s_per_fraction * (ratio - 1)
                              + tyre_costs[i] + penalties[i] + battery)
                mass -= ratio * nominal / p.fuel_lhv_mj_per_kg
            if not np.isfinite(objective):
                raise ValueError("Nonfinite continuation objective")
            candidates += 1
            if best is None or objective < best[0]:
                best = (float(objective), tuple(float(v) for v in ratios),
                        tuple(float(v) for v in deltas), plan)
    if best is None:
        raise ValueError("No legal unclipped continuation")
    cost, ratios, deltas, plan = best
    actions = tuple(PaperStrategyAction(r * nominal, d, pit)
                    for r, d, pit in zip(ratios, deltas, plan, strict=True))
    return ContinuationResult(cost, actions, ratios, deltas, plan, candidates,
                              len(fuels), len(batteries), excluded)
