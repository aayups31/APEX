"""R035 immutable conditional-driver calibration and held-out lap evaluation."""
from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from apexsim.examples.open_loop_study import RECORDED_SEAL, load_study
from apexsim.examples.recorded_replay import guard_inputs, load_recorded_replay, verify_recorded_replay
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research.evidence import check_seal, compare_numeric, finish_run, read_json, verify_inventory
from apexsim.research.longitudinal_data import EVENT_ROLES
from apexsim.research.reference_geometry import GeometryConfig, ReferenceCurve
from apexsim.research.transparent_driver import (
    AERO,
    CAR,
    PACE_CANDIDATES,
    DriverMap,
    simulate_driver,
    speed_profile,
)

VERSION = "apex-transparent-driver-v1"
PROTOCOL = Path(__file__).resolve().parents[4]/"research/protocols/TRANSPARENT_DRIVER.md"


def source_files():
    from apexsim.research import aero_audit, aero_bicycle, bicycle, driver_audit, transparent_driver

    return [Path(__file__), *(Path(m.__file__) for m in (transparent_driver, driver_audit, aero_bicycle, bicycle, aero_audit)), PROTOCOL]


def maps_from_source(recorded: Path) -> dict[str, DriverMap]:
    guard_inputs(recorded)
    base = recorded/"longitudinal/geometry"
    geometry = read_json(base/"summary.json")
    maps = {}
    for track in ("bahrain", "monza"):
        with np.load(base/(track+"_geometry_predictions.npz"), allow_pickle=False) as arrays:
            curve = ReferenceCurve(arrays["coefficients"], GeometryConfig(**geometry["cases"][track]["selected_config"]), track)
        maps[track] = DriverMap.from_curve(curve)
    return maps


def calibration_targets(recorded: Path) -> tuple[list[dict], dict]:
    """Read train/validation labels only; native speed vs backward registered position."""
    header = guard_inputs(recorded)
    rows, targets = [], {}
    for track in ("bahrain", "monza"):
        base = recorded/"longitudinal/geometry"
        with (np.load(base/(track+"_lap_inputs.npz"), allow_pickle=False) as native,
              np.load(base/(track+"_geometry_predictions.npz"), allow_pickle=False) as geometry):
            for lap in header["laps"]:
                if lap["track_id"] != track or EVENT_ROLES[lap["event_id"]] == "test":
                    continue
                key = lap["lap_id"]
                parents = native[key+"_native_parents"]
                stations, distances = geometry[key+"_station_m"], geometry[key+"_distance_m"]
                lookup = {int(a): float(s) for (a, b), s, d in zip(parents, stations, distances, strict=True) if a == b and d <= 15}
                frame = pd.read_parquet(recorded/"frames"/(key+".parquet"))
                selected = frame.joint_observed_ready & frame.position_source_row.isin(lookup)
                subset = frame.loc[selected]
                station = np.array([lookup[int(v)] for v in subset.position_source_row])
                speed = subset.speed_mps.to_numpy(float)
                if len(speed) < 20:
                    raise ValueError("R035 insufficient frozen calibration label support")
                targets[key+"_station_m"], targets[key+"_speed_mps"] = station, speed
                rows.append({"lap_id": key, "event_id": lap["event_id"], "driver_id": lap["driver_id"], "track_id": track,
                             "role": EVENT_ROLES[lap["event_id"]], "native_car_rows": len(frame), "matched_rows": len(speed),
                             "speed_truth": "FASTF1_PARSED_SOURCE", "station_truth": "RECONSTRUCTED_OFFLINE_MAP_BACKWARD_NATIVE_POSITION"})
    return rows, targets


