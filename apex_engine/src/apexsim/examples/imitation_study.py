"""R036 source-bound event splits, expert selection, BC and train-only aggregation."""
from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.examples.driver_study import load_calibration, load_driver_study, verify_driver_calibration
from apexsim.examples.recorded_replay import guard_inputs
from apexsim.provenance import RUN_ID_PATTERN, file_sha256, payload_sha256, write_manifest
from apexsim.research.evidence import check_seal, finish_run, read_json, verify_inventory
from apexsim.research.imitation_driver import (
    ALPHAS,
    LEADS,
    expert_residual,
    fit_policy,
    rollout_policy,
)
from apexsim.research.longitudinal_data import EVENT_ROLES, EVENT_TRACKS
from apexsim.research.reference_geometry import GeometryConfig, ReferenceCurve
from apexsim.research.transparent_driver import DriverMap

VERSION = "apex-imitation-driver-v1"
PARENT_SEAL = "58a8e7a318e12c0db80a9c70c2dfffb6fd5818534a15fa657a8e33d6b0b49ae0"
CALIBRATION_SEAL = "2dc610c27b9219caf53759c0d8f1211a8b5d492b82758c04743997e099059b1e"
PROTOCOL = Path(__file__).resolve().parents[4]/"research/protocols/IMITATION_DRIVER.md"


def implementation_files() -> list[Path]:
    from apexsim.research import imitation_audit, imitation_driver

    return [Path(__file__), Path(imitation_driver.__file__), Path(imitation_audit.__file__), PROTOCOL]


def commit_id() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()


def parent_catalog(parent: Path) -> list[dict]:
    header = guard_inputs(parent/"calibration/recorded")
    cases = []
    for event in EVENT_ROLES:
        for driver in ("4", "44"):
            selected = sorted([r for r in header["laps"] if r["event_id"] == event and r["driver_id"] == driver], key=lambda r: r["lap_number"])[:2]
            if len(selected) != 2:
                raise ValueError("R036 requires the full preregistered first-two-lap cohort")
            cases.extend({**r, "role": EVENT_ROLES[event]} for r in selected)
    return cases


def guard_dataset(root: Path) -> dict:
    """Inspect all JSON event identities before binary/inventory access."""
    header = read_json(root/"inputs.json")
    if header.get("schema_version") != VERSION+"-inputs":
        raise ValueError("R036 source header version mismatch")
    for case in header["cases"]:
        event = case["event_id"]
        assert_development_event(int(event[3:7]), int(event[-2:]), event_id=event)
        if (event not in EVENT_ROLES or case["role"] != EVENT_ROLES[event] or case["track_id"] != EVENT_TRACKS[event]
                or case["driver_id"] not in ("4", "44") or not RUN_ID_PATTERN.fullmatch(case["lap_id"])):
            raise ValueError("R036 source event/split/track/driver identity mismatch")
    if len({c["lap_id"] for c in header["cases"]}) != len(header["cases"]):
        raise ValueError("R036 duplicate condition identity")
    if header["profile"] == "research":
        parent, _ = load_driver_study(root/"parent")
        calibration, _, _ = load_calibration(root/"parent/calibration")
        if (parent["content_sha256"] != PARENT_SEAL or calibration["content_sha256"] != CALIBRATION_SEAL
                or header["parent_sha256"] != PARENT_SEAL or header["cases"] != parent_catalog(root/"parent")
                or header["condition_truth"] != "FROZEN_SOURCE_INITIAL_SPEED_KNOWN_MAP_GENERIC_PRIOR_VEHICLE"):
            raise ValueError("R036 requires frozen accepted R035 cohort, map and pace")
    elif (header["profile"] != "smoke" or header["condition_truth"] != "SIMULATED_FIXTURE_CONDITIONS"
          or header["parent_sha256"] is not None or len(header["cases"]) != 8
          or {(c["event_id"], c["driver_id"]) for c in header["cases"]} != {(e, d) for e in EVENT_ROLES for d in ("4", "44")}
          or any(c.get("fixture_truth") != "SIMULATED" for c in header["cases"])):
        raise ValueError("R036 invalid simulated dataset provenance")
    return header


