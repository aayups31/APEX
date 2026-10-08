import builtins
import itertools
import json
from dataclasses import replace
from math import sqrt

import numpy as np
import pytest

from apexsim.research.fienia_strategy import (
    PaperStrategyAction,
    PaperStrategyModel,
    PaperStrategyParameters,
    TireTimeLossCoefficients,
)
from apexsim.research.smooth_lap import LapMode, SmoothLapMap
from apexsim.sim_core.types import TyreCompound

ca = pytest.importorskip("casadi", reason="Optional optimization extra is required; CI installs it")
DRY = (TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD)


def independent_value(model, x, compound, mode, *, smooth):
    fuel, delta, mass, wear = x
    p, c = model.p, model.time_loss[compound]
    if smooth:
        # Scalar NumPy/Python formula; no symbolic graph reuse.
        battery = ((p.battery_deploy_time_s_per_mj + p.battery_recharge_time_s_per_mj)*delta/2
                   + (p.battery_recharge_time_s_per_mj-p.battery_deploy_time_s_per_mj)
                   *(sqrt(delta**2 + model.eps**2)-model.eps)/2)
    else:
        battery = delta * (p.battery_deploy_time_s_per_mj if delta < 0 else p.battery_recharge_time_s_per_mj)
    penalties = {LapMode.NORMAL: 0, LapMode.INLAP: p.pit_inlap_penalty_s,
                 LapMode.OUTLAP: p.pit_outlap_penalty_s, LapMode.OUT_INLAP: p.consecutive_pit_penalty_s}
    return (p.nominal_lap_time_s + p.mass_time_s_per_kg*(mass-p.empty_mass_kg)
            - p.fuel_energy_time_s_per_fraction*(fuel/p.nominal_fuel_energy_mj()-1)
            + battery + c.fresh_loss_s+c.linear_s*wear+c.quadratic_s*wear**2+c.cubic_s*wear**3+penalties[mode])


def analytic_derivatives(model, x, compound):
    p, c = model.p, model.time_loss[compound]
    delta, wear = x[1], x[3]
    radius = sqrt(delta**2+model.eps**2)
    battery_gradient = (p.battery_deploy_time_s_per_mj+p.battery_recharge_time_s_per_mj)/2 + (
        p.battery_recharge_time_s_per_mj-p.battery_deploy_time_s_per_mj)*delta/(2*radius)
    gradient = np.array([-p.fuel_energy_time_s_per_fraction/p.nominal_fuel_energy_mj(),
                         battery_gradient, p.mass_time_s_per_kg,
                         c.linear_s+2*c.quadratic_s*wear+3*c.cubic_s*wear**2])
    hessian = np.zeros((4, 4))
    hessian[1, 1] = (p.battery_recharge_time_s_per_mj-p.battery_deploy_time_s_per_mj)*model.eps**2/(2*radius**3)
    hessian[3, 3] = 2*c.quadratic_s+6*c.cubic_s*wear
    return gradient, hessian


@pytest.mark.parametrize("compound,mode", list(itertools.product(DRY, LapMode)))
def test_all_fixed_maps_match_reference_bound_and_analytic_derivatives(compound, mode):
    model = SmoothLapMap()
    starter = PaperStrategyModel(model.p, time_loss_coefficients=model.time_loss)
    points = [np.array(v) for v in itertools.product(*zip(model.lower, model.upper, strict=True))]
    middle = np.mean([model.lower, model.upper], axis=0)
    points += [np.array([middle[0], delta, middle[2], middle[3]]) for delta in (-1e-6, 0, 1e-6)]
    for x in points:
        result = model.evaluate(x, compound, mode)
        reference = independent_value(model, x, compound, mode, smooth=True)
        baseline = independent_value(model, x, compound, mode, smooth=False)
        # Pace-only parity: these box points need not be feasible race states.
        state = replace(starter.initial_state(compound), car_mass_kg=x[2], tyre_wear=x[3],
                        outlap=mode in (LapMode.OUTLAP, LapMode.OUT_INLAP))
        action = PaperStrategyAction(x[0], x[1], compound if mode in (LapMode.INLAP, LapMode.OUT_INLAP) else None)
        starter_value = starter._nominal_lap_time(state, action) + starter.time_loss[compound].evaluate(x[3])
        assert baseline == pytest.approx(starter_value, abs=1e-10, rel=0)
        assert result.lap_time_s == pytest.approx(reference, abs=1e-10, rel=0)
        assert abs(result.lap_time_s-baseline) <= model.approximation_bound_s+1e-10
        assert result.lap_time_s >= model.lower_bound_s
        gradient, hessian = analytic_derivatives(model, x, compound)
        np.testing.assert_allclose(result.gradient, gradient, atol=1e-10, rtol=0)
        np.testing.assert_allclose(result.hessian, hessian, atol=1e-10, rtol=0)
        assert np.array_equal(result.hessian, result.hessian.T)
        assert result.gradient[0] <= 0 and np.all(result.gradient[1:] >= 0)


