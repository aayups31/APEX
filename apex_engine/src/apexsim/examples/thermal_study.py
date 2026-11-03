"""Replay the R039 thermal model against frozen R037 vehicle trajectories."""
from dataclasses import asdict
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from apexsim.examples.recovery_study import load_recovery
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.aero_bicycle import aero_bicycle_rhs
from apexsim.research.bicycle import BicycleControl, BicycleState
from apexsim.research.evidence import finish_run, read_json
from apexsim.research.transparent_driver import AERO, CAR
from apexsim.research.tyre_thermal import ThermalParameters, ThermalState, heat_step

ROAD_K, AIR_K = 308.15, 298.15
VERSION = "apex-tyre-thermal-v1"


def replay_case(times: np.ndarray, states: np.ndarray, controls: np.ndarray) -> tuple[dict, np.ndarray]:
    """Use held inputs and an independent adaptive integration of the two ODEs."""
    if (times.ndim != 1 or len(times) < 2 or states.shape != (len(times), 6)
            or controls.shape != (len(times)-1, 4) or not np.isfinite(times).all()
            or np.any(np.diff(times) <= 0)):
        raise ValueError("Invalid thermal replay intervals")
    p = ThermalParameters()
    history = np.empty((len(times), 2, 2))
    history[0] = reference = np.full((2, 2), 333.15)
    maximum_balance = maximum_difference = 0.0
    energies = np.zeros((2, 4))
    for i, duration in enumerate(np.diff(times)):
        state = BicycleState.from_array(states[i])
        control = BicycleControl(*controls[i])
        _, diagnostic = aero_bicycle_rhs(state, control, CAR, AERO)
        wrench = diagnostic.wrench
        axle_loads = np.array([wrench.front.normal_n, wrench.rear.normal_n])
        tread_power = -np.array([wrench.front.fy_n * wrench.front_wheel_vy_mps,
                                 wrench.rear.fy_n * wrench.rear_wheel_vy_mps])
        carcass_power = .30 * control.resistance_n * state.vx_mps * axle_loads / axle_loads.sum()
        if np.min(tread_power) < -1e-9:
            raise ValueError("Simulated lateral slip generated positive mechanical work")
        tread_power = np.maximum(tread_power, 0.)
        for axle in range(2):
            step = heat_step(ThermalState(*history[i, axle]), float(duration),
                             tread_w=tread_power[axle], carcass_w=carcass_power[axle], road_k=ROAD_K, air_k=AIR_K)
            history[i+1, axle] = step.state.tread_k, step.state.carcass_k
            maximum_balance = max(maximum_balance, abs(step.balance_error_j))
            energies[axle] += step.source_j, step.road_j, step.air_j, step.stored_j

        def rhs(_time, vector, tread_power=tread_power, carcass_power=carcass_power):
            tread, carcass = vector.reshape(2, 2).T
            coupling = p.coupling_w_k * (tread - carcass)
            return np.column_stack((
                (tread_power + p.road_w_k * (ROAD_K-tread) - coupling) / p.tread_capacity_j_k,
                (carcass_power + p.air_w_k * (AIR_K-carcass) + coupling) / p.carcass_capacity_j_k,
            )).ravel()

        solution = solve_ivp(rhs, (0., duration), reference.ravel(), rtol=1e-11, atol=1e-11, method="DOP853")
        if not solution.success:
            raise ValueError("Independent thermal integration failed")
        reference = solution.y[:, -1].reshape(2, 2)
        maximum_difference = max(maximum_difference, float(np.max(abs(reference-history[i+1]))))
    return {"intervals": len(controls), "maximum_balance_error_j": maximum_balance,
            "maximum_independent_difference_k": maximum_difference,
            "minimum_k": history.min(axis=0).tolist(), "maximum_k": history.max(axis=0).tolist(),
            "energy_j_source_road_air_stored": energies.tolist(),
            "passed": maximum_balance <= 1e-6 and maximum_difference <= 1e-6}, history


def run_thermal_study(recovery: Path, receipt_path: Path, output: Path) -> dict:
    summary, result = load_recovery(recovery)
    receipt = read_json(receipt_path)
    if (not summary["task_closure_eligible"] or receipt.get("verified") is not True
            or receipt.get("task_closure_eligible") is not True
            or receipt["summary_sha256"] != summary["content_sha256"]
            or receipt["maximum_replay_difference"] != 0):
        raise ValueError("R039 requires an accepted and exactly replayed R037 parent")
    output.mkdir(parents=True, exist_ok=False)
    catalog = [c for c in result["cases"] if c["actor"] == "learned"
               and c["scenario"] == "nominal" and c["max_step_s"] == .02]
    if len(catalog) != 4 or any(not c["passed"] for c in catalog):
        raise ValueError("R039 requires all four frozen five-lap cases")
    rows, histories = [], {}
    with np.load(recovery/"trajectories.npz", allow_pickle=False) as arrays:
        for case in catalog:
            key = case["case_id"]
            row, histories[key] = replay_case(*(arrays[key+"__"+k] for k in ("time_s", "states", "controls")))
            rows.append({"case_id": key, **row})
    np.savez_compressed(output/"thermal_trajectories.npz", **histories)
    write_manifest(output/"results.json", {"cases": rows})
    from apexsim.research import tyre_thermal

    return finish_run(output, VERSION, {"schema_version": VERSION, "recovery_sha256": summary["content_sha256"],
                      "replay_receipt_sha256": file_sha256(receipt_path),
                      "implementation_sha256": {p.name: file_sha256(p) for p in (Path(__file__), Path(tyre_thermal.__file__))},
                      "parameter_truth": "DECLARED_EFFECTIVE_AXLE_PRIORS", "parameters": asdict(ThermalParameters()),
                      "road_k": ROAD_K, "air_k": AIR_K, "passed": all(row["passed"] for row in rows),
                      "production_promotion": False})