def calibration_scores(maps, rows, targets):
    if not rows or any(r["event_id"] not in EVENT_ROLES or EVENT_ROLES[r["event_id"]] not in ("train", "validation")
                       or r["role"] != EVENT_ROLES[r["event_id"]] for r in rows):
        raise ValueError("R035 calibration forbids test labels or changed source roles")
    candidates = []
    for fraction, maximum in PACE_CANDIDATES:
        profiles = {track: speed_profile(m, fraction, maximum) for track, m in maps.items()}
        per_lap = []
        for row in rows:
            key, track = row["lap_id"], row["track_id"]
            predicted = maps[track].interpolate(profiles[track], targets[key+"_station_m"])
            error = predicted-targets[key+"_speed_mps"]
            per_lap.append({**row, "mse_m2ps2": float(np.mean(error**2)), "mae_mps": float(np.mean(abs(error)))})
        aggregate = {}
        for role in ("train", "validation"):
            events = []
            for event in sorted({r["event_id"] for r in per_lap if r["role"] == role}):
                drivers = []
                for driver in ("4", "44"):
                    values = [r["mse_m2ps2"] for r in per_lap if r["event_id"] == event and r["driver_id"] == driver]
                    if not values:
                        raise ValueError("R035 missing calibration event/driver")
                    drivers.append(float(np.mean(values)))
                events.append(float(np.mean(drivers)))
            aggregate[role+"_mse_m2ps2"] = float(np.mean(events))
        candidates.append({"fraction": fraction, "maximum_mps": maximum, **aggregate, "per_lap": per_lap})
    choice = min(candidates, key=lambda c: (c["validation_mse_m2ps2"], c["maximum_mps"], c["fraction"]))
    return {"candidates": candidates, "selected": {"fraction": choice["fraction"], "maximum_mps": choice["maximum_mps"]},
            "selection_truth": "CONDITIONAL_PACE_CALIBRATION; GENERIC_VEHICLE_CONFOUNDED", "test_outcomes_used": False,
            "label_laps": len(rows), "label_rows": sum(r["matched_rows"] for r in rows)}