@pytest.mark.parametrize("delta", [-.6, -1e-6, 0, 1e-6, .3])
@pytest.mark.parametrize("compound", DRY)
def test_gradient_and_hessian_finite_differences_across_battery_join(delta, compound):
    model = SmoothLapMap()
    x = np.mean([model.lower, model.upper], axis=0)
    x[1] = delta
    result = model.evaluate(x, compound)
    steps = np.array([1e-3, 1e-6, 1e-3, 1e-6])
    fd_gradient, fd_hessian = np.zeros(4), np.zeros((4, 4))
    for i, step in enumerate(steps):
        offset = np.eye(4)[i]*step
        plus, minus = model.evaluate(x+offset, compound), model.evaluate(x-offset, compound)
        fd_gradient[i] = (plus.lap_time_s-minus.lap_time_s)/(2*step)
        fd_hessian[:, i] = (plus.gradient-minus.gradient)/(2*step)
    np.testing.assert_allclose(result.gradient, fd_gradient, atol=1e-6, rtol=1e-5)
    np.testing.assert_allclose(result.hessian, fd_hessian, atol=1e-5, rtol=1e-4)


def test_mx_composition_and_mandatory_domain_slacks():
    model = SmoothLapMap()
    functions = model.functions(TyreCompound.MEDIUM)
    x = ca.MX.sym("x", 4)
    composed = ca.Function("composed", [x], [functions.value(x), ca.jacobian(functions.value(x), x)])
    middle = np.mean([model.lower, model.upper], axis=0)
    value, gradient = composed(middle)
    assert float(value) == model.evaluate(middle, TyreCompound.MEDIUM).lap_time_s
    np.testing.assert_allclose(np.asarray(gradient).reshape(4), model.evaluate(middle, TyreCompound.MEDIUM).gradient)
    assert np.asarray(functions.box_slacks(middle)).min() >= 0
    outside = middle.copy()
    outside[3] = 2
    assert np.asarray(functions.box_slacks(outside)).min() < 0
    # Symbolic extensions are unrestricted; safe numeric calls refuse them.
    assert np.isfinite(float(functions.value(outside)))
    with pytest.raises(ValueError, match="outside"):
        model.evaluate(outside, TyreCompound.MEDIUM)


@pytest.mark.parametrize("index", range(4))
@pytest.mark.parametrize("side", [-1, 1])
def test_each_numeric_bound_violation_fails_without_clipping(index, side):
    model = SmoothLapMap()
    x = np.mean([model.lower, model.upper], axis=0)
    x[index] = model.lower[index]-.01 if side < 0 else model.upper[index]+.01
    with pytest.raises(ValueError, match="no clipping"):
        model.evaluate(x, TyreCompound.SOFT)


@pytest.mark.parametrize("values", [[1, 2], [[1, 2], [3, 4]], [80, 0, 850, float("nan")]])
def test_bad_shapes_and_nonfinite_coordinates_fail(values):
    with pytest.raises(ValueError, match="four finite"):
        SmoothLapMap().evaluate(values, TyreCompound.SOFT)


