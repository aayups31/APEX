"""R016 bounded pit enumeration plus local IPOPT, not a global MINLP solver."""
from __future__ import annotations

import itertools
from dataclasses import asdict, dataclass
from math import isfinite, sqrt
from time import perf_counter
from typing import Any

import numpy as np
from numpy.typing import ArrayLike

from apexsim.research.fienia_strategy import PaperStrategyAction, PaperStrategyModel, PaperStrategyState
from apexsim.research.smooth_lap import LapMode, SmoothLapMap
from apexsim.sim_core.types import TyreCompound

DRY = (TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD)


@dataclass(frozen=True)
class SolverSettings:
    """Declared research budgets and residual tolerances, not calibrated car data."""

    max_laps: int = 8
    max_pit_sequences: int = 256
    max_iterations: int = 500
    solver_tolerance: float = 1e-9
    primal_tolerance: float = 1e-7

    def __post_init__(self) -> None:
        if any(type(v) is not int or v <= 0 for v in
               (self.max_laps, self.max_pit_sequences, self.max_iterations)) or self.max_laps > 8:
            raise ValueError("Solver budgets must be positive integers; at most eight laps are supported")
        if any(not isfinite(v) or not 0 < v <= 1e-6 for v in
               (self.solver_tolerance, self.primal_tolerance)):
            raise ValueError("Solver tolerances must be finite in (0, 1e-6]")


class SolverAbstention(RuntimeError):
    """No independently accepted solution; diagnostics remain available."""

    def __init__(self, report: dict[str, Any]) -> None:
        super().__init__("Strategy solver abstained: no accepted feasible local solution")
        self.report = report


@dataclass(frozen=True)
class StrategyReplay:
    actions: tuple[PaperStrategyAction, ...]
    states: tuple[PaperStrategyState, ...]
    smooth_race_time_s: float
    original_race_time_s: float
    max_primal_violation: float
    terminal_fuel_mj: float
    terminal_battery_mj: float
    max_legacy_action_adjustment_mj: float
    legacy_state_errors: dict[str, float]


@dataclass(frozen=True)
class StrategySolverResult:
    solution: StrategyReplay
    report: dict[str, Any]


def enumerate_pit_plans(model: PaperStrategyModel, initial_compound: TyreCompound,
                        pit_window: tuple[int, int] | None, settings: SolverSettings) -> tuple[tuple, ...]:
    """Preflight the full raw schedule count; last-lap-only changes are excluded."""
    n = model.p.total_laps
    model.initial_state(initial_compound)
    if n > settings.max_laps:
        raise ValueError("Strategy horizon exceeds max_laps; no partial solution")
    window = pit_window if pit_window is not None else (0, n - 2)
    if (len(window) != 2 or any(type(v) is not int for v in window)
            or window[0] < 0 or window[1] >= n - 1 or window[1] < window[0] - 1):
        raise ValueError("Pit window must be a valid interval before the final lap (or empty)")
    options = [(None, *DRY) if window[0] <= i <= window[1] else (None,) for i in range(n)]
    count = 4 ** sum(len(v) == 4 for v in options)
    if count > settings.max_pit_sequences:
        raise ValueError(f"Pit enumeration exceeds max_pit_sequences={settings.max_pit_sequences}; no partial solution")
    plans = []
    for plan in itertools.product(*options):
        compound, changed = initial_compound, False
        for pit in plan:
            if pit is not None:
                changed = changed or pit != compound
                compound = pit
        if changed or not model.p.require_compound_change:
            plans.append(plan)
    return tuple(plans)


def energy_starts(model: PaperStrategyModel) -> tuple[np.ndarray, ...]:
    """Three deterministic backward-reachable starts; no benchmark/oracle access."""
    p, n = model.p, model.p.total_laps
    starts = []
    for label in range(3):
        fuel, battery = float(n), p.battery_capacity_mj
        ratios, deltas = [], []
        for i in range(n):
            remaining = n - i - 1
            lo, hi = max(.9, fuel - 1.1 * remaining), min(1.1, fuel - .9 * remaining)
            ratio = min(hi, max(lo, 1.)) if label == 0 else (hi if label == 1 else lo)
            lower = max(p.battery_delta_min_mj, -battery)
            upper = min(p.battery_delta_max_mj, p.battery_capacity_mj - battery,
                        remaining * abs(p.battery_delta_min_mj) - battery)
            if label == 0:
                delta = min(upper, max(lower, -p.battery_capacity_mj / n))
            else:
                delta = lower if (i + label) % 2 else upper
            ratios.append(ratio)
            deltas.append(delta)
            fuel -= ratio
            battery += delta
        starts.append(np.array([*ratios, *deltas]))
    return tuple(starts)


