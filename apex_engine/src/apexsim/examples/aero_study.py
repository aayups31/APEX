"""R032 fixed synthetic aero/load-transfer and identifiability study."""
from __future__ import annotations

import platform
import subprocess
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import scipy

from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import aero_audit, aero_bicycle, aero_identifiability, evidence
from apexsim.research.aero_audit import independent_loaded_path, independent_loaded_rhs
from apexsim.research.aero_bicycle import (
    AeroParameters,
    aero_bicycle_rhs,
    integrate_aero_bicycle,
    solve_axle_loads,
)
from apexsim.research.aero_identifiability import identifiability_report
from apexsim.research.bicycle import BicycleControl, BicycleParameters, BicycleState, integrate_bicycle
from apexsim.research.evidence import check_seal, compare_numeric, finish_run, read_json, verify_inventory

VERSION = "apex-aero-load-transfer-v1"
PROTOCOL = Path(__file__).resolve().parents[4]/"research/protocols/AERO_LOAD_TRANSFER.md"


def cases() -> list[dict]:
    result = []
    for name, command in (("coast", BicycleControl()), ("drive", BicycleControl(rear_fx_request_n=3000)),
                          ("brake", BicycleControl(front_fx_request_n=-2000, rear_fx_request_n=-1000)),
                          ("left", BicycleControl(.02)), ("right", BicycleControl(-.02)),
                          ("combined", BicycleControl(.03, -1000, -500)), ("pulse", None)):
        t = np.linspace(0, 2, 21)
        commands = [BicycleControl(.03 if i < 5 else -.03 if i < 10 else 0) for i in range(20)] if command is None else [command]*20
        result.append({"name": name, "time_s": t, "commands": commands})
    return result


def configuration() -> dict:
    return {"schema_version": VERSION+"-config", "parameters": asdict(BicycleParameters()), "aero": asdict(AeroParameters()),
            "initial": asdict(BicycleState()), "input_truth": "SYNTHETIC", "parameter_truth": "GENERIC_PRIOR",
            "cases": [{"name": c["name"], "time_s": c["time_s"].tolist(), "commands": [asdict(u) for u in c["commands"]]} for c in cases()]}


