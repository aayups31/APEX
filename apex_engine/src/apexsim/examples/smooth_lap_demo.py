"""Deterministic R015 acceptance, independent of the CasADi expression graph."""
from __future__ import annotations

import itertools
import math
import platform
from pathlib import Path

import numpy as np

from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import smooth_lap
from apexsim.research.smooth_lap import LapMode, SmoothLapMap
from apexsim.sim_core.types import TyreCompound


def _reference(model, x, compound, mode):
    """Scalar closed forms; no symbolic functions or automatic differentiation."""
    p, c = model.p, model.time_loss[compound]
    fuel, delta, mass, wear = x
    radius = math.sqrt(delta**2 + model.eps**2)
    slope_mean = (p.battery_deploy_time_s_per_mj + p.battery_recharge_time_s_per_mj) / 2
    slope_difference = (p.battery_recharge_time_s_per_mj - p.battery_deploy_time_s_per_mj) / 2
    battery = slope_mean * delta + slope_difference * (radius - model.eps)
    piecewise = delta * (p.battery_deploy_time_s_per_mj if delta < 0 else p.battery_recharge_time_s_per_mj)
    penalty = {LapMode.NORMAL: 0., LapMode.INLAP: p.pit_inlap_penalty_s,
               LapMode.OUTLAP: p.pit_outlap_penalty_s, LapMode.OUT_INLAP: p.consecutive_pit_penalty_s}[mode]
    other = (p.nominal_lap_time_s + p.mass_time_s_per_kg * (mass - p.empty_mass_kg)
             - p.fuel_energy_time_s_per_fraction * (fuel / p.nominal_fuel_energy_mj() - 1)
             + c.fresh_loss_s + c.linear_s * wear + c.quadratic_s * wear**2 + c.cubic_s * wear**3 + penalty)
    gradient = np.array([-p.fuel_energy_time_s_per_fraction / p.nominal_fuel_energy_mj(),
                         slope_mean + slope_difference * delta / radius, p.mass_time_s_per_kg,
                         c.linear_s + 2 * c.quadratic_s * wear + 3 * c.cubic_s * wear**2])
    hessian = np.zeros((4, 4))
    hessian[1, 1] = slope_difference * model.eps**2 / radius**3
    hessian[3, 3] = 2 * c.quadratic_s + 6 * c.cubic_s * wear
    return other + battery, other + piecewise, gradient, hessian