def load_dataset(root: Path):
    header = guard_dataset(root)
    manifest = verify_inventory(root, VERSION+"-dataset")
    summary = read_json(root/"summary.json")
    check_seal(summary)
    if (summary["schema_version"] != VERSION+"-dataset" or manifest["summary_sha256"] != summary["content_sha256"]
            or summary["input_header_sha256"] != payload_sha256(header) or summary["profile"] != header["profile"]
            or summary["production_promotion"] is not False or summary["task_closure_eligible"] is not False):
        raise ValueError("R036 dataset source/truth binding mismatch")
    if header["profile"] == "research":
        _, choice, maps = load_calibration(root/"parent/calibration")
        pace = choice["selected"]["fraction"], choice["selected"]["maximum_mps"]
    else:
        maps = {}
        with np.load(root/"maps.npz", allow_pickle=False) as arrays:
            for track in ("bahrain", "monza"):
                maps[track] = DriverMap(float(arrays[track+"_length"]), *(arrays[track+"_"+k] for k in ("xy", "tangent", "curvature")))
        pace = .65, 60.
    return summary, header, maps, pace


def prepare_imitation_dataset(parent: Path, output: Path) -> dict:
    if output.exists() or output.resolve().is_relative_to(parent.resolve()):
        raise ValueError("R036 dataset output must be fresh and outside parent")
    source, _ = load_driver_study(parent)
    calibration = verify_driver_calibration(parent/"calibration")
    if source["content_sha256"] != PARENT_SEAL or calibration["summary_sha256"] != CALIBRATION_SEAL or not source["task_closure_eligible"]:
        raise ValueError("R036 requires accepted unchanged R035")
    cases = parent_catalog(parent)
    output.mkdir(parents=True)
    shutil.copytree(parent, output/"parent")
    header = {"schema_version": VERSION+"-inputs", "profile": "research", "parent_sha256": PARENT_SEAL,
              "condition_truth": "FROZEN_SOURCE_INITIAL_SPEED_KNOWN_MAP_GENERIC_PRIOR_VEHICLE", "cases": cases}
    write_manifest(output/"inputs.json", header)
    return finish_run(output, VERSION+"-dataset", {"schema_version": VERSION+"-dataset", "profile": "research",
                                                   "input_header_sha256": payload_sha256(header), "commit": commit_id(),
                                                   "production_promotion": False, "task_closure_eligible": False})


def make_imitation_smoke_dataset(output: Path) -> dict:
    if output.exists():
        raise FileExistsError("R036 smoke dataset must be fresh")
    output.mkdir(parents=True)
    arrays, cases = {}, []
    for track in ("bahrain", "monza"):
        coefficients = np.array([[0., 0.], [25., 0.], [0., 25.]]) if track == "bahrain" else np.array([[0., 0.], [40., 0.], [0., 30.]])
        m = DriverMap.from_curve(ReferenceCurve(coefficients, GeometryConfig(1, 0.), "SIMULATED_"+track))
        arrays[track+"_length"] = np.asarray(m.length_m)
        arrays.update({track+"_"+k: getattr(m, k) for k in ("xy", "tangent", "curvature")})
    for event, role in EVENT_ROLES.items():
        for driver in ("4", "44"):
            cases.append({"event_id": event, "driver_id": driver, "role": role, "track_id": EVENT_TRACKS[event],
                          "lap_id": event+"_"+driver+"_SIMULATED", "lap_number": 2, "initial_speed_mps": 10., "fixture_truth": "SIMULATED"})
    header = {"schema_version": VERSION+"-inputs", "profile": "smoke", "parent_sha256": None,
              "condition_truth": "SIMULATED_FIXTURE_CONDITIONS", "cases": cases}
    np.savez_compressed(output/"maps.npz", **arrays)
    write_manifest(output/"inputs.json", header)
    return finish_run(output, VERSION+"-dataset", {"schema_version": VERSION+"-dataset", "profile": "smoke",
                                                   "input_header_sha256": payload_sha256(header), "commit": commit_id(),
                                                   "production_promotion": False, "task_closure_eligible": False})


def initial_speed(dataset: Path, header: dict, case: dict, allowed_roles: tuple[str, ...]) -> float:
    if case["role"] not in allowed_roles or EVENT_ROLES[case["event_id"]] != case["role"]:
        raise ValueError("R036 forbidden event role at payload boundary")
    if header["profile"] == "smoke":
        return float(case["initial_speed_mps"])
    frame = pd.read_parquet(dataset/"parent/calibration/recorded/frames"/(case["lap_id"]+".parquet"), columns=["speed_mps"])
    return float(frame.speed_mps.iloc[0])


