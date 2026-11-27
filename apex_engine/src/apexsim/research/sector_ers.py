"""Sector-level battery accounting and causal energy allocation for research."""

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from time import perf_counter
from typing import Literal

import numpy as np
from scipy.optimize import linprog

EPS = 1e-9


@dataclass(frozen=True)
class Battery:
    capacity_mj: float
    terminal_minimum_mj: float
    deploy_efficiency: float = 0.8
    harvest_efficiency: float = 0.8

    def __post_init__(self) -> None:
        if (
            not all(map(isfinite, (self.capacity_mj, self.terminal_minimum_mj)))
            or not 0 <= self.terminal_minimum_mj <= self.capacity_mj
            or self.capacity_mj <= 0
            or not 0 < self.deploy_efficiency <= 1
            or not 0 < self.harvest_efficiency <= 1
        ):
            raise ValueError("Invalid ERS battery bounds or efficiency")


@dataclass(frozen=True)
class Sector:
    mode: Literal["deploy", "harvest", "coast"]
    duration_s: float
    wheel_power_limit_w: float
    wheel_opportunity_mj: float
    seconds_per_storage_mj: float

    def __post_init__(self) -> None:
        values = (
            self.duration_s,
            self.wheel_power_limit_w,
            self.wheel_opportunity_mj,
            self.seconds_per_storage_mj,
        )
        if self.mode not in ("deploy", "harvest", "coast") or (
            not all(map(isfinite, values)) or self.duration_s <= 0 or min(values[1:]) < 0
        ):
            raise ValueError("Invalid ERS sector")

    def bounds(self, battery: Battery) -> tuple[float, float]:
        """Return signed storage action limits, in MJ."""
        work = min(self.wheel_opportunity_mj, self.duration_s * self.wheel_power_limit_w / 1e6)
        if self.mode == "deploy":
            return -work / battery.deploy_efficiency, 0.0
        if self.mode == "harvest":
            return 0.0, work * battery.harvest_efficiency
        return 0.0, 0.0


@dataclass(frozen=True)
class Transition:
    charge_mj: float
    storage_delta_mj: float
    wheel_work_mj: float
    conversion_loss_mj: float
    time_delta_s: float


def advance(battery: Battery, state_mj: float, sector: Sector, delta_mj: float) -> Transition:
    """Apply one legal command. Positive wheel work means propulsion."""
    if not isfinite(state_mj) or not 0 <= state_mj <= battery.capacity_mj:
        raise ValueError("Initial ERS charge outside battery bounds")
    lo, hi = sector.bounds(battery)
    if not isfinite(delta_mj) or not lo - EPS <= delta_mj <= hi + EPS:
        raise ValueError("ERS action outside sector opportunity")
    if not -EPS <= state_mj + delta_mj <= battery.capacity_mj + EPS:
        raise ValueError("ERS action outside battery bounds")
    # Canonicalize only solver roundoff at an active state or action bound.
    lower, upper = max(lo, -state_mj), min(hi, battery.capacity_mj - state_mj)
    delta = min(upper, max(lower, delta_mj))
    wheel = -delta * battery.deploy_efficiency if delta < 0 else -delta / battery.harvest_efficiency
    return Transition(state_mj + delta, delta, wheel, -wheel - delta, delta * sector.seconds_per_storage_mj)


class InfeasibleEnergyPlan(ValueError):
    """The known sector constraints prevent a terminal-feasible plan."""


def allocate(battery: Battery, state_mj: float, forecast: Sequence[Sector]) -> tuple[float, ...]:
    """Solve the remaining linear horizon with hard path and terminal bounds."""
    if not forecast or not isfinite(state_mj) or not 0 <= state_mj <= battery.capacity_mj:
        raise ValueError("Invalid initial charge or empty energy horizon")
    n = len(forecast)
    cumulative = np.tril(np.ones((n, n)))
    cap = np.full(n, battery.capacity_mj - state_mj)
    lower = np.full(n, state_mj)
    lower[-1] -= battery.terminal_minimum_mj
    result = linprog(
        [s.seconds_per_storage_mj for s in forecast],
        A_ub=np.vstack((cumulative, -cumulative)),
        b_ub=np.r_[cap, lower],
        bounds=[s.bounds(battery) for s in forecast],
        method="highs",
        options={"primal_feasibility_tolerance": EPS, "dual_feasibility_tolerance": EPS},
    )
    if result.status == 2:
        raise InfeasibleEnergyPlan("Terminal ERS charge is infeasible")
    if not result.success:
        raise RuntimeError(f"ERS allocation failed: {result.message}")
    state = state_mj
    actions = []
    for sector, delta in zip(forecast, result.x, strict=True):
        transition = advance(battery, state, sector, float(delta))
        state = transition.charge_mj
        actions.append(transition.storage_delta_mj)
    if state < battery.terminal_minimum_mj - EPS:
        raise RuntimeError("Solver replay failed the terminal ERS bound")
    return tuple(actions)


def feedback_step(
    battery: Battery, state_mj: float, current: Sector, future: Sequence[Sector]
) -> tuple[Transition, float]:
    """Observe the current sector and charge, then apply exactly one action."""
    start = perf_counter()
    actions = allocate(battery, state_mj, (current, *future))
    return advance(battery, state_mj, current, actions[0]), perf_counter() - start
