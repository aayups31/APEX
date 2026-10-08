"""R015: bounded synthetic C-infinity lap maps for fixed compound and lap mode.

Numeric calls reject domain violations. Symbolic graphs extend outside the box:
an optimizer must impose the exposed box constraints AND race resource constraints.
No production transition, fitted paper map or car calibration is replaced.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from math import isfinite
from typing import Any

import numpy as np
from numpy.typing import ArrayLike

from apexsim.research.fienia_strategy import (
    PaperStrategyModel,
    PaperStrategyParameters,
    TireTimeLossCoefficients,
)
from apexsim.sim_core.types import TyreCompound

MAP_VERSION = "apex-smooth-lap-map-v1"
COORDINATES = ("fuel_energy_mj", "battery_delta_mj", "car_mass_kg", "tyre_wear")


class LapMode(str, Enum):
    NORMAL = "normal"
    INLAP = "inlap"
    OUTLAP = "outlap"
    OUT_INLAP = "out_inlap"


@dataclass(frozen=True)
class SymbolicLapFunctions:
    """CasADi functions of x[4]; bounds are mandatory for optimization callers."""

    value: Any
    gradient: Any
    hessian: Any
    box_slacks: Any


@dataclass(frozen=True)
class LapMapEvaluation:
    lap_time_s: float
    gradient: np.ndarray
    hessian: np.ndarray


class SmoothLapMap:
    """A smooth counterpart to declared synthetic lap terms, not a race solver."""

    def __init__(self, parameters: PaperStrategyParameters | None = None,
                 time_loss_coefficients: dict[TyreCompound, TireTimeLossCoefficients] | None = None,
                 battery_smoothing_mj: float = .01) -> None:
        model = PaperStrategyModel(parameters, time_loss_coefficients=time_loss_coefficients)
        self.p, self.time_loss = model.p, dict(model.time_loss)
        if not isfinite(battery_smoothing_mj) or battery_smoothing_mj <= 0:
            raise ValueError("battery_smoothing_mj must be finite and positive")
        self.eps = float(battery_smoothing_mj)
        positive_terms = (self.p.nominal_lap_time_s, self.p.mass_time_s_per_kg,
                          self.p.fuel_energy_time_s_per_fraction, self.p.battery_deploy_time_s_per_mj,
                          self.p.battery_recharge_time_s_per_mj, self.p.pit_inlap_penalty_s,
                          self.p.pit_outlap_penalty_s, self.p.consecutive_pit_penalty_s,
                          *(v for coeff in self.time_loss.values() for v in vars(coeff).values()))
        if not all(isfinite(v) and v >= 0 for v in positive_terms):
            raise ValueError("Smooth map requires finite nonnegative pace/tyre coefficients")
        self.lower_bound_s = (self.p.nominal_lap_time_s - .1 * self.p.fuel_energy_time_s_per_fraction
                              + self.p.battery_deploy_time_s_per_mj * self.p.battery_delta_min_mj
                              - self.approximation_bound_s)
        if self.lower_bound_s <= 0:
            raise ValueError("Smooth map cannot certify positive lap time over the declared domain")
        nominal = self.p.nominal_fuel_energy_mj()
        self.lower = (.9 * nominal, self.p.battery_delta_min_mj, self.p.empty_mass_kg, 0.)
        self.upper = (1.1 * nominal, self.p.battery_delta_max_mj,
                      self.p.empty_mass_kg + self.p.initial_fuel_kg, 1.25)
        try:
            import casadi as ca
        except ImportError as exc:
            raise RuntimeError("Smooth lap maps require the optional dependency; install apexsim[optimization]") from exc
        self._ca = ca
        self._functions: dict[tuple[TyreCompound, LapMode], SymbolicLapFunctions] = {}

    @property
    def approximation_bound_s(self) -> float:
        return .5 * abs(self.p.battery_recharge_time_s_per_mj - self.p.battery_deploy_time_s_per_mj) * self.eps

    def metadata(self) -> dict:
        return {"schema_version": MAP_VERSION, "classification": "ADAPTATION",
                "parameter_truth_label": "PRIOR", "calibrated": False,
                "coordinates": list(COORDINATES), "coordinate_units": ["MJ/lap", "MJ/lap", "kg", "dimensionless"],
                "lower": list(self.lower), "upper": list(self.upper),
                "battery_smoothing_mj": self.eps, "battery_approximation_bound_s": self.approximation_bound_s,
                "certified_lap_time_lower_bound_s": self.lower_bound_s, "casadi_version": self._ca.__version__,
                "parameters": asdict(self.p), "tyre_coefficients": {k.value: asdict(v) for k, v in self.time_loss.items()},
                "limitations": ["Synthetic pace maps only; no fitted FIENI data or current-battery pace dependence.",
                                "Fixed discrete mode/compound; resource feasibility is a separate constraint.",
                                "Symbolic graphs do not enforce their boxes; numeric wrapper rejects extrapolation.",
                                "No clipping or state/action projection inside the smooth graph."]}

    def functions(self, compound: TyreCompound, mode: LapMode | str = LapMode.NORMAL) -> SymbolicLapFunctions:
        if (not isinstance(compound, TyreCompound)
                or compound not in (TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD)):
            raise ValueError("Smooth lap maps require a supported dry TyreCompound")
        try:
            mode = LapMode(mode)
        except (ValueError, TypeError) as exc:
            raise ValueError("Unknown smooth lap mode") from exc
        key = compound, mode
        if key not in self._functions:
            ca, p = self._ca, self.p
            x = ca.SX.sym("x", 4)
            fuel, delta, mass, wear = (x[i] for i in range(4))
            battery = (.5 * (p.battery_deploy_time_s_per_mj + p.battery_recharge_time_s_per_mj) * delta
                       + .5 * (p.battery_recharge_time_s_per_mj - p.battery_deploy_time_s_per_mj)
                       * (ca.sqrt(delta * delta + self.eps * self.eps) - self.eps))
            coeff = self.time_loss[compound]
            tyre = coeff.fresh_loss_s + coeff.linear_s * wear + coeff.quadratic_s * wear**2 + coeff.cubic_s * wear**3
            penalty = {LapMode.NORMAL: 0., LapMode.INLAP: p.pit_inlap_penalty_s,
                       LapMode.OUTLAP: p.pit_outlap_penalty_s, LapMode.OUT_INLAP: p.consecutive_pit_penalty_s}[mode]
            value = (p.nominal_lap_time_s + p.mass_time_s_per_kg * (mass - p.empty_mass_kg)
                     - p.fuel_energy_time_s_per_fraction * (fuel / p.nominal_fuel_energy_mj() - 1.)
                     + battery + tyre + penalty)
            gradient = ca.gradient(value, x)
            hessian = ca.hessian(value, x)[0]
            slacks = ca.vertcat(x - ca.DM(self.lower), ca.DM(self.upper) - x)
            name = f"lap_{compound.value}_{mode.value}"
            self._functions[key] = SymbolicLapFunctions(
                ca.Function(name, [x], [value]), ca.Function(name + "_gradient", [x], [gradient]),
                ca.Function(name + "_hessian", [x], [hessian]), ca.Function(name + "_box", [x], [slacks]))
        return self._functions[key]

    def evaluate(self, coordinates: ArrayLike, compound: TyreCompound,
                 mode: LapMode | str = LapMode.NORMAL) -> LapMapEvaluation:
        x = np.asarray(coordinates, dtype=float)
        if x.shape != (4,) or not np.isfinite(x).all():
            raise ValueError("Smooth map requires four finite coordinates in declared order")
        if np.any(x < self.lower) or np.any(x > self.upper):
            raise ValueError("Smooth map input is outside its declared domain; no clipping or extrapolation")
        functions = self.functions(compound, mode)
        result = LapMapEvaluation(float(functions.value(x)), np.asarray(functions.gradient(x)).reshape(4),
                                  np.asarray(functions.hessian(x)))
        if not np.isfinite(result.lap_time_s) or not np.isfinite(result.gradient).all() or not np.isfinite(result.hessian).all():
            raise ValueError("Nonfinite smooth map value/derivative")
        return result
