"""Independent tiny-family reference: affine fuel plus concave battery on polytopes.

No optimizer graphs, gradients, multistart helpers or projected transitions are used.
Numerical vertex enumeration is restricted to <=3 laps and mass-independent wear.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from math import sqrt

import numpy as np

from apexsim.research.fienia_strategy import PaperStrategyModel
from apexsim.sim_core.types import TyreCompound


@dataclass(frozen=True)
class ContinuousReferenceResult:
    race_time_s: float
    fuel_fractions: tuple[float, ...]
    battery_deltas_mj: tuple[float, ...]
    pit_plan: tuple[TyreCompound | None, ...]
    evaluated_candidates: int
    fuel_vertices: int
    battery_vertices: int
    certificate_family: str = "AFFINE_FUEL_CONCAVE_BATTERY_MASS_INDEPENDENT_WEAR"


def _vertices(lower: np.ndarray, upper: np.ndarray, total: float,
              battery_capacity: float | None = None) -> tuple[np.ndarray, ...]:
    n = len(lower)
    rows, rhs = list(np.eye(n)) + list(-np.eye(n)), [*upper, *(-lower)]
    if battery_capacity is not None:
        for i in range(1, n):
            prefix = np.array([1.] * i + [0.] * (n - i))
            rows.extend((prefix, -prefix))
            rhs.extend((0., battery_capacity))
    a, b = np.array(rows), np.array(rhs)
    found = {}
    for active in itertools.combinations(range(len(rows)), n - 1):
        matrix = np.vstack([np.ones(n), a[list(active)]])
        if np.linalg.matrix_rank(matrix) != n:
            continue
        point = np.linalg.solve(matrix, np.array([total, *b[list(active)]]))
        if np.max(a @ point - b) <= 1e-9 and abs(point.sum() - total) <= 1e-9:
            found[tuple(np.round(point, 12))] = point
    if not found:
        raise ValueError("Tiny reference resource polytope is empty")
    return tuple(found[k] for k in sorted(found))


def tiny_continuous_reference(model: PaperStrategyModel, initial_compound: TyreCompound = TyreCompound.MEDIUM,
                              pit_window: tuple[int, int] | None = None,
                              battery_smoothing_mj: float = .01) -> ContinuousReferenceResult:
    """Global minimum for this declared restricted family, up to numerical vertex tolerance."""
    p, n = model.p, model.p.total_laps
    model.initial_state(initial_compound)
    if n > 3 or any(c.b != 0 for c in model.wear.values()):
        raise ValueError("Tiny reference requires <=3 laps and mass-independent wear")
    if p.battery_recharge_time_s_per_mj > p.battery_deploy_time_s_per_mj:
        raise ValueError("Tiny reference requires a concave or linear battery objective")
    if not np.isfinite(battery_smoothing_mj) or battery_smoothing_mj <= 0:
        raise ValueError("Tiny reference smoothing must be finite and positive")
    window = pit_window if pit_window is not None else (0, n - 2)
    if (len(window) != 2 or any(type(v) is not int for v in window)
            or window[0] < 0 or window[1] >= n - 1 or window[1] < window[0] - 1):
        raise ValueError("Tiny reference pit window must be before the final lap (or empty)")
    # Construct each resource polytope independently; terminal equalities are explicit.
    fuels = _vertices(np.full(n, .9), np.full(n, 1.1), float(n))
    batteries = _vertices(np.full(n, p.battery_delta_min_mj), np.full(n, p.battery_delta_max_mj),
                          -p.battery_capacity_mj, p.battery_capacity_mj)
    dry = (TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD)
    options = [(None, *dry) if window[0] <= i <= window[1] else (None,) for i in range(n)]
    best, candidates = None, 0
    for plan in itertools.product(*options):
        previous, changed = initial_compound, False
        for pit in plan:
            if pit is not None:
                changed = changed or pit != previous
                previous = pit
        if p.require_compound_change and not changed:
            continue
        for ratios, deltas in itertools.product(fuels, batteries):
            mass, wear, compound, outlap, objective = p.empty_mass_kg + p.initial_fuel_kg, 0., initial_compound, False, 0.
            for ratio, delta, pit in zip(ratios, deltas, plan, strict=True):
                if not -1e-9 <= wear <= 1.25 + 1e-9:
                    raise ValueError("Tiny reference requires unclipped wear throughout the declared family")
                coeff = model.time_loss[compound]
                tyre = coeff.fresh_loss_s + coeff.linear_s * wear + coeff.quadratic_s * wear**2 + coeff.cubic_s * wear**3
                battery = ((p.battery_deploy_time_s_per_mj + p.battery_recharge_time_s_per_mj) * delta / 2
                           + (p.battery_recharge_time_s_per_mj - p.battery_deploy_time_s_per_mj)
                           * (sqrt(delta**2 + battery_smoothing_mj**2) - battery_smoothing_mj) / 2)
                penalty = (p.consecutive_pit_penalty_s if outlap else p.pit_inlap_penalty_s) if pit is not None else (
                    p.pit_outlap_penalty_s if outlap else 0.)
                objective += (p.nominal_lap_time_s + p.mass_time_s_per_kg * (mass - p.empty_mass_kg)
                              - p.fuel_energy_time_s_per_fraction * (ratio - 1) + tyre + battery + penalty)
                if pit is not None:
                    compound, wear = pit, 0.
                else:
                    wear = model.wear[compound].a * wear + model.wear[compound].c
                mass -= ratio * p.nominal_fuel_energy_mj() / p.fuel_lhv_mj_per_kg
                outlap = pit is not None
            if not np.isfinite(objective) or not 0 <= wear <= 1.25:
                raise ValueError("Tiny reference requires finite objective and unclipped terminal wear")
            candidates += 1
            if best is None or objective < best[0]:
                best = (float(objective), tuple(float(v) for v in ratios), tuple(float(v) for v in deltas), plan)
    if best is None:
        raise ValueError("Tiny reference has no legal compound schedule")
    return ContinuousReferenceResult(*best, candidates, len(fuels), len(batteries))