def execute(dataset, header, maps, pace, case, actor, lead, model=None, *, disturbed=False, step=.02, allowed_roles=("train",), progress=None):
    speed = initial_speed(dataset, header, case, allowed_roles)
    sign = 1 if case["driver_id"] == "4" else -1
    scenario = "disturbed" if disturbed else "nominal"
    key = actor+"__"+case["lap_id"]+"__"+scenario+"__"+str(step)
    kind = "transparent" if actor == "transparent" else "expert" if actor.startswith("expert") else "learned"
    if progress:
        progress("Running "+key)
    result, arrays = rollout_policy(maps[case["track_id"]], pace, speed, kind, lead, model, max_step=step,
                                    initial_lateral=sign*.4 if disturbed else 0., initial_heading=sign*.01 if disturbed else 0.)
    result.update(case_id=key, lap_id=case["lap_id"], event_id=case["event_id"], driver_id=case["driver_id"], role=case["role"],
                  track_id=case["track_id"], actor=actor, scenario=scenario, max_step_s=step, initial_speed_mps=speed)
    if progress:
        progress(str({k: result[k] for k in ("case_id", "passed", "station_weighted_mse_m2", "failure")}))
    return result, arrays


def validation_score(results: list[dict]) -> float | None:
    if not results or any(not r["passed"] for r in results):
        return None
    drivers = []
    for driver in ("4", "44"):
        rows = [r for r in results if r["driver_id"] == driver]
        if not rows:
            raise ValueError("R036 missing validation driver")
        drivers.append(float(np.mean([r["station_weighted_mse_m2"] for r in rows])))
    return float(np.mean(drivers))


def training_arrays(episodes: list[tuple[dict, dict]]) -> tuple[dict, list[dict]]:
    """Equal collection rounds and episodes; forbid validation/test before concatenation."""
    if not episodes or any(r["role"] != "train" or EVENT_ROLES[r["event_id"]] != "train" for r, _ in episodes):
        raise ValueError("R036 fitting/aggregation forbids validation and test episodes")
    rounds = sorted({r["collection_round"] for r, _ in episodes})
    pieces, ledger = [], []
    for index, (result, arrays) in enumerate(episodes):
        rows = arrays["features"]
        if len(rows) < 12:
            raise ValueError("R036 training episode prefix has fewer than12 labelled states")
        count = sum(r["collection_round"] == result["collection_round"] for r, _ in episodes)
        weight = np.full(len(rows), 1/(len(rounds)*count*len(rows)))
        y = np.array([expert_residual(row) for row in rows])
        pieces.append({"x": rows, "y": y, "weights": weight, "episode_index": np.full(len(rows), index, dtype=np.int64)})
        ledger.append({"case_id": result["case_id"], "lap_id": result["lap_id"], "event_id": result["event_id"],
                       "driver_id": result["driver_id"], "role": result["role"], "collection_round": result["collection_round"],
                       "rows": len(rows), "total_weight": float(weight.sum()), "completed": result["completed"],
                       "label_truth": "SIMULATED_EXPERT; NOT_HUMAN_STEERING"})
    return {k: np.concatenate([p[k] for p in pieces]) for k in pieces[0]}, ledger


