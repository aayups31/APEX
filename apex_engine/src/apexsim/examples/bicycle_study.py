"""R031 frozen synthetic force/stability campaign with immutable scientific replay."""
from __future__ import annotations

import itertools
import json
import platform
import subprocess
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import scipy
from scipy.linalg import expm

from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import bicycle, bicycle_audit
from apexsim.research.bicycle import (
    BicycleControl,
    BicycleParameters,
    BicycleState,
    BicycleSupportError,
    StraightPowerDragInput,
    axle_force,
    bicycle_rhs,
    integrate_bicycle,
    kinetic_energy_j,
    lateral_linear_system,
)
from apexsim.research.bicycle_audit import independent_support_exit, independent_trajectory
from apexsim.research.longitudinal_calibration import SpecificPowerDrag, integrate_speed

VERSION = "apex-bicycle-dynamics-v1"
PROTOCOL = Path(__file__).resolve().parents[4]/"research/protocols/BICYCLE_DYNAMICS.md"
STATE_UNITS = ["m", "m", "rad", "m/s", "m/s", "rad/s"]


def frozen_cases() -> list[dict]:
    """Fixed synthetic regimes, not a selected subset of empirical outcomes."""
    p = BicycleParameters()
    cases = []

    def add(name, duration, control, *, initial=None, params=p):
        t = np.linspace(0., duration, round(duration/.1)+1)
        commands = control if isinstance(control, list) else [control]*(len(t)-1)
        cases.append({"name": name, "params": params, "initial": initial or BicycleState(), "time_s": t, "commands": commands})

    add("coast", 3., BicycleControl(resistance_n=300))
    add("drive", 3., BicycleControl(rear_fx_request_n=2500))
    add("brake", 3., BicycleControl(front_fx_request_n=-2000, rear_fx_request_n=-1500))
    add("left", 3., BicycleControl(.02))
    add("right", 3., BicycleControl(-.02))
    add("combined_brake", 3., BicycleControl(.02, -2000, -1000))
    add("near_limit_drive", 1., BicycleControl(.01, rear_fx_request_n=6200), initial=BicycleState(vx_mps=30))
    add("pulse", 4., [BicycleControl(.03 if i < 5 else -.03 if i < 10 else 0.) for i in range(40)])
    add("disturbance", 6., BicycleControl(), initial=BicycleState(vy_mps=.2, yaw_rate_radps=.02))
    for v in (20, 40, 70):
        add(f"small_angle_{v}", 4., BicycleControl(1e-4), initial=BicycleState(vx_mps=v))
    add("straight_force", 2., BicycleControl(rear_fx_request_n=1800), initial=BicycleState(vx_mps=20))
    add("r030_consistency", 2., StraightPowerDragInput(SpecificPowerDrag(900., .0005)),
        initial=BicycleState(vx_mps=50), params=replace(p, mu_x=8.))
    return cases


def configuration() -> dict:
    """Portable unit-labelled protocol snapshot; no raw telemetry or trained states."""
    return {"schema_version": VERSION+"-config", "truth": "SYNTHETIC_STATES_AND_PRIOR_PARAMETERS",
            "state_order": list(BicycleState.__dataclass_fields__), "state_units": STATE_UNITS,
            "cases": [{"name": c["name"], "expected_outcome": "ABSTAIN_SUPPORT_EXIT" if c["name"] == "near_limit_drive" else "SUPPORTED",
                       "parameters": asdict(c["params"]), "initial": asdict(c["initial"]),
                       "time_s": c["time_s"].tolist(), "commands": [dict(kind="straight_power_drag" if isinstance(u, StraightPowerDragInput) else "axle_forces", **asdict(u)) for u in c["commands"]]}
                      for c in frozen_cases()]}