class FixedPlanProblem:
    """Direct shooting: fuel fractions then battery deltas (MJ), each of length N."""

    def __init__(self, model: PaperStrategyModel, pit_plan: tuple[TyreCompound | None, ...],
                 initial_compound: TyreCompound = TyreCompound.MEDIUM,
                 battery_smoothing_mj: float = .01) -> None:
        self.model, self.plan, self.initial_compound = model, tuple(pit_plan), initial_compound
        model.initial_state(initial_compound)
        p, n = model.p, model.p.total_laps
        if n > 8 or len(self.plan) != n or self.plan[-1] is not None:
            raise ValueError("Fixed plan requires at most eight laps, N decisions and no final-lap pit")
        if any(pit is not None and (not isinstance(pit, TyreCompound) or pit not in DRY) for pit in self.plan):
            raise ValueError("Fixed plan requires supported dry compounds")
        compound, changed = initial_compound, False
        for pit in self.plan:
            if pit is not None:
                changed = changed or pit != compound
                compound = pit
        if p.require_compound_change and not changed:
            raise ValueError("Fixed plan does not meet the required compound change")
        self.map = SmoothLapMap(p, model.time_loss, battery_smoothing_mj)
        ca = self.map._ca
        x = ca.SX.sym("allocation", 2 * n)
        fuel, battery, wear = p.initial_fuel_energy_mj(), p.battery_capacity_mj, 0.
        compound, outlap, objective = initial_compound, False, 0.
        g, self.lbg, self.ubg = [], [], []
        for i, pit in enumerate(self.plan):
            mass = p.empty_mass_kg + fuel / p.fuel_lhv_mj_per_kg
            mode = self._mode(pit, outlap)
            objective += self.map.functions(compound, mode).value(
                ca.vertcat(x[i] * p.nominal_fuel_energy_mj(), x[n + i], mass, wear))
            fuel -= x[i] * p.nominal_fuel_energy_mj()
            battery += x[n + i]
            if pit is not None:
                compound, wear = pit, 0.
            else:
                c = model.wear[compound]
                wear = c.a * wear + c.b * mass / (p.empty_mass_kg + p.initial_fuel_kg) + c.c
            outlap = pit is not None
            remaining = n - i - 1
            g.extend((fuel / p.nominal_fuel_energy_mj(), battery, wear))
            self.lbg.extend((.9 * remaining, 0., 0.))
            self.ubg.extend((1.1 * remaining, min(p.battery_capacity_mj, remaining * abs(p.battery_delta_min_mj)), 1.25))
        g = ca.vertcat(*g)
        self.lbx = np.array([.9] * n + [p.battery_delta_min_mj] * n)
        self.ubx = np.array([1.1] * n + [p.battery_delta_max_mj] * n)
        self.nlp = {"x": x, "f": objective, "g": g}
        self.objective = ca.Function("strategy_objective", [x], [objective])
        self.gradient = ca.Function("strategy_gradient", [x], [ca.gradient(objective, x)])
        self.constraints = ca.Function("strategy_constraints", [x], [g])
        self.jacobian = ca.Function("strategy_jacobian", [x], [ca.jacobian(g, x)])

    @staticmethod
    def _mode(pit: TyreCompound | None, outlap: bool) -> LapMode:
        return (LapMode.OUT_INLAP if outlap else LapMode.INLAP) if pit is not None else (
            LapMode.OUTLAP if outlap else LapMode.NORMAL)

    def replay(self, controls: ArrayLike, tolerance: float = 1e-7) -> StrategyReplay:
        """Unclipped scalar replay, then checked legacy replay; refuse any material repair."""
        p, n = self.model.p, self.model.p.total_laps
        x = np.asarray(controls, dtype=float)
        if x.shape != (2 * n,) or not np.isfinite(x).all():
            raise ValueError("Solver controls must be a finite vector of length 2*N")
        if not isfinite(tolerance) or not 0 < tolerance <= 1e-6:
            raise ValueError("Replay tolerance must be finite in (0, 1e-6]")
        if np.any(x < self.lbx - tolerance) or np.any(x > self.ubx + tolerance):
            raise ValueError("Solver controls are outside declared bounds")
        states = [self.model.initial_state(self.initial_compound)]
        actions, constraints = [], []
        for i, pit in enumerate(self.plan):
            s = states[-1]
            action = PaperStrategyAction(float(x[i] * p.nominal_fuel_energy_mj()), float(x[n + i]), pit)
            d, eps = action.battery_delta_mj, self.map.eps
            b = ((p.battery_deploy_time_s_per_mj + p.battery_recharge_time_s_per_mj) * d / 2
                 + (p.battery_recharge_time_s_per_mj - p.battery_deploy_time_s_per_mj)
                 * (sqrt(d * d + eps * eps) - eps) / 2)
            c = self.model.time_loss[s.compound]
            mode = self._mode(pit, s.outlap)
            penalty = {LapMode.NORMAL: 0., LapMode.INLAP: p.pit_inlap_penalty_s,
                       LapMode.OUTLAP: p.pit_outlap_penalty_s, LapMode.OUT_INLAP: p.consecutive_pit_penalty_s}[mode]
            lap_time = (p.nominal_lap_time_s + p.mass_time_s_per_kg * (s.car_mass_kg - p.empty_mass_kg)
                        - p.fuel_energy_time_s_per_fraction * (x[i] - 1) + b
                        + c.fresh_loss_s + c.linear_s * s.tyre_wear + c.quadratic_s * s.tyre_wear**2
                        + c.cubic_s * s.tyre_wear**3 + penalty)
            if not isfinite(lap_time) or lap_time <= 0:
                raise ValueError("Scalar solver replay produced an invalid lap time")
            fuel = s.fuel_energy_mj - action.fuel_energy_mj
            wear_coeff = self.model.wear[s.compound]
            wear = 0. if pit is not None else (wear_coeff.a * s.tyre_wear
                    + wear_coeff.b * s.car_mass_kg / (p.empty_mass_kg + p.initial_fuel_kg) + wear_coeff.c)
            state = PaperStrategyState(i + 1, s.battery_mj + d, fuel, p.empty_mass_kg + fuel / p.fuel_lhv_mj_per_kg,
                                      s.race_time_s + lap_time, s.compound_changed or (pit is not None and pit != s.compound),
                                      pit if pit is not None else s.compound, wear, pit is not None, lap_time)
            states.append(state)
            actions.append(action)
            constraints.extend((fuel / p.nominal_fuel_energy_mj(), state.battery_mj, wear))
        constraints = np.array(constraints)
        if not np.isfinite(constraints).all():
            raise ValueError("Scalar solver replay produced nonfinite constraints")
        violation = float(max(0., np.max(self.lbx - x), np.max(x - self.ubx),
                              np.max(np.array(self.lbg) - constraints), np.max(constraints - self.ubg)))
        terminal = states[-1]
        if (violation > tolerance or abs(terminal.fuel_energy_mj) > tolerance
                or abs(terminal.battery_mj) > tolerance):
            raise ValueError("Solver replay failed primal/resource/terminal constraints")
        if (abs(float(self.objective(x)) - terminal.race_time_s) > 1e-8
                or not np.allclose(np.asarray(self.constraints(x)).reshape(-1), constraints, atol=1e-9, rtol=0)):
            raise ValueError("Solver graph disagrees with independent scalar replay")
        legacy, infos = self.model.rollout(actions, self.initial_compound)
        adjustment = max(max(abs(a.fuel_energy_mj - info.applied_action.fuel_energy_mj),
                             abs(a.battery_delta_mj - info.applied_action.battery_delta_mj))
                         for a, info in zip(actions, infos, strict=True))
        if adjustment > tolerance or any(info.wear_clipped for info in infos) or not self.model.final_state_is_legal(legacy[-1]):
            raise ValueError("Legacy replay needs material projection, clipping or has an illegal finish")
        pairs = tuple(zip(states, legacy, strict=True))
        state_errors = {label: max(abs(getattr(raw, field) - getattr(old, field)) for raw, old in pairs)
                        for label, field in (("fuel_mj", "fuel_energy_mj"), ("battery_mj", "battery_mj"),
                                             ("mass_kg", "car_mass_kg"), ("wear", "tyre_wear"))}
        if (max(state_errors.values()) > tolerance
                or any((raw.compound, raw.compound_changed, raw.outlap, raw.lap)
                       != (old.compound, old.compound_changed, old.outlap, old.lap) for raw, old in pairs)):
            raise ValueError("Legacy replay disagrees with solver resource/tyre/discrete trajectory")
        discrepancy = abs(legacy[-1].race_time_s - terminal.race_time_s)
        if discrepancy > n * self.map.approximation_bound_s + 1e-6:
            raise ValueError("Legacy replay exceeds the declared smooth/piecewise objective bound")
        return StrategyReplay(tuple(actions), tuple(states), terminal.race_time_s, legacy[-1].race_time_s,
                              violation, terminal.fuel_energy_mj, terminal.battery_mj, float(adjustment), state_errors)

    def backend(self, settings: SolverSettings) -> Any:
        """Open-source IPOPT plugin with fixed options; no fallback or global claim."""
        return self.map._ca.nlpsol("strategy_ipopt", "ipopt", self.nlp,
                                  {"print_time": False, "ipopt.print_level": 0, "ipopt.sb": "yes",
                                   "ipopt.max_iter": settings.max_iterations, "ipopt.tol": settings.solver_tolerance,
                                   "ipopt.acceptable_tol": settings.solver_tolerance,
                                   "ipopt.constr_viol_tol": settings.solver_tolerance,
                                   "ipopt.bound_relax_factor": 0., "error_on_fail": False})