def fit_imitation_study(dataset: Path, output: Path, progress=None) -> dict:
    if output.exists() or output.resolve().is_relative_to(dataset.resolve()):
        raise ValueError("R036 development output must be fresh and outside dataset")
    source, header, maps, pace = load_dataset(dataset)
    output.mkdir(parents=True)
    shutil.copytree(dataset, output/"dataset")
    paths = implementation_files()
    hashes = {p.name: file_sha256(p) for p in paths}
    trials, stored, model_table, episode_list = [], {}, {}, []
    validation = [c for c in header["cases"] if c["role"] == "validation"]

    def run(case, actor, lead, model=None, **kwargs):
        result, arrays = execute(dataset, header, maps, pace, case, actor, lead, model, progress=progress, **kwargs)
        trials.append(result)
        stored.update({result["case_id"]+"__"+k: v for k, v in arrays.items()})
        return result, arrays

    expert_scores = {}
    for lead in LEADS:
        rows = [run(case, "expert"+str(lead), lead, allowed_roles=("validation",))[0] for case in validation]
        expert_scores[str(lead)] = validation_score(rows)
    eligible = [lead for lead in LEADS if expert_scores[str(lead)] is not None]
    if not eligible:
        write_manifest(output/"rejected_experts.json", {"trials": trials, "expert_scores": expert_scores})
        raise ValueError("R036 every preregistered expert failed; rejected trial evidence retained")
    lead = min(eligible, key=lambda candidate: (expert_scores[str(candidate)], candidate))
    for case in header["cases"]:
        if case["role"] != "train":
            continue
        for disturbed in (False, True):
            result, arrays = run(case, "expert_train", lead, disturbed=disturbed)
            result["collection_round"] = 0
            episode_list.append((result, arrays))
    base_data, base_ledger = training_arrays(episode_list)
    scores = {}
    for degree in (1, 2):
        for alpha in ALPHAS:
            name = f"bc_d{degree}_a{alpha}"
            model = fit_policy(base_data["x"], base_data["y"], base_data["weights"], degree, alpha)
            model_table[name] = model
            scores[name] = validation_score([run(case, name, lead, model, allowed_roles=("validation",))[0] for case in validation])
    eligible = [name for name in scores if scores[name] is not None]
    if not eligible:
        write_manifest(output/"rejected_students.json", {"trials": trials, "scores": scores})
        raise ValueError("R036 every behavior-cloning model failed; evidence retained")
    best_bc = min(eligible, key=lambda n: (scores[n], model_table[n]["parameters"], -model_table[n]["alpha"]))
    linear = [n for n in eligible if model_table[n]["degree"] == 1]
    best_linear = min(linear, key=lambda n: (scores[n], -model_table[n]["alpha"])) if linear else None
    for case in header["cases"]:
        if case["role"] != "train":
            continue
        for disturbed in (False, True):
            result, arrays = run(case, "collection_learner", lead, model_table[best_bc], disturbed=disturbed)
            result["collection_round"] = 1
            episode_list.append((result, arrays))
    aggregate, ledger = training_arrays(episode_list)
    model = model_table[best_bc]
    model_table["aggregated"] = fit_policy(aggregate["x"], aggregate["y"], aggregate["weights"], model["degree"], model["alpha"])
    scores["aggregated"] = validation_score([run(case, "aggregated", lead, model_table["aggregated"], allowed_roles=("validation",))[0] for case in validation])
    selected = "aggregated" if scores["aggregated"] is not None and scores["aggregated"] < scores[best_bc] else best_bc
    result = {"profile": header["profile"], "expert_validation_scores": expert_scores, "selected_lead_s": lead,
              "validation_scores": scores, "best_bc": best_bc, "best_linear": best_linear, "selected": selected,
              "models": model_table, "trials": trials, "base_episode_ledger": base_ledger, "episode_ledger": ledger,
              "base_training_rows": len(base_data["y"]), "aggregated_training_rows": len(aggregate["y"]),
              "test_outcomes_used": False, "training_action_truth": "SIMULATED_EXPERT; NOT_MEASURED_HUMAN",
              "production_promotion": False, "task_closure_eligible": False}
    write_manifest(output/"development.json", result)
    np.savez_compressed(output/"training.npz", **{"base_"+k: v for k, v in base_data.items()}, **{"aggregate_"+k: v for k, v in aggregate.items()})
    np.savez_compressed(output/"rollouts.npz", **stored)
    if hashes != {p.name: file_sha256(p) for p in paths}:
        raise ValueError("R036 implementation changed during fitting")
    (output/"sources").mkdir()
    for p in paths:
        shutil.copyfile(p, output/"sources"/p.name)
    return finish_run(output, VERSION+"-development", {"schema_version": VERSION+"-development", "profile": header["profile"],
                                                       "dataset_sha256": source["content_sha256"], "development_sha256": payload_sha256(result),
                                                       "selected": selected, "selected_model_sha256": payload_sha256(model_table[selected]),
                                                       "selected_lead_s": lead, "test_outcomes_used": False, "implementation_sha256": hashes,
                                                       "production_promotion": False, "task_closure_eligible": False, "commit": commit_id(),
                                                       "environment": {"python": platform.python_version(), "numpy": np.__version__}})