def _force_checks() -> dict:
    utilization, positive_power = 0., 0.
    count = 0
    for normal, mx, my, alpha, fraction in itertools.product(
            (500, 1000, 5000), (.7, 1.5), (.8, 1.7), (-.3, -.05, 0, .05, .3), (-2, -1, -.6, 0, .6, 1, 2)):
        f = axle_force(alpha, fraction*mx*normal, normal, 100000, mx, my)
        utilization = max(utilization, f.utilization_squared)
        positive_power = max(positive_power, float(f.fy_n*10*np.tan(alpha)))
        count += 1
    hand = axle_force(.08, 1200, 1000, 20000, 2, 1)
    p = BicycleParameters()
    fz, rz = p.axle_loads_n
    force_rhs, _ = bicycle_rhs(BicycleState(vx_mps=20), BicycleControl(front_fx_request_n=900, rear_fx_request_n=1800, resistance_n=450), p)
    hand_error = max(abs(fz-4905), abs(rz-3924), abs(hand.lateral_budget_n-800),
                     abs(hand.fy_n+800*np.tanh(2)), float(np.max(abs(force_rhs-[20, 0, 0, 2.5, 0, 0]))))
    return {"grid_points": count, "maximum_utilization_squared": utilization,
            "maximum_positive_slip_power_w": positive_power, "maximum_hand_fixture_error_si": hand_error,
            "passed": bool(utilization <= 1+1e-12 and positive_power <= 1e-9 and hand_error <= 1e-9)}


def _linear_checks() -> dict:
    p, eps = BicycleParameters(), 1e-6
    eigenvalues, jacobian_error = {}, 0.
    for speed in (5, 10, 20, 40, 70, 100, 110):
        a, b = lateral_linear_system(speed, p)
        vals = np.linalg.eigvals(a)
        eigenvalues[str(speed)] = [{"real_per_s": float(z.real), "imag_per_s": float(z.imag)} for z in vals]
        for j, field in enumerate(("vy_mps", "yaw_rate_radps")):
            plus = bicycle_rhs(replace(BicycleState(vx_mps=speed), **{field: eps}), BicycleControl(), p)[0][[4, 5]]
            minus = bicycle_rhs(replace(BicycleState(vx_mps=speed), **{field: -eps}), BicycleControl(), p)[0][[4, 5]]
            jacobian_error = max(jacobian_error, float(np.max(abs((plus-minus)/(2*eps)-a[:, j]))))
        plus = bicycle_rhs(BicycleState(vx_mps=speed), BicycleControl(eps), p)[0][[4, 5]]
        minus = bicycle_rhs(BicycleState(vx_mps=speed), BicycleControl(-eps), p)[0][[4, 5]]
        jacobian_error = max(jacobian_error, float(np.max(abs((plus-minus)/(2*eps)-b))))
    unstable = replace(p, front_stiffness_nprad=200000, rear_stiffness_nprad=50000)
    unstable_max = float(max(np.linalg.eigvals(lateral_linear_system(40., unstable)[0]).real))
    max_default = max(z["real_per_s"] for values in eigenvalues.values() for z in values)
    return {"eigenvalues": eigenvalues, "default_maximum_real_eigenvalue_per_s": max_default,
            "deliberate_oversteer_maximum_real_eigenvalue_per_s": unstable_max,
            "maximum_jacobian_error": jacobian_error,
            "passed": bool(max_default < 0 < unstable_max and jacobian_error <= 1e-5)}