def compute_evidence() -> tuple[dict, dict[str, np.ndarray]]:
    p, aero, initial = BicycleParameters(), AeroParameters(), BicycleState()
    arrays, rows = {}, []
    for case in cases():
        name, t, commands = case["name"], case["time_s"], case["commands"]
        paths = [integrate_aero_bicycle(initial, t, commands, p, aero, max_step_s=h) for h in (.02, .01, .005)]
        reference = independent_loaded_path(initial.array(), t, commands, p, aero)
        arrays[name+"__time_s"] = t
        for suffix, values in zip(("rk4_02", "rk4_01", "rk4_005", "dop853"), [s.states for s in paths]+[reference], strict=True):
            arrays[name+"__"+suffix] = values
        errors = [np.max(abs(path.states-reference), axis=0).tolist() for path in paths]
        fine = np.max(abs(paths[1].states-paths[2].states), axis=0)
        d = paths[1].integration_checks
        passed = bool(max(max(e) for e in errors) <= 1e-4 and max(fine) <= 1e-4
                      and d["maximum_pitch_residual_nm"] <= 1e-6 and d["maximum_root_residual_n"] <= 1e-7
                      and d["maximum_utilization_squared"] <= 1+1e-12 and d["maximum_power_balance_error_w"] <= 1e-6
                      and d["maximum_positive_slip_power_w"] <= 1e-9)
        rows.append({"name": name, "maximum_dop853_error_by_step_and_state": errors,
                     "maximum_fine_refinement_by_state": fine.tolist(), "diagnostics": d, "passed": passed})
    hand = solve_axle_loads(BicycleState(vx_mps=50), BicycleControl(front_fx_request_n=900, rear_fx_request_n=1800), p, aero)
    hand_error = float(max(abs(hand.front.normal_n-6747.1875), abs(hand.rear.normal_n-6675.5625), abs(hand.downforce_n-4593.75), abs(hand.drag_n-1684.375)))
    grid, rejected, maximum_load_error, maximum_rhs_error = [], [], 0., 0.
    for v in (10, 40, 90):
        for steering in (-.1, 0, .1):
            for fx in (-20000, -3000, 0, 3000, 20000):
                state, control = BicycleState(vx_mps=v, vy_mps=.2, yaw_rate_radps=.02), BicycleControl(steering, fx, fx)
                try:
                    actual, d = aero_bicycle_rhs(state, control, p, aero)
                except ValueError as exc:
                    if "uniqueness unsupported across front saturation" not in str(exc):
                        raise
                    rejected.append({"speed_mps": v, "steering_rad": steering, "each_axle_fx_n": fx, "reason": "UNPROVEN_UNIQUENESS_AT_FRONT_SATURATION"})
                    continue
                reference, loads = independent_loaded_rhs(state.array(), control, p, aero)
                maximum_load_error = max(maximum_load_error, abs(loads[0]-d.loads.front.normal_n), abs(loads[1]-d.loads.rear.normal_n))
                maximum_rhs_error = max(maximum_rhs_error, float(max(abs(actual-reference))))
                grid.append({"speed_mps": v, "steering_rad": steering, "each_axle_fx_n": fx,
                             "front_load_n": d.loads.front.normal_n, "rear_load_n": d.loads.rear.normal_n,
                             "pitch_residual_nm": d.loads.pitch_residual_nm})
    zeros = AeroParameters(drag_area_m2=0, downforce_area_m2=0, cg_height_m=0)
    t, command = cases()[3]["time_s"], BicycleControl(.02)
    zero = integrate_aero_bicycle(initial, t, [command]*20, p, zeros)
    old = integrate_bicycle(initial, t, [command]*20, p)
    zero_difference = float(np.max(abs(zero.states-old.states)))
    sensitivity = []
    nominal = integrate_aero_bicycle(initial, t, [BicycleControl(.03, -1000, -500)]*20, p, aero)
    for field in ("drag_area_m2", "downforce_area_m2", "front_downforce_fraction", "cg_height_m"):
        for sign in (-1, 1):
            value = getattr(aero, field)+(sign*.1 if field == "front_downforce_fraction" else sign*.2*getattr(aero, field))
            varied = replace(aero, **{field: value})
            path = integrate_aero_bicycle(initial, t, [BicycleControl(.03, -1000, -500)]*20, p, varied)
            load = solve_axle_loads(initial, BicycleControl(.03, -1000, -500), p, varied)
            sensitivity.append({"parameter": field, "value": value, "terminal_state_difference": (path.states[-1]-nominal.states[-1]).tolist(),
                                "initial_front_load_n": load.front.normal_n, "initial_rear_load_n": load.rear.normal_n,
                                "truth": "SYNTHETIC_PRIOR_SENSITIVITY"})
    ident = identifiability_report()
    passed = bool(all(r["passed"] for r in rows) and ident["passed"] and hand_error <= 1e-8
                  and maximum_load_error <= 1e-7 and maximum_rhs_error <= 1e-7 and zero_difference <= 1e-8)
    return {"schema_version": VERSION+"-results", "decision": "ACCEPT_SCOPED_AERO_LOAD_TRANSFER" if passed else "REJECT_AERO_LOAD_TRANSFER",
            "task_closure_eligible": passed, "input_truth": "SYNTHETIC", "production_promotion": False,
            "cases": rows, "hand_error_n": hand_error, "zero_aero_height_r031_maximum_difference": zero_difference,
            "force_grid": {"attempted": 45, "supported": len(grid), "abstained": len(rejected), "supported_points": grid,
                           "rejections": rejected, "maximum_independent_load_error_n": maximum_load_error,
                           "maximum_independent_rhs_error": maximum_rhs_error},
            "sensitivity": sensitivity, "identifiability": ident,
            "limitations": ["Generic priors and synthetic force-sensor oracle; real vehicle parameters not identified",
                            "Static pitch equilibrium and fixed axle stiffness; no lateral load transfer, suspension or ride-height map",
                            "Drag at CoG; no independent torque/fuel/ERS calibration or production promotion"]}, arrays


