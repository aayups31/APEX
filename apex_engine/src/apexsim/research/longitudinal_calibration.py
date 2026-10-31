"""R030 effective specific-power/drag identification and recorded-control speed replay.

Public channels cannot identify true mass, engine/ERS power, CdA, wind or slope.
These fitted coefficients stay in research and never mutate production cars.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear

from apexsim.research.longitudinal_data import LongitudinalSection
from apexsim.sim_core.calibration import fit_longitudinal_dynamics

ROLLING_PRIOR = .015*9.81
KINDS = ("shared_drag", "drs_drag")


@dataclass(frozen=True)
class SpecificPowerDrag:
    """Effective p[W/kg], d[1/m] and fixed rolling PRIOR[m/s2]."""

    power_per_mass: float
    open_drag_per_mass: float
    extra_closed_drag_per_mass: float = 0.
    rolling_acceleration: float = ROLLING_PRIOR

    def __post_init__(self) -> None:
        if (not np.isfinite(list(self.as_dict().values())).all() or not 100 <= self.power_per_mass <= 2000
                or not 0 <= self.open_drag_per_mass <= .005 or not 0 <= self.extra_closed_drag_per_mass <= .005
                or self.rolling_acceleration < 0):
            raise ValueError("R030 effective parameters violate finite physical-prior bounds")

    def as_dict(self) -> dict[str, float]:
        return {"power_per_mass": self.power_per_mass, "open_drag_per_mass": self.open_drag_per_mass,
                "extra_closed_drag_per_mass": self.extra_closed_drag_per_mass,
                "rolling_acceleration": self.rolling_acceleration}

    def acceleration(self, speed: float, throttle: float, drs: int) -> float:
        if not np.isfinite([speed, throttle, drs]).all() or not 0 < speed <= 120 or not 0 <= throttle <= 1 or drs not in (0, 1):
            raise ValueError("R030 speed/control outside finite replay domain; no clipping")
        drag = self.open_drag_per_mass+self.extra_closed_drag_per_mass*(1-drs)
        return self.power_per_mass*throttle/speed-drag*speed**2-self.rolling_acceleration

    def derivatives(self, speed: float, throttle: float, drs: int) -> tuple[float, np.ndarray]:
        """Analytic da/dv and da/d[p,d_open,d_extra] for equation audit."""
        self.acceleration(speed, throttle, drs)
        drag = self.open_drag_per_mass+self.extra_closed_drag_per_mass*(1-drs)
        return (-self.power_per_mass*throttle/speed**2-2*drag*speed,
                np.array([throttle/speed, -speed**2, -(1-drs)*speed**2]))


def physical_prior() -> SpecificPowerDrag:
    closed_drag = .5*1.225*1.05/900
    return SpecificPowerDrag(740000*.92/900, closed_drag*.84, closed_drag*.16)


def identification_arrays(sections: list[LongitudinalSection], kind: str,
                          rolling: float = ROLLING_PRIOR) -> tuple[np.ndarray, np.ndarray]:
    if not sections or kind not in KINDS or not np.isfinite(rolling) or rolling < 0:
        raise ValueError("Invalid R030 identification inputs")
    design, targets = [], []
    for s in sections:
        if s.metadata["role"] != "train":
            raise ValueError("R030 fitting requires training events only")
        v, dt = s.speed_mps[:-1], np.diff(s.time_s)
        columns = [dt*s.throttle[:-1]/v, -dt*v**2]
        if kind == "drs_drag":
            columns.append(-dt*(1-s.drs_open[:-1])*v**2)
        design.append(np.column_stack(columns))
        targets.append(np.diff(s.speed_mps)+rolling*dt)
    return np.concatenate(design), np.concatenate(targets)


def fit_cell(sections: list[LongitudinalSection], kind: str, *, rolling: float = ROLLING_PRIOR,
             bootstrap: bool = False) -> dict:
    """Bounded convex speed-increment fit; report rank, conditioning and active bounds."""
    if len({s.cell for s in sections}) != 1:
        raise ValueError("R030 fit must retain one track/driver identity")
    x, y = identification_arrays(sections, kind, rolling)
    laps = len({s.metadata["lap_id"] for s in sections})
    if len(y) < 100 or (not bootstrap and laps < 5):
        raise ValueError("R030 fit lacks100 training intervals/five laps")
    scale = np.sqrt(np.mean(x*x, axis=0))
    normalized = x/np.where(scale > 0, scale, 1.)
    singular = np.linalg.svd(normalized, compute_uv=False)
    condition = float(singular[0]/singular[-1]) if singular[-1] > 0 else None
    if np.linalg.matrix_rank(normalized) != x.shape[1] or condition is None or condition > 1e4:
        raise ValueError("R030 training design is unidentifiable/rank deficient")
    lower, upper = np.array([100., *([0.]*(x.shape[1]-1))]), np.array([2000., *([.005]*(x.shape[1]-1))])
    fitted = lsq_linear(normalized, y, bounds=(lower*scale, upper*scale), tol=1e-12, max_iter=1000)
    if not fitted.success or not np.isfinite(fitted.x).all():
        raise ValueError("R030 bounded least-squares solver failed")
    coefficients = fitted.x/scale
    model = SpecificPowerDrag(float(coefficients[0]), float(coefficients[1]), float(coefficients[2]) if len(coefficients) == 3 else 0., rolling)
    residual = x@coefficients-y
    return {"kind": kind, "cell": sections[0].cell, "parameters": model.as_dict(),
            "intervals": len(y), "laps": laps, "singular_values_normalized": singular.tolist(),
            "normalized_condition_number": condition, "training_column_rms": scale.tolist(),
            "active_bounds": fitted.active_mask.tolist(), "solver_optimality": float(fitted.optimality),
            "increment_rmse_mps": float(np.sqrt(np.mean(residual**2))),
            "training_speed_range_mps": [float(min(s.speed_mps.min() for s in sections)), float(max(s.speed_mps.max() for s in sections))],
            "parameter_truth": "CALIBRATED_EFFECTIVE_RATIOS; NOT_IDENTIFIED_ABSOLUTE_POWER_OR_CDA"}


def fit_candidates(training: list[LongitudinalSection]) -> dict:
    cells = {s.cell for s in training}
    if cells != {t+"/"+d for t in ("bahrain", "monza") for d in ("4", "44")}:
        raise ValueError("R030 requires all four training track/driver cells")
    result = {}
    for kind in KINDS:
        fits, failures = {}, {}
        for cell in sorted(cells):
            try:
                fits[cell] = fit_cell([s for s in training if s.cell == cell], kind)
            except ValueError as exc:
                failures[cell] = str(exc)
        result[kind] = {"eligible": not failures, "cells": fits, "failures": failures}
    return result


def integrate_speed(initial_speed: float, time_s: np.ndarray, throttle: np.ndarray, drs: np.ndarray,
                    rhs: Callable[[float, float, int], float], *, max_step_s: float = .05) -> np.ndarray:
    """RK4, recorded left-held controls, no observation resets or velocity clipping."""
    n = len(time_s)
    if (n < 2 or throttle.shape != (n,) or drs.shape != (n,) or not np.isfinite([time_s, throttle, drs]).all()
            or np.any(np.diff(time_s) <= 0) or not np.isfinite(max_step_s) or max_step_s <= 0
            or np.any((throttle < 0) | (throttle > 1)) or not np.all(np.isin(drs, [0, 1]))
            or not np.isfinite(initial_speed) or not 0 < initial_speed <= 120):
        raise ValueError("Invalid R030 replay state/times/controls")
    values = [float(initial_speed)]
    v = float(initial_speed)
    for i, dt in enumerate(np.diff(time_s)):
        steps = int(np.ceil(dt/max_step_s))
        h, u, z = float(dt/steps), float(throttle[i]), int(drs[i])
        for _ in range(steps):
            k1 = rhs(v, u, z)
            k2 = rhs(v+h*k1/2, u, z)
            k3 = rhs(v+h*k2/2, u, z)
            k4 = rhs(v+h*k3, u, z)
            v += h*(k1+2*k2+2*k3+k4)/6
            if not np.isfinite(v) or not 0 < v <= 120:
                raise ValueError("R030 integration outside positive bounded speed domain")
        values.append(v)
    return np.array(values)


def fit_legacy(training: list[LongitudinalSection]) -> dict:
    """Existing Huber diagnostic on the same native training intervals, without mapping/clipping."""
    result = {}
    for cell in sorted({s.cell for s in training}):
        rows = []
        for section in [s for s in training if s.cell == cell]:
            if section.metadata["role"] != "train":
                raise ValueError("R030 legacy baseline must fit training only")
            for i, dt in enumerate(np.diff(section.time_s)):
                rows.append({"speed_mps": section.speed_mps[i], "throttle": section.throttle[i], "brake": 0.,
                             "acceleration_mps2": (section.speed_mps[i+1]-section.speed_mps[i])/dt})
        result[cell] = fit_longitudinal_dynamics(pd.DataFrame(rows)).to_dict()
    return result


def replay_section(section: LongitudinalSection, method: str, cells: dict | None = None,
                   *, max_step_s: float = .05) -> np.ndarray:
    """No future observed speed is read: only initial speed and causal past slope."""
    v0 = float(section.speed_mps[0])
    if method == "constant_speed":
        return np.full(len(section.time_s), v0)
    if method == "constant_acceleration":
        # Raw extrapolation is retained, with any nonphysical values reported.
        return v0+section.initial_acceleration_mps2*(section.time_s-section.time_s[0])
    if method == "physical_prior":
        rhs = physical_prior().acceleration
    elif method == "legacy_huber":
        if cells is None:
            raise ValueError("R030 legacy replay requires fitted coefficients")
        fit = cells[section.cell]

        def rhs(v: float, u: float, z: int) -> float:
            return -fit["rolling_accel"]+fit["throttle_accel_gain"]*u-fit["drag_accel_coeff"]*v*v
    elif method in KINDS:
        if cells is None:
            raise ValueError("R030 calibrated replay requires fitted coefficients")
        rhs = SpecificPowerDrag(**cells[section.cell]["parameters"]).acceleration
    else:
        raise ValueError("Unknown R030 replay method")
    return integrate_speed(v0, section.time_s, section.throttle, section.drs_open, rhs, max_step_s=max_step_s)