def _abstention_case(case: dict) -> tuple[dict, dict[str, np.ndarray]]:
    """Retain the unchanged full-rear saturation failure and audit its safe prefix."""
    name, p, initial, t, commands = (case[k] for k in ("name", "params", "initial", "time_s", "commands"))
    failures = []
    for h in (.02, .01, .005):
        try:
            integrate_bicycle(initial, t, commands, p, max_step_s=h)
        except BicycleSupportError as exc:
            failures.append(exc)
        else:
            raise ValueError("R031 original saturated rear-drive challenge no longer abstains")
    boundary_time, boundary_state = independent_support_exit(initial.array(), t, commands, p)
    common = min(len(exc.partial_time_s) for exc in failures)
    prefix_t = t[:common]
    independent = independent_trajectory(initial.array(), prefix_t, commands[:common-1], p)
    arrays = {name+"__time_s": prefix_t, name+"__dop853": independent, name+"__boundary_state": boundary_state}
    errors = []
    for suffix, exc in zip(("rk4_02", "rk4_01", "rk4_005"), failures, strict=True):
        arrays[name+"__"+suffix] = exc.partial_states[:common]
        errors.append(np.max(abs(exc.partial_states[:common]-independent), axis=0))
    max_error = np.max(errors, axis=0)
    rejection = [{"max_step_s": h, "first_rejected_stage_time_s": exc.time_s,
                  "rejected_state": exc.state.tolist(), "last_supported_output_time_s": float(exc.partial_time_s[-1]),
                  "independent_exit_time_difference_s": abs(exc.time_s-boundary_time)}
                 for h, exc in zip((.02, .01, .005), failures, strict=True)]
    maximum_time_difference = max(r["independent_exit_time_difference_s"] for r in rejection)
    return ({"name": name, "outcome": "ABSTAIN_SUPPORT_EXIT", "output_nodes": common,
             "requested_duration_s": float(t[-1]), "supported_prefix_duration_s": float(prefix_t[-1]),
             "independent_exit_time_s": boundary_time, "rejection_by_step": rejection,
             "maximum_prefix_error_by_state": max_error.tolist(),
             "passed": bool(max(max_error) <= 1e-4 and maximum_time_difference <= .02)}, arrays)