class EnumeratedStrategySolver:
    """Complete bounded pit enumeration, deterministic multistart LOCAL continuous solves."""

    def __init__(self, model: PaperStrategyModel, settings: SolverSettings | None = None,
                 battery_smoothing_mj: float = .01) -> None:
        self.model, self.settings, self.eps = model, settings or SolverSettings(), battery_smoothing_mj

    def solve(self, initial_compound: TyreCompound = TyreCompound.MEDIUM,
              pit_window: tuple[int, int] | None = None) -> StrategySolverResult:
        settings = self.settings
        plans = enumerate_pit_plans(self.model, initial_compound, pit_window, settings)
        starts = energy_starts(self.model)
        report: dict[str, Any] = {"schema_version": "apex-strategy-solver-v1", "classification": "ADAPTATION",
                                  "method": "ENUMERATED_LOCAL_IPOPT_WITH_FEASIBLE_INCUMBENTS", "global_optimality_certified": False,
                                  "parameter_truth_label": "PRIOR", "calibrated": False,
                                  "parameters": asdict(self.model.p),
                                  "wear_coefficients": {k.value: asdict(v) for k, v in self.model.wear.items()},
                                  "settings": asdict(settings), "plans": len(plans), "starts_per_plan": len(starts),
                                  "pit_window": list(pit_window) if pit_window is not None else [0, self.model.p.total_laps - 2],
                                  "start_vectors": [x.tolist() for x in starts], "attempts": []}
        best = None
        begin = perf_counter()
        for plan in plans:
            problem = FixedPlanProblem(self.model, plan, initial_compound, self.eps)
            report["lap_map"] = problem.map.metadata()
            try:
                backend = problem.backend(settings)
            except RuntimeError as exc:
                report["attempts"].append({"plan": [p.value if p else None for p in plan],
                                            "accepted": False, "reason": str(exc), "stage": "plugin_creation"})
                continue
            for start_index, start in enumerate(starts):
                attempt = {"plan": [p.value if p else None for p in plan], "start_index": start_index, "accepted": False}
                attempt_begin = perf_counter()
                try:
                    raw = backend(x0=start, lbx=problem.lbx, ubx=problem.ubx, lbg=problem.lbg, ubg=problem.ubg)
                    stats = backend.stats()
                    attempt.update(status=stats.get("return_status", "unknown"), solver_success=bool(stats.get("success", False)),
                                   iterations=int(stats.get("iter_count", -1)))
                    if not stats.get("success", False):
                        raise ValueError("IPOPT did not report success")
                    solution = problem.replay(np.asarray(raw["x"]).reshape(-1), settings.primal_tolerance)
                    reported = float(raw["f"])
                    if not isfinite(reported) or abs(reported - solution.smooth_race_time_s) > 1e-8:
                        raise ValueError("IPOPT objective disagrees with independent replay")
                    attempt.update(nlp_objective_s=solution.smooth_race_time_s, selected_source="nlp")
                    # A successful local solve must not discard a better, independently feasible start.
                    # Failed/invalid NLP calls still abstain; starts never bypass that acceptance gate.
                    try:
                        incumbent = problem.replay(start, settings.primal_tolerance)
                    except ValueError as exc:
                        attempt["start_rejection"] = str(exc)
                    else:
                        attempt["feasible_start_objective_s"] = incumbent.smooth_race_time_s
                        if incumbent.smooth_race_time_s < solution.smooth_race_time_s:
                            solution = incumbent
                            attempt["selected_source"] = "feasible_start"
                    attempt.update(accepted=True, smooth_race_time_s=solution.smooth_race_time_s,
                                   max_primal_violation=solution.max_primal_violation,
                                   terminal_fuel_mj=solution.terminal_fuel_mj, terminal_battery_mj=solution.terminal_battery_mj)
                    if best is None or solution.smooth_race_time_s < best.smooth_race_time_s:
                        best = solution
                        report["selected_attempt"] = len(report["attempts"])
                except (ValueError, RuntimeError) as exc:
                    attempt["reason"] = str(exc)
                attempt["runtime_s"] = perf_counter() - attempt_begin
                report["attempts"].append(attempt)
        report["runtime_s"] = perf_counter() - begin
        report["accepted_attempts"] = sum(a["accepted"] for a in report["attempts"])
        report["all_plans_have_accepted_solution"] = bool(plans) and all(
            any(a["accepted"] and a["plan"] == [p.value if p else None for p in plan] for a in report["attempts"]) for plan in plans)
        if best is None:
            raise SolverAbstention(report)
        return StrategySolverResult(best, report)