def load_development(root: Path):
    source, header, maps, pace = load_dataset(root/"dataset")
    manifest = verify_inventory(root, VERSION+"-development")
    summary, result = read_json(root/"summary.json"), read_json(root/"development.json")
    check_seal(summary)
    if (summary["schema_version"] != VERSION+"-development" or manifest["summary_sha256"] != summary["content_sha256"]
            or summary["dataset_sha256"] != source["content_sha256"] or summary["development_sha256"] != payload_sha256(result)
            or summary["selected"] != result["selected"] or summary["selected_lead_s"] != result["selected_lead_s"]
            or summary["selected_model_sha256"] != payload_sha256(result["models"][result["selected"]])
            or summary["profile"] != header["profile"] or result["profile"] != header["profile"]
            or any(obj["test_outcomes_used"] is not False or obj["production_promotion"] is not False or obj["task_closure_eligible"] is not False for obj in (summary, result))):
        raise ValueError("R036 frozen development source/selection/truth binding mismatch")
    for name, digest in summary["implementation_sha256"].items():
        if Path(name).name != name or ":" in name or "\\" in name or file_sha256(root/"sources"/name) != digest:
            raise ValueError("R036 implementation snapshot mismatch")
    return summary, result, header, maps, pace


def verify_imitation_development(root: Path, *, replay_dynamics=True, progress=None) -> dict:
    from apexsim.research.imitation_audit import audit_development

    summary, result, header, maps, _ = load_development(root)
    return audit_development(root, summary, result, header, maps, replay_dynamics=replay_dynamics, progress=progress)


def improvement_gate(cases: list[dict], expected_laps: set[str], profile: str) -> dict:
    """Matched source denominators and station-weighted driver/lap scores."""
    final = [r for r in cases if r["actor"] == "final" and r["max_step_s"] == .02]
    baseline = [r for r in cases if r["actor"] == "transparent" and r["max_step_s"] == .02]
    expected = {(lap, scenario) for lap in expected_laps for scenario in ("nominal", "disturbed")}
    catalog_ok = (len(final) == len(expected) and {(r["lap_id"], r["scenario"]) for r in final} == expected
                  and len(baseline) == len(expected) and {(r["lap_id"], r["scenario"]) for r in baseline} == expected)
    support = catalog_ok and all(r["passed"] for r in final) and all(r["passed"] for r in baseline)
    recovery = all(abs(r["final_lateral_error_m"]) < .4 for r in final if r["scenario"] == "disturbed")
    drivers = {}
    finish_ok = True
    for driver in ("4", "44"):
        a = [r for r in final if r["driver_id"] == driver and r["scenario"] == "nominal"]
        b = [r for r in baseline if r["driver_id"] == driver and r["scenario"] == "nominal"]
        if not a or len(a) != len(b) or any(r["station_weighted_mse_m2"] is None for r in [*a, *b]):
            drivers[driver] = {"supported": False}
            support = False
            continue
        am, bm = float(np.mean([r["station_weighted_mse_m2"] for r in a])), float(np.mean([r["station_weighted_mse_m2"] for r in b]))
        ap, bp = float(np.mean([r["p95_lateral_error_m"] for r in a])), float(np.mean([r["p95_lateral_error_m"] for r in b]))
        drivers[driver] = {"supported": True, "final_mse_m2": am, "baseline_mse_m2": bm,
                           "rmse_ratio": float(np.sqrt(am/bm)) if bm > 0 else None, "p95_ratio": ap/bp if bp > 0 else None}
        lookup = {r["lap_id"]: r for r in b}
        finish_ok = finish_ok and all(r["completion_time_s"] is not None and lookup[r["lap_id"]]["completion_time_s"] is not None
                                     and r["completion_time_s"] <= 1.01*lookup[r["lap_id"]]["completion_time_s"] for r in a)
    macro_ratio = None
    if support and all(v["supported"] for v in drivers.values()):
        denominator = float(np.mean([v["baseline_mse_m2"] for v in drivers.values()]))
        macro_ratio = float(np.sqrt(np.mean([v["final_mse_m2"] for v in drivers.values()])/denominator)) if denominator > 0 else None
    improvement = bool(macro_ratio is not None and macro_ratio <= .9 and all(v["rmse_ratio"] is not None and v["rmse_ratio"] <= .95
                        and v["p95_ratio"] is not None and v["p95_ratio"] <= 1.05 for v in drivers.values()))
    passed = bool(support and recovery and finish_ok and improvement)
    return {"catalog_passed": catalog_ok, "stability_passed": support, "small_disturbance_recovery_passed": recovery,
            "finish_noninferiority_passed": bool(finish_ok), "tracking_improvement_passed": improvement,
            "macro_rmse_ratio": macro_ratio, "by_driver": drivers, "passed": passed, "profile": profile,
            "required_final_cases": len(expected), "evaluated_final_cases": len(final)}