def compute_evidence() -> tuple[dict, dict[str, np.ndarray]]:
    """Run every fixed case and all three timestep refinements without tuning."""
    arrays, results = {}, []
    for case in frozen_cases():
        name, p, initial, t, commands = (case[k] for k in ("name", "params", "initial", "time_s", "commands"))
        if name == "near_limit_drive":
            rejection, rejected_arrays = _abstention_case(case)
            results.append(rejection)
            arrays.update(rejected_arrays)
            continue
        paths = [integrate_bicycle(initial, t, commands, p, max_step_s=h) for h in (.02, .01, .005)]
        independent = independent_trajectory(initial.array(), t, commands, p)
        for suffix, values in zip(("rk4_02", "rk4_01", "rk4_005", "dop853"), [v.states for v in paths]+[independent], strict=True):
            arrays[name+"__"+suffix] = values
        arrays[name+"__time_s"] = t
        # All six components are reported separately; SI magnitudes are not a shared error unit.
        errors = np.max(abs(paths[1].states-independent), axis=0)
        refinement = np.max(abs(paths[1].states-paths[2].states), axis=0)
        coarse_error = np.max(abs(paths[0].states-independent), axis=0)
        monitors = paths[1].integration_checks
        extra, special_pass = {}, True
        if name.startswith("small_angle_"):
            a, b = lateral_linear_system(initial.vx_mps, p)
            equilibrium = -np.linalg.solve(a, b*1e-4)
            linear = np.array([(np.eye(2)-expm(a*s))@equilibrium for s in t])
            extra["maximum_linear_vy_error_mps"] = float(max(abs(paths[1].states[:, 4]-linear[:, 0])))
            extra["maximum_linear_yaw_error_radps"] = float(max(abs(paths[1].states[:, 5]-linear[:, 1])))
            special_pass = bool(np.allclose(paths[1].states[:, [4, 5]], linear, atol=1e-6, rtol=.01))
        if name in ("disturbance", "coast"):
            energy = np.array([kinetic_energy_j(BicycleState.from_array(s), p) for s in paths[1].states])
            extra["maximum_node_energy_increase_j"] = float(max(np.diff(energy)))
            special_pass = bool(max(np.diff(energy)) <= 1e-6)
        if name == "disturbance":
            extra["vy_recovery_fraction"] = float(abs(paths[1].states[-1, 4]/initial.vy_mps))
            extra["yaw_recovery_fraction"] = float(abs(paths[1].states[-1, 5]/initial.yaw_rate_radps))
            special_pass = special_pass and max(extra["vy_recovery_fraction"], extra["yaw_recovery_fraction"]) < .1
        if name == "straight_force":
            extra["maximum_analytical_position_error_m"] = float(max(abs(paths[1].states[:, 0]-(20*t+t*t))))
            extra["maximum_analytical_speed_error_mps"] = float(max(abs(paths[1].states[:, 3]-(20+2*t))))
            special_pass = max(extra.values()) <= 1e-9
        if name == "r030_consistency":
            model = commands[0].model
            reference = integrate_speed(50, t, np.ones(len(t)), np.zeros(len(t)), model.acceleration, max_step_s=.01)
            extra["maximum_r030_speed_error_mps"] = float(max(abs(paths[1].states[:, 3]-reference)))
            instantaneous = bicycle_rhs(initial, commands[0].at(initial, p), p)[0][3]
            extra["r030_acceleration_error_mps2"] = float(abs(instantaneous-model.acceleration(50, 1, 0)))
            special_pass = extra["maximum_r030_speed_error_mps"] <= 1e-6 and extra["r030_acceleration_error_mps2"] <= 1e-10
        passed = bool(max(errors) <= 1e-4 and max(refinement) <= 1e-4 and max(coarse_error) <= 1e-4
                      and monitors["maximum_utilization_squared"] <= 1+1e-12
                      and monitors["maximum_lateral_slip_power_w"] <= 1e-9
                      and monitors["maximum_power_balance_error_w"] <= 1e-7 and special_pass)
        results.append({"name": name, "outcome": "SUPPORTED", "output_nodes": len(t), "duration_s": float(t[-1]),
                        "rk4_01_vs_dop853_maximum_by_state": errors.tolist(),
                        "rk4_02_vs_dop853_maximum_by_state": coarse_error.tolist(),
                        "rk4_01_vs_005_maximum_by_state": refinement.tolist(),
                        "stage_diagnostics": monitors, "special_checks": extra, "passed": passed})
    force, linear = _force_checks(), _linear_checks()
    mirror_error = float(np.max(abs(arrays["right__rk4_01"]-arrays["left__rk4_01"]*np.array([1, -1, -1, 1, -1, -1]))))
    accepted = bool(force["passed"] and linear["passed"] and all(c["passed"] for c in results) and mirror_error <= 1e-9)
    result = {"schema_version": VERSION+"-results", "classification": "EQUATION_LEVEL_ADAPTATION",
              "input_truth": "SYNTHETIC", "parameter_truth": "GENERIC_PRIOR", "production_promotion": False,
              "research_foundation_maturity": "R1", "production_kernel_maturity": "R0",
              "decision": "ACCEPT_SCOPED_BICYCLE_FORCE_STABILITY" if accepted else "REJECT_BICYCLE_FORCE_STABILITY",
              "task_closure_eligible": accepted, "state_order": list(BicycleState.__dataclass_fields__),
              "supported_cases": sum(c["outcome"] == "SUPPORTED" for c in results),
              "abstention_challenges": sum(c["outcome"] == "ABSTAIN_SUPPORT_EXIT" for c in results),
              "state_units": STATE_UNITS, "force_checks": force, "linear_checks": linear,
              "mirror_maximum_error_si": mirror_error, "cases": results,
              "limitations": ["Synthetic dynamics and generic priors; real-car lateral parameters uncalibrated",
                              "Static axle loads, no aero/load transfer/thermal/wheel-spin dynamics",
                              "Forward-only restricted speed/slip; no low-speed or full-lap controller",
                              "Longitudinal-priority combined-slip prior; not an identified tyre model",
                              "R030 adapter checks algebra only; effective ratios do not identify absolute forces",
                              "No public cornering accuracy, uncertainty calibration or maturity promotion"]}
    return result, arrays