def test_bad_modes_coefficients_smoothing_and_positive_bound_fail():
    model = SmoothLapMap()
    x = np.mean([model.lower, model.upper], axis=0)
    for compound, mode in ((TyreCompound.WET, LapMode.NORMAL), (TyreCompound.SOFT, "unknown")):
        with pytest.raises(ValueError):
            model.evaluate(x, compound, mode)
    extended = SmoothLapMap(time_loss_coefficients={**model.time_loss,
                                                  TyreCompound.WET: model.time_loss[TyreCompound.SOFT]})
    with pytest.raises(ValueError, match="supported dry"):
        extended.evaluate(x, TyreCompound.WET)
    for eps in (0, -1, float("nan")):
        with pytest.raises(ValueError, match="smoothing"):
            SmoothLapMap(battery_smoothing_mj=eps)
    with pytest.raises(ValueError, match="nonnegative"):
        SmoothLapMap(replace(PaperStrategyParameters(), mass_time_s_per_kg=-.1))
    with pytest.raises(ValueError, match="positive lap time"):
        SmoothLapMap(replace(PaperStrategyParameters(), nominal_lap_time_s=.1))
    with pytest.raises(ValueError, match="nonnegative"):
        SmoothLapMap(time_loss_coefficients={c:TireTimeLossCoefficients(0, -1, 0) for c in DRY})


def test_reversed_battery_slopes_still_respect_error_and_positive_lower_bound():
    model = SmoothLapMap(replace(PaperStrategyParameters(), battery_deploy_time_s_per_mj=.2,
                                battery_recharge_time_s_per_mj=.8))
    x = np.array(model.lower)
    result = model.evaluate(x, TyreCompound.SOFT)
    assert result.lap_time_s >= model.lower_bound_s
    assert abs(result.lap_time_s-independent_value(model,x,TyreCompound.SOFT,LapMode.NORMAL,smooth=False)) <= model.approximation_bound_s


def test_optional_dependency_error_is_actionable(monkeypatch):
    original = builtins.__import__
    def missing(name, *args, **kwargs):
        if name == "casadi":
            raise ImportError("fixture: absent optimization extra")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", missing)
    with pytest.raises(RuntimeError, match=r"apexsim\[optimization\]"):
        SmoothLapMap()


def test_acceptance_cli_seals_artifacts_and_refuses_overwrite(tmp_path):
    from typer.testing import CliRunner

    from apexsim.cli import app
    from apexsim.provenance import file_sha256, payload_sha256

    output = tmp_path / "evidence"
    result = CliRunner().invoke(app, ["smooth-lap-demo", "--output", str(output)])
    assert result.exit_code == 0, result.output
    summary = json.loads(result.output)
    assert summary["passed"] and not summary["training_ready"] and summary["maturity"] == "R0"
    assert (summary["reference_checks"], summary["finite_difference_checks"], summary["rejected_box_violations"]) == (228, 60, 8)
    for name in ("summary", "manifest"):
        sealed = json.loads((output / f"{name}.json").read_text())
        digest = sealed.pop("content_sha256")
        assert payload_sha256(sealed) == digest
    manifest = json.loads((output / "manifest.json").read_text())
    assert set(manifest["files"]) == {"summary.json", "checks.json"}
    assert len(json.loads((output / "checks.json").read_text())) == 288
    for name, info in manifest["files"].items():
        assert info == {"sha256": file_sha256(output / name), "bytes": (output / name).stat().st_size}
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    result = CliRunner().invoke(app, ["smooth-lap-demo", "--output", str(output)])
    assert result.exit_code != 0 and isinstance(result.exception, FileExistsError)
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}


def test_failed_acceptance_writes_no_evidence(tmp_path, monkeypatch):
    from apexsim.examples.smooth_lap_demo import run_smooth_lap_demo

    original = SmoothLapMap.evaluate
    def faulty(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        return replace(result, lap_time_s=result.lap_time_s + 1)
    monkeypatch.setattr(SmoothLapMap, "evaluate", faulty)
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="reference/bound acceptance failed"):
        run_smooth_lap_demo(output)
    assert not output.exists()