def compute_imitation_evaluation(development: Path, progress=None):
    from apexsim.examples.driver_study import refinement_metrics

    summary, fitted, header, maps, pace = load_development(development)
    lead = fitted["selected_lead_s"]
    linear = fitted["best_linear"] or next(name for name, m in fitted["models"].items() if m["degree"] == 1)
    identities = {"transparent": None, "expert": None, "linear": linear, "bc": fitted["best_bc"], "final": fitted["selected"]}
    cases, arrays, refinements = [], {}, []
    for case in header["cases"]:
        if case["role"] != "test":
            continue
        for actor, checkpoint in identities.items():
            model = fitted["models"].get(checkpoint)
            for disturbed in (False, True):
                result, trajectory = execute(development/"dataset", header, maps, pace, case, actor, lead, model,
                                             disturbed=disturbed, allowed_roles=("test",), progress=progress)
                cases.append(result)
                arrays.update({result["case_id"]+"__"+k: v for k, v in trajectory.items()})
        result, refined = execute(development/"dataset", header, maps, pace, case, "final", lead, fitted["models"][fitted["selected"]],
                                 step=.01, allowed_roles=("test",), progress=progress)
        cases.append(result)
        arrays.update({result["case_id"]+"__"+k: v for k, v in refined.items()})
        nominal_result = next(r for r in cases if r["lap_id"] == case["lap_id"] and r["actor"] == "final" and r["scenario"] == "nominal" and r["max_step_s"] == .02)
        nominal = {k: arrays[nominal_result["case_id"]+"__"+k] for k in refined}
        refinements.append({"lap_id": case["lap_id"], **refinement_metrics(maps[case["track_id"]], nominal, refined, nominal_result, result)})
    laps = {c["lap_id"] for c in header["cases"] if c["role"] == "test"}
    gate = improvement_gate(cases, laps, header["profile"])
    gate["refinement_passed"] = len(refinements) == len(laps) and all(r["passed"] for r in refinements)
    gate["passed"] = gate["passed"] and gate["refinement_passed"]
    return {"profile": header["profile"], "development_sha256": summary["content_sha256"], "selected": fitted["selected"],
            "selected_lead_s": lead, "checkpoint_identities": identities, "cases": cases, "refinements": refinements,
            "gate": gate, "production_promotion": False, "conditional_research_only": True,
            "training_action_truth": "SIMULATED_EXPERT; NOT_MEASURED_HUMAN", "complete_measured_car_replay": False}, arrays


def run_imitation_evaluation(development: Path, verification: Path, output: Path, progress=None):
    from apexsim.research.imitation_audit import audit_final_paths

    if output.exists() or output.resolve().is_relative_to(development.resolve()):
        raise ValueError("R036 evaluation output must be fresh and outside development")
    summary, _, _, _, _ = load_development(development)
    receipt = read_json(verification)
    if (receipt.get("verified") is not True or receipt.get("replay_dynamics") is not True
            or receipt.get("summary_sha256") != summary["content_sha256"]):
        raise ValueError("R036 evaluation requires a full run-bound development replay receipt")
    verify_imitation_development(development, replay_dynamics=False)
    paths = implementation_files()
    hashes = {p.name: file_sha256(p) for p in paths}
    if summary["implementation_sha256"] != hashes:
        raise ValueError("R036 implementation changed after model freeze; explicitly refreeze before test")
    output.mkdir(parents=True)
    shutil.copytree(development, output/"development")
    write_manifest(output/"development_verification.json", receipt)
    result, arrays = compute_imitation_evaluation(output/"development", progress)
    result["independent_audit"] = audit_final_paths(result, arrays, progress)
    passed = result["profile"] == "research" and result["gate"]["passed"] and result["independent_audit"]["passed"]
    decision = "ACCEPT_CONDITIONAL_IMITATION_DRIVER" if passed else "SIMULATED_EXECUTION_ONLY" if result["profile"] == "smoke" else "REJECT_CONDITIONAL_IMITATION_DRIVER"
    result.update(task_closure_eligible=passed, decision=decision)
    np.savez_compressed(output/"trajectories.npz", **arrays)
    write_manifest(output/"results.json", result)
    if hashes != {p.name: file_sha256(p) for p in paths}:
        raise ValueError("R036 source changed during evaluation")
    (output/"sources").mkdir()
    for p in paths:
        shutil.copyfile(p, output/"sources"/p.name)
    return finish_run(output, VERSION, {"schema_version": VERSION, "profile": result["profile"], "decision": decision,
                                       "task_closure_eligible": passed, "production_promotion": False, "conditional_research_only": True,
                                       "results_sha256": payload_sha256(result), "development_sha256": summary["content_sha256"],
                                       "development_verification_sha256": payload_sha256(receipt), "implementation_sha256": hashes, "commit": commit_id()})