def _seal(payload: dict) -> dict:
    return dict(payload, content_sha256=payload_sha256(payload))


def _inventory(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): {"sha256": file_sha256(p), "bytes": p.stat().st_size}
            for p in sorted(root.rglob("*")) if p.is_file() and p != root/"manifest.json"}


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _check_seal(payload: dict) -> None:
    if payload.get("content_sha256") != payload_sha256({k: v for k, v in payload.items() if k != "content_sha256"}):
        raise ValueError("R031 content seal mismatch")


def run_bicycle_study(output: Path) -> dict:
    """Generate fresh immutable outputs; scientific failures remain recorded."""
    if output.exists():
        raise FileExistsError("R031 output must be fresh")
    sources = [Path(bicycle.__file__), Path(bicycle_audit.__file__), Path(__file__), PROTOCOL]
    hashes = {p.name: file_sha256(p) for p in sources}
    started = time.perf_counter()
    result, arrays = compute_evidence()
    if hashes != {p.name: file_sha256(p) for p in sources}:
        raise ValueError("R031 source changed during evaluation")
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    config = configuration()
    summary = _seal({"schema_version": VERSION+"-study", "commit": commit,
                     "decision": result["decision"], "task_closure_eligible": result["task_closure_eligible"],
                     "input_truth": "SYNTHETIC", "production_promotion": False, "cases": len(result["cases"]),
                     "configuration_sha256": payload_sha256(config), "results_sha256": payload_sha256(result),
                     "implementation_sha256": hashes, "runtime_seconds": time.perf_counter()-started,
                     "environment": {"python": platform.python_version(), "numpy": np.__version__,
                                     "scipy": scipy.__version__, "platform": platform.platform()}})
    output.mkdir(parents=True, exist_ok=False)
    (output/"sources").mkdir()
    for p in sources:
        (output/"sources"/p.name).write_bytes(p.read_bytes())
    write_manifest(output/"configuration.json", config)
    write_manifest(output/"results.json", result)
    np.savez_compressed(output/"trajectories.npz", **arrays)
    write_manifest(output/"summary.json", summary)
    manifest = _seal({"schema_version": VERSION+"-manifest", "summary_sha256": summary["content_sha256"], "files": _inventory(output)})
    write_manifest(output/"manifest.json", manifest)
    return summary


def load_bicycle_study(output: Path) -> tuple[dict, dict]:
    """Validate exact bytes/config/truth binding before any scientific replay."""
    manifest = _read_json(output/"manifest.json")
    _check_seal(manifest)
    if manifest.get("schema_version") != VERSION+"-manifest":
        raise ValueError("R031 manifest version mismatch")
    for name in manifest["files"]:
        path = output/name
        if ("\\" in name or ":" in name or Path(name).is_absolute() or ".." in Path(name).parts
                or path.is_symlink() or not path.resolve().is_relative_to(output.resolve())):
            raise ValueError("R031 unsafe artifact path")
    if manifest["files"] != _inventory(output):
        raise ValueError("R031 artifact inventory/hash mismatch")
    summary, result = _read_json(output/"summary.json"), _read_json(output/"results.json")
    _check_seal(summary)
    if (summary.get("schema_version") != VERSION+"-study" or manifest["summary_sha256"] != summary["content_sha256"]
            or summary["results_sha256"] != payload_sha256(result)
            or summary["configuration_sha256"] != payload_sha256(configuration())
            or _read_json(output/"configuration.json") != configuration()
            or summary["decision"] != result["decision"] or summary["task_closure_eligible"] != result["task_closure_eligible"]
            or summary["input_truth"] != "SYNTHETIC" or summary["production_promotion"] is not False):
        raise ValueError("R031 study binding/configuration/truth mismatch")
    for name, digest in summary["implementation_sha256"].items():
        if "/" in name or "\\" in name or name in (".", "..") or file_sha256(output/"sources"/name) != digest:
            raise ValueError("R031 implementation snapshot mismatch")
    return summary, result