def run_smooth_lap_demo(output: Path) -> dict:
    """Fail before writing on numerical rejection; refuse an existing evidence root."""
    if output.exists():
        raise FileExistsError(f"Smooth lap evidence output already exists: {output}")
    model = SmoothLapMap()
    sources = [Path(smooth_lap.__file__), Path(__file__)]
    before = {p.name: file_sha256(p) for p in sources}
    center = np.mean([model.lower, model.upper], axis=0)
    corners = [np.array(v) for v in itertools.product(*zip(model.lower, model.upper, strict=True))]
    joins = [np.array([center[0], d, center[2], center[3]]) for d in (-1e-6, 0., 1e-6)]
    metrics = dict.fromkeys(("value_error_s", "piecewise_discrepancy_s", "analytic_gradient_error",
                            "analytic_hessian_error", "fd_gradient_error", "fd_hessian_error"), 0.)
    checks = []
    dry = (TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD)
    for compound, mode in itertools.product(dry, LapMode):
        for x in corners + joins:
            result = model.evaluate(x, compound, mode)
            value, baseline, gradient, hessian = _reference(model, x, compound, mode)
            errors = {"value_error_s": abs(result.lap_time_s - value),
                      "piecewise_discrepancy_s": abs(result.lap_time_s - baseline),
                      "analytic_gradient_error": float(np.max(abs(result.gradient - gradient))),
                      "analytic_hessian_error": float(np.max(abs(result.hessian - hessian)))}
            if (errors["value_error_s"] > 1e-10
                    or errors["piecewise_discrepancy_s"] > model.approximation_bound_s + 1e-10
                    or errors["analytic_gradient_error"] > 1e-10 or errors["analytic_hessian_error"] > 1e-10
                    or result.lap_time_s < model.lower_bound_s or result.gradient[0] > 0
                    or np.any(result.gradient[1:] < 0) or not np.array_equal(result.hessian, result.hessian.T)
                    or np.asarray(model.functions(compound, mode).box_slacks(x)).min() < 0):
                raise ValueError(f"Smooth reference/bound acceptance failed: {compound.value}/{mode.value}")
            for key, value in errors.items():
                metrics[key] = max(metrics[key], value)
            checks.append({"kind": "reference", "compound": compound.value, "mode": mode.value,
                           "coordinates": x.tolist(), "lap_time_s": result.lap_time_s, **errors})
        for delta in (-.6, -1e-6, 0., 1e-6, .3):
            x = center.copy()
            x[1] = delta
            result = model.evaluate(x, compound, mode)
            fd_gradient, fd_hessian = np.zeros(4), np.zeros((4, 4))
            for i, step in enumerate((1e-3, 1e-6, 1e-3, 1e-6)):
                offset = np.eye(4)[i] * step
                plus, minus = model.evaluate(x + offset, compound, mode), model.evaluate(x - offset, compound, mode)
                fd_gradient[i] = (plus.lap_time_s - minus.lap_time_s) / (2 * step)
                fd_hessian[:, i] = (plus.gradient - minus.gradient) / (2 * step)
            if (not np.allclose(result.gradient, fd_gradient, atol=1e-6, rtol=1e-5)
                    or not np.allclose(result.hessian, fd_hessian, atol=1e-5, rtol=1e-4)):
                raise ValueError(f"Smooth finite-difference acceptance failed: {compound.value}/{mode.value}")
            errors = {"fd_gradient_error": float(np.max(abs(result.gradient - fd_gradient))),
                      "fd_hessian_error": float(np.max(abs(result.hessian - fd_hessian)))}
            for key, value in errors.items():
                metrics[key] = max(metrics[key], value)
            checks.append({"kind": "finite_difference", "compound": compound.value, "mode": mode.value,
                           "coordinates": x.tolist(), **errors})
    for i, side in itertools.product(range(4), (-1, 1)):
        x = center.copy()
        x[i] = model.lower[i] - .01 if side < 0 else model.upper[i] + .01
        try:
            model.evaluate(x, TyreCompound.SOFT)
        except ValueError:
            pass
        else:
            raise ValueError("Smooth numeric map silently accepted an out-of-domain input")
    if before != {p.name: file_sha256(p) for p in sources}:
        raise ValueError("Smooth acceptance source changed during evaluation")
    summary = {"schema_version": "apex-smooth-lap-run-v1", "classification": "ADAPTATION",
               "maturity": "R0", "passed": True, "training_ready": False, "map": model.metadata(),
               "fixed_maps": 12, "reference_checks": 228, "finite_difference_checks": 60,
               "rejected_box_violations": 8, "maximum_errors": metrics,
               "tolerances": {"reference_absolute": 1e-10, "fd_gradient_absolute": 1e-6,
                              "fd_gradient_relative": 1e-5, "fd_hessian_absolute": 1e-5,
                              "fd_hessian_relative": 1e-4},
               "finite_difference_steps": [1e-3, 1e-6, 1e-3, 1e-6],
               "runtime": {"python": platform.python_version(), "numpy": np.__version__},
               "implementation_sha256": before}
    summary["content_sha256"] = payload_sha256(summary)
    output.mkdir(parents=True, exist_ok=False)
    write_manifest(output / "checks.json", checks)
    write_manifest(output / "summary.json", summary)
    manifest = {"schema_version": "apex-smooth-lap-manifest-v1", "summary_sha256": summary["content_sha256"],
                "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size}
                          for p in sorted(output.iterdir())}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(output / "manifest.json", manifest)
    return summary