def load_imitation_evaluation(root: Path):
    development, _, header, _, _ = load_development(root/"development")
    manifest = verify_inventory(root, VERSION)
    summary, result = read_json(root/"summary.json"), read_json(root/"results.json")
    check_seal(summary)
    receipt = read_json(root/"development_verification.json")
    if (summary["schema_version"] != VERSION or manifest["summary_sha256"] != summary["content_sha256"]
            or summary["results_sha256"] != payload_sha256(result) or summary["development_sha256"] != development["content_sha256"]
            or result["development_sha256"] != development["content_sha256"] or summary["development_verification_sha256"] != payload_sha256(receipt)
            or receipt.get("summary_sha256") != development["content_sha256"] or receipt.get("verified") is not True or receipt.get("replay_dynamics") is not True
            or summary["profile"] != header["profile"] or any(summary[k] != result[k] for k in ("profile", "decision", "task_closure_eligible", "production_promotion", "conditional_research_only"))
            or result["production_promotion"] is not False or result["conditional_research_only"] is not True):
        raise ValueError("R036 evaluation source/truth/result binding mismatch")
    for name, digest in summary["implementation_sha256"].items():
        if Path(name).name != name or ":" in name or "\\" in name or file_sha256(root/"sources"/name) != digest:
            raise ValueError("R036 evaluation implementation snapshot mismatch")
    return summary, result


def verify_imitation_evaluation(root: Path, progress=None):
    from apexsim.research.evidence import compare_numeric
    from apexsim.research.imitation_audit import audit_final_paths

    summary, stored = load_imitation_evaluation(root)
    # Physical demonstration replay was completed before model freeze and is run-bound
    # above; recheck all independent feature/fit/selection equations after relocation.
    development_audit = verify_imitation_development(root/"development", replay_dynamics=False)
    result, arrays = compute_imitation_evaluation(root/"development", progress)
    for key, value in result.items():
        compare_numeric(value, stored[key], "R036 evaluation/"+key)
    maximum = 0.
    with np.load(root/"trajectories.npz", allow_pickle=False) as saved:
        if set(saved.files) != set(arrays):
            raise ValueError("R036 evaluation trajectory catalog mismatch")
        for key, value in arrays.items():
            if saved[key].shape != value.shape or not np.allclose(saved[key], value, atol=1e-8, rtol=1e-7):
                raise ValueError("R036 evaluation scientific trajectory mismatch: "+key)
            maximum = max(maximum, float(np.max(abs(saved[key]-value))))
    audit = audit_final_paths(result, arrays, progress)
    compare_numeric(audit, stored["independent_audit"])
    passed = result["profile"] == "research" and result["gate"]["passed"] and audit["passed"]
    decision = "ACCEPT_CONDITIONAL_IMITATION_DRIVER" if passed else "SIMULATED_EXECUTION_ONLY" if result["profile"] == "smoke" else "REJECT_CONDITIONAL_IMITATION_DRIVER"
    if stored["task_closure_eligible"] != passed or stored["decision"] != decision:
        raise ValueError("R036 false completion")
    return {"verified": True, "summary_sha256": summary["content_sha256"], "task_closure_eligible": passed, "decision": decision,
            "cases": len(result["cases"]), "maximum_replay_difference": maximum, "independent_audit": audit,
            "development_equation_audit": development_audit}