def run_aero_study(output: Path) -> dict:
    if output.exists():
        raise FileExistsError("R032 output must be fresh")
    files = [Path(__file__), Path(aero_bicycle.__file__), Path(aero_audit.__file__), Path(aero_identifiability.__file__), Path(evidence.__file__), PROTOCOL]
    hashes = {p.name: file_sha256(p) for p in files}
    started = time.perf_counter()
    result, arrays = compute_evidence()
    config = configuration()
    if hashes != {p.name: file_sha256(p) for p in files}:
        raise ValueError("R032 sources changed during evaluation")
    output.mkdir(parents=True, exist_ok=False)
    (output/"sources").mkdir()
    for p in files:
        (output/"sources"/p.name).write_bytes(p.read_bytes())
    write_manifest(output/"configuration.json", config)
    write_manifest(output/"results.json", result)
    np.savez_compressed(output/"trajectories.npz", **arrays)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], text=True, capture_output=True, check=True).stdout.strip()
    return finish_run(output, VERSION, {"schema_version": VERSION+"-study", "commit": commit, "input_truth": "SYNTHETIC",
                                       "decision": result["decision"], "task_closure_eligible": result["task_closure_eligible"], "production_promotion": False,
                                       "results_sha256": payload_sha256(result), "configuration_sha256": payload_sha256(config),
                                       "implementation_sha256": hashes, "runtime_seconds": time.perf_counter()-started,
                                       "environment": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "platform": platform.platform()}})


def load_aero_study(root: Path) -> tuple[dict, dict]:
    manifest = verify_inventory(root, VERSION)
    summary, result = read_json(root/"summary.json"), read_json(root/"results.json")
    check_seal(summary)
    if (summary["schema_version"] != VERSION+"-study" or manifest["summary_sha256"] != summary["content_sha256"]
            or payload_sha256(result) != summary["results_sha256"] or read_json(root/"configuration.json") != configuration()
            or summary["configuration_sha256"] != payload_sha256(configuration()) or summary["input_truth"] != "SYNTHETIC"
            or summary["production_promotion"] is not False or summary["decision"] != result["decision"]
            or summary["task_closure_eligible"] != result["task_closure_eligible"]):
        raise ValueError("R032 stored configuration/truth/result binding mismatch")
    for name, digest in summary["implementation_sha256"].items():
        if "/" in name or "\\" in name or ":" in name or name in (".", "..") or file_sha256(root/"sources"/name) != digest:
            raise ValueError("R032 source snapshot mismatch")
    return summary, result


def verify_aero_study(root: Path) -> dict:
    summary, stored = load_aero_study(root)
    result, arrays = compute_evidence()
    compare_numeric(result, stored)
    maximum = 0.
    with np.load(root/"trajectories.npz", allow_pickle=False) as saved:
        if set(saved.files) != set(arrays):
            raise ValueError("R032 trajectory inventory mismatch")
        for key, values in arrays.items():
            if values.shape != saved[key].shape or not np.allclose(values, saved[key], atol=1e-8, rtol=1e-7):
                raise ValueError("R032 scientific trajectory replay mismatch")
            maximum = max(maximum, float(max(abs(values-saved[key]).ravel())))
    return {"verified": True, "summary_sha256": summary["content_sha256"], "decision": result["decision"], "maximum_reload_difference": maximum}


def audit_aero_study(root: Path) -> dict:
    summary, _ = load_aero_study(root)
    maximum = np.zeros(6)
    with np.load(root/"trajectories.npz", allow_pickle=False) as saved:
        for case in cases():
            name, t = case["name"], case["time_s"]
            if not np.array_equal(t, saved[name+"__time_s"]):
                raise ValueError("R032 independent time coverage mismatch")
            path = independent_loaded_path(BicycleState().array(), t, case["commands"], BicycleParameters(), AeroParameters())
            for suffix in ("rk4_02", "rk4_01", "rk4_005", "dop853"):
                values = saved[name+"__"+suffix]
                if values.shape != path.shape or not np.isfinite(values).all():
                    raise ValueError("R032 independent trajectory shape/finite mismatch")
                maximum = np.maximum(maximum, np.max(abs(values-path), axis=0))
    if max(maximum) > 1e-4:
        raise ValueError("R032 independent DOP853 audit failed")
    return {"verified": True, "summary_sha256": summary["content_sha256"], "cases": len(cases()), "maximum_error_by_state": maximum.tolist(), "input_truth": "SYNTHETIC"}