def _numerically_equal(actual, expected, name="results") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"R031 scientific replay keys mismatch: {name}")
        for key in expected:
            _numerically_equal(actual[key], expected[key], name+"/"+key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"R031 scientific replay list mismatch: {name}")
        for i, (a, b) in enumerate(zip(actual, expected, strict=True)):
            _numerically_equal(a, b, name+"/"+str(i))
    elif isinstance(expected, float):
        if not isinstance(actual, (float, int)) or not np.isclose(actual, expected, rtol=1e-7, atol=1e-8):
            raise ValueError(f"R031 scientific replay numeric mismatch: {name}")
    elif type(actual) is not type(expected) or actual != expected:
        raise ValueError(f"R031 scientific replay value mismatch: {name}")


def verify_bicycle_study(output: Path) -> dict:
    """Recompute every equation gate/trajectory; hashes alone cannot establish acceptance."""
    summary, stored = load_bicycle_study(output)
    result, arrays = compute_evidence()
    _numerically_equal(result, stored)
    maximum = 0.
    with np.load(output/"trajectories.npz", allow_pickle=False) as saved:
        if set(saved.files) != set(arrays):
            raise ValueError("R031 scientific replay array keys mismatch")
        for key, values in arrays.items():
            if saved[key].shape != values.shape or not np.allclose(values, saved[key], rtol=1e-7, atol=1e-8):
                raise ValueError("R031 scientific replay trajectory mismatch: "+key)
            maximum = max(maximum, float(np.max(abs(values-saved[key]))))
    return {"verified": True, "summary_sha256": summary["content_sha256"], "decision": result["decision"],
            "task_closure_eligible": result["task_closure_eligible"], "maximum_reload_difference_si": maximum,
            "input_truth": "SYNTHETIC", "production_promotion": False}


def audit_bicycle_study(output: Path) -> dict:
    """Independently recompute DOP853 against all stored RK4 paths, without RK4 helpers."""
    summary, result = load_bicycle_study(output)
    maximum = np.zeros(6)
    with np.load(output/"trajectories.npz", allow_pickle=False) as saved:
        for case in frozen_cases():
            t = saved[case["name"]+"__time_s"]
            if case["name"] == "near_limit_drive":
                exit_time, exit_state = independent_support_exit(case["initial"].array(), case["time_s"], case["commands"], case["params"])
                expected_t = case["time_s"][case["time_s"] < exit_time]
                recorded = next(c for c in result["cases"] if c["name"] == case["name"])
                if (abs(recorded["independent_exit_time_s"]-exit_time) > 1e-7
                        or any(abs(r["first_rejected_stage_time_s"]-exit_time) > .02 for r in recorded["rejection_by_step"])
                        or not np.allclose(saved[case["name"]+"__boundary_state"], exit_state, rtol=1e-7, atol=1e-8)):
                    raise ValueError("R031 independent support-exit audit failed")
            else:
                expected_t = case["time_s"]
            if not np.array_equal(t, expected_t):
                raise ValueError("R031 independent saved time coverage mismatch")
            expected = independent_trajectory(case["initial"].array(), t, case["commands"][:len(t)-1], case["params"])
            for suffix in ("rk4_02", "rk4_01", "rk4_005", "dop853"):
                values = saved[case["name"]+"__"+suffix]
                if values.shape != expected.shape or not np.isfinite(values).all():
                    raise ValueError("R031 independent trajectory shape/finite mismatch")
                maximum = np.maximum(maximum, np.max(abs(expected-values), axis=0))
    if max(maximum) > 1e-4:
        raise ValueError("R031 independent DOP853 trajectory audit failed")
    return {"verified": True, "summary_sha256": summary["content_sha256"], "cases": len(frozen_cases()),
            "maximum_error_by_state": maximum.tolist(), "state_units": STATE_UNITS,
            "input_truth": "SYNTHETIC", "production_promotion": False}