def freeze_driver_calibration(open_loop: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("R035 calibration output must be fresh")
    if output.resolve().is_relative_to(open_loop.resolve()):
        raise ValueError("R035 output must be outside immutable input")
    previous, _ = load_study(open_loop)
    source, _ = load_recorded_replay(open_loop/"recorded")
    if not previous["task_closure_eligible"] or source["content_sha256"] != RECORDED_SEAL:
        raise ValueError("R035 requires accepted public R034/R033 evidence")
    verify_recorded_replay(open_loop/"recorded")
    output.mkdir(parents=True)
    shutil.copytree(open_loop/"recorded", output/"recorded")
    write_manifest(output/"r034_summary.json", previous)
    paths = source_files()
    hashes = {p.name: file_sha256(p) for p in paths}
    maps = maps_from_source(output/"recorded")
    rows, targets = calibration_targets(output/"recorded")
    result = calibration_scores(maps, rows, targets)
    header = guard_inputs(output/"recorded")
    catalog = []
    for event in ("F1_2024_R01", "F1_2024_R16"):
        for driver in ("4", "44"):
            selected = sorted([lap for lap in header["laps"] if lap["event_id"] == event and lap["driver_id"] == driver], key=lambda lap: lap["lap_number"])[:2]
            if len(selected) != 2:
                raise ValueError("R035 incomplete preregistered lap catalog")
            catalog.extend(selected)
    write_manifest(output/"calibration.json", result)
    write_manifest(output/"target_catalog.json", rows)
    write_manifest(output/"lap_catalog.json", catalog)
    np.savez_compressed(output/"targets.npz", **targets)
    arrays = {}
    for track, m in maps.items():
        for name in ("length_m", "xy", "tangent", "curvature"):
            arrays[track+"_"+name] = np.asarray(getattr(m, name))
    np.savez_compressed(output/"maps.npz", **arrays)
    if hashes != {p.name: file_sha256(p) for p in paths}:
        raise ValueError("R035 implementation changed during calibration")
    (output/"sources").mkdir()
    for path in paths:
        shutil.copyfile(path, output/"sources"/path.name)
    return finish_run(output, VERSION+"-calibration", {"schema_version": VERSION+"-calibration", "profile": "research",
                                                      "selected": result["selected"], "calibration_sha256": payload_sha256(result),
                                                      "recorded_sha256": source["content_sha256"], "r034_sha256": previous["content_sha256"],
                                                      "implementation_sha256": hashes, "test_outcomes_used": False,
                                                      "vehicle_parameters": asdict(CAR), "aero_parameters": asdict(AERO), "production_promotion": False,
                                                      "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip(),
                                                      "environment": {"python": platform.python_version(), "numpy": np.__version__}})


def load_calibration(root: Path):
    header = guard_inputs(root/"recorded")
    manifest = verify_inventory(root, VERSION+"-calibration")
    summary, calibration = read_json(root/"summary.json"), read_json(root/"calibration.json")
    check_seal(summary)
    source, _ = load_recorded_replay(root/"recorded")
    prior = read_json(root/"r034_summary.json")
    check_seal(prior)
    if (manifest["summary_sha256"] != summary["content_sha256"] or summary["schema_version"] != VERSION+"-calibration"
            or summary["calibration_sha256"] != payload_sha256(calibration) or summary["selected"] != calibration["selected"]
            or summary["recorded_sha256"] != source["content_sha256"] or source["content_sha256"] != RECORDED_SEAL
            or summary["r034_sha256"] != prior["content_sha256"] or not prior["task_closure_eligible"]
            or summary["test_outcomes_used"] is not False or calibration["test_outcomes_used"] is not False
            or summary["production_promotion"] is not False or summary["vehicle_parameters"] != asdict(CAR) or summary["aero_parameters"] != asdict(AERO)):
        raise ValueError("R035 calibration source/selection/truth binding mismatch")
    expected = []
    for event in ("F1_2024_R01", "F1_2024_R16"):
        for driver in ("4", "44"):
            expected.extend(sorted([lap for lap in header["laps"] if lap["event_id"] == event and lap["driver_id"] == driver], key=lambda lap: lap["lap_number"])[:2])
    if read_json(root/"lap_catalog.json") != expected:
        raise ValueError("R035 frozen first-two-lap catalog changed")
    maps = {}
    with np.load(root/"maps.npz", allow_pickle=False) as arrays:
        for track in ("bahrain", "monza"):
            maps[track] = DriverMap(float(arrays[track+"_length_m"]), *(arrays[track+"_"+k] for k in ("xy", "tangent", "curvature")))
    for name, digest in summary["implementation_sha256"].items():
        if Path(name).name != name or ":" in name or "\\" in name or file_sha256(root/"sources"/name) != digest:
            raise ValueError("R035 implementation snapshot mismatch")
    return summary, calibration, maps


def verify_driver_calibration(root: Path):
    summary, calibration, maps = load_calibration(root)
    regenerated = maps_from_source(root/"recorded")
    for track, m in maps.items():
        for name in ("length_m", "xy", "tangent", "curvature"):
            compare_numeric(np.asarray(getattr(m, name)).tolist(), np.asarray(getattr(regenerated[track], name)).tolist())
    rows, targets = calibration_targets(root/"recorded")
    compare_numeric(rows, read_json(root/"target_catalog.json"))
    with np.load(root/"targets.npz", allow_pickle=False) as stored:
        if set(stored.files) != set(targets):
            raise ValueError("R035 target catalog mismatch")
        for key, value in targets.items():
            compare_numeric(stored[key].tolist(), value.tolist())
    compare_numeric(calibration_scores(regenerated, rows, targets), calibration)
    return {"verified": True, "summary_sha256": summary["content_sha256"], "selected": calibration["selected"], "test_outcomes_used": False}


def refinement_metrics(track: DriverMap, nominal: dict, refined: dict, nominal_result: dict, refined_result: dict):
    if not nominal_result["completed"] or not refined_result["completed"]:
        return {"passed": False, "reason": "INCOMPLETE_NOMINAL_OR_REFINED_LAP"}
    station = np.linspace(0, track.length_m, 2001)
    ns, rs = nominal["station_m"], refined["station_m"]
    xy = [np.column_stack([np.interp(station, s, a["states"][:, i]) for i in (0, 1)]) for s, a in ((ns, nominal), (rs, refined))]
    speeds = [np.interp(station, s, np.hypot(a["states"][:, 3], a["states"][:, 4])) for s, a in ((ns, nominal), (rs, refined))]
    position = float(np.max(np.linalg.norm(xy[0]-xy[1], axis=1)))
    speed = float(np.max(abs(speeds[0]-speeds[1])))
    elapsed = abs(nominal_result["completion_time_s"]-refined_result["completion_time_s"])
    return {"passed": bool(position <= .5 and speed <= .5 and elapsed <= .2), "maximum_common_station_position_difference_m": position,
            "maximum_common_station_speed_difference_mps": speed, "completion_time_difference_s": elapsed}


def compute_rollouts(calibration: Path, progress=None):
    summary, choice, maps = load_calibration(calibration)
    pace = choice["selected"]["fraction"], choice["selected"]["maximum_mps"]
    catalog = read_json(calibration/"lap_catalog.json")
    results, arrays, refinements = [], {}, []
    for lap in catalog:
        frame = pd.read_parquet(calibration/"recorded/frames"/(lap["lap_id"]+".parquet"))
        initial = float(frame.speed_mps.iloc[0])
        variants = [("feedback", .02)]
        if EVENT_ROLES[lap["event_id"]] == "test":
            variants.extend([("pure_pursuit", .02), ("feedback", .01)])
        for mode, step in variants:
            key = lap["lap_id"]+"_"+mode+"_"+str(step)
            if progress:
                progress("Running "+key)
            result, trajectory = simulate_driver(maps[lap["track_id"]], pace, initial, mode=mode, max_step=step)
            result.update(case_id=key, lap_id=lap["lap_id"], event_id=lap["event_id"], driver_id=lap["driver_id"],
                          role=EVENT_ROLES[lap["event_id"]], track_id=lap["track_id"], max_step_s=step, initial_speed_mps=initial,
                          source_lap_time_s=lap["lap_end_s"]-lap["lap_start_s"],
                          source_time_difference_s=None if not result["completed"] else result["completion_time_s"]-(lap["lap_end_s"]-lap["lap_start_s"]))
            results.append(result)
            arrays.update({key+"__"+name: value for name, value in trajectory.items()})
            if progress:
                progress(str({k: result[k] for k in ("case_id", "completed", "completion_time_s", "maximum_lateral_error_m", "failure")}))
            if step == .01:
                nominal_key = lap["lap_id"]+"_feedback_0.02"
                nominal_result = next(r for r in results if r["case_id"] == nominal_key)
                nominal = {k: arrays[nominal_key+"__"+k] for k in trajectory}
                refinements.append({"lap_id": lap["lap_id"], **refinement_metrics(maps[lap["track_id"]], nominal, trajectory, nominal_result, result)})
    nominal = [r for r in results if r["role"] == "test" and r["mode"] == "feedback" and r["max_step_s"] == .02]
    gate = len(nominal) == 4 and all(r["passed"] for r in nominal) and len(refinements) == 4 and all(r["passed"] for r in refinements)
    return {"cases": results, "refinements": refinements, "nominal_and_refinement_gate_passed": gate,
            "calibration_sha256": summary["content_sha256"], "selected": choice["selected"], "production_promotion": False,
            "conditional_research_only": True, "complete_measured_car_replay": False}, arrays


def run_driver_study(calibration: Path, output: Path, progress=None):
    if output.exists():
        raise FileExistsError("R035 study output must be fresh")
    if output.resolve().is_relative_to(calibration.resolve()):
        raise ValueError("R035 output must be outside calibration")
    verify_driver_calibration(calibration)
    frozen, _, _ = load_calibration(calibration)
    if frozen["implementation_sha256"] != {p.name: file_sha256(p) for p in source_files()}:
        raise ValueError("R035 controller implementation changed after calibration freeze; explicitly refreeze before evaluation")
    output.mkdir(parents=True)
    shutil.copytree(calibration, output/"calibration")
    paths = source_files()
    hashes = {p.name: file_sha256(p) for p in paths}
    result, arrays = compute_rollouts(output/"calibration", progress)
    np.savez_compressed(output/"trajectories.npz", **arrays)
    from apexsim.research.driver_audit import audit_arrays

    audit = audit_arrays(result, arrays, progress)
    result["independent_audit"] = audit
    passed = result["nominal_and_refinement_gate_passed"] and audit["passed"]
    result.update(task_closure_eligible=passed, decision="ACCEPT_CONDITIONAL_RESEARCH_DRIVER" if passed else "REJECT_CONDITIONAL_RESEARCH_DRIVER")
    write_manifest(output/"results.json", result)
    if hashes != {p.name: file_sha256(p) for p in paths}:
        raise ValueError("R035 implementation changed during evaluation")
    (output/"sources").mkdir()
    for path in paths:
        shutil.copyfile(path, output/"sources"/path.name)
    return finish_run(output, VERSION, {"schema_version": VERSION, "decision": result["decision"], "task_closure_eligible": passed,
                                       "results_sha256": payload_sha256(result), "calibration_sha256": result["calibration_sha256"],
                                       "implementation_sha256": hashes, "production_promotion": False, "conditional_research_only": True,
                                       "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()})


def load_driver_study(root: Path):
    calibration, _, _ = load_calibration(root/"calibration")
    manifest = verify_inventory(root, VERSION)
    summary, result = read_json(root/"summary.json"), read_json(root/"results.json")
    check_seal(summary)
    if (summary["schema_version"] != VERSION or manifest["summary_sha256"] != summary["content_sha256"]
            or summary["results_sha256"] != payload_sha256(result) or summary["calibration_sha256"] != calibration["content_sha256"]
            or result["calibration_sha256"] != calibration["content_sha256"]
            or any(summary[k] != result[k] for k in ("decision", "task_closure_eligible", "production_promotion", "conditional_research_only"))
            or result["production_promotion"] is not False or result["conditional_research_only"] is not True):
        raise ValueError("R035 stored result/source/truth binding mismatch")
    for name, digest in summary["implementation_sha256"].items():
        if Path(name).name != name or ":" in name or "\\" in name or file_sha256(root/"sources"/name) != digest:
            raise ValueError("R035 implementation snapshot mismatch")
    return summary, result


def verify_driver_study(root: Path, progress=None):
    summary, stored = load_driver_study(root)
    verify_driver_calibration(root/"calibration")
    result, arrays = compute_rollouts(root/"calibration", progress)
    for name, value in result.items():
        compare_numeric(stored[name], value, name)
    with np.load(root/"trajectories.npz", allow_pickle=False) as saved:
        if set(saved.files) != set(arrays):
            raise ValueError("R035 trajectory catalog mismatch")
        for key, value in arrays.items():
            if saved[key].shape != value.shape or not np.allclose(saved[key], value, atol=1e-8, rtol=1e-7):
                raise ValueError("R035 scientific trajectory replay mismatch: "+key)
    from apexsim.research.driver_audit import audit_arrays

    audit = audit_arrays(result, arrays, progress)
    compare_numeric(audit, stored["independent_audit"])
    passed = result["nominal_and_refinement_gate_passed"] and audit["passed"]
    if stored["task_closure_eligible"] != passed or stored["decision"] != ("ACCEPT_CONDITIONAL_RESEARCH_DRIVER" if passed else "REJECT_CONDITIONAL_RESEARCH_DRIVER"):
        raise ValueError("R035 false completion")
    return {"verified": True, "summary_sha256": summary["content_sha256"], "task_closure_eligible": passed,
            "cases": len(result["cases"]), "independent_audit": audit}
