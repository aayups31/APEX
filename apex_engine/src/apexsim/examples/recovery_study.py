"""R037 sealed input freeze, complete multi-lap catalog and scientific regeneration."""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np

from apexsim.examples.imitation_study import (
    commit_id,
    initial_speed,
    load_development,
    load_imitation_evaluation,
)
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research.closed_loop import compare_continuous_paths, recovery_metrics, run_continuous
from apexsim.research.closed_loop_audit import audit_continuous
from apexsim.research.evidence import check_seal, compare_numeric, finish_run, read_json, verify_inventory

VERSION = "apex-multilap-recovery-v1"
PARENT = "2f549c5224413fde09f5d99af2043305c5cac81ce49daa9afd9647a2be4264ae"
PROTOCOL = Path(__file__).resolve().parents[4]/"research/protocols/MULTILAP_RECOVERY.md"


def sources() -> list[Path]:
    from apexsim.research import closed_loop, closed_loop_audit
    return [Path(__file__), Path(closed_loop.__file__), Path(closed_loop_audit.__file__), PROTOCOL]


def source_hashes() -> dict:
    return {p.name: file_sha256(p) for p in sources()}


def snapshot(output: Path) -> None:
    (output/"sources").mkdir()
    for path in sources():
        shutil.copyfile(path, output/"sources"/path.name)


def check_snapshot(root: Path, hashes: dict) -> None:
    if set(hashes) != {p.name for p in sources()}:
        raise ValueError("R037 source snapshot catalog changed")
    for name, digest in hashes.items():
        if Path(name).name != name or file_sha256(root/"sources"/name) != digest:
            raise ValueError("R037 source snapshot hash mismatch")


def prepare_recovery(reference: Path, output: Path) -> dict:
    if output.exists() or output.resolve().is_relative_to(reference.resolve()):
        raise ValueError("R037 input output must be fresh and outside reference")
    parent, result = load_imitation_evaluation(reference)
    if parent["profile"] == "research" and (parent["content_sha256"] != PARENT or not result["task_closure_eligible"]):
        raise ValueError("R037 requires the accepted frozen R036 evaluation")
    output.mkdir(parents=True)
    shutil.copytree(reference, output/"reference")
    snapshot(output)
    return finish_run(output, VERSION+"-inputs", {"schema_version": VERSION+"-inputs", "profile": parent["profile"],
                       "parent_sha256": parent["content_sha256"], "implementation_sha256": source_hashes(),
                       "commit": commit_id(), "production_promotion": False, "task_closure_eligible": False})


def load_recovery_inputs(root: Path):
    # The parent guards every event JSON identity before binary/inventory reads.
    parent, _ = load_imitation_evaluation(root/"reference")
    _, development, header, maps, pace = load_development(root/"reference/development")
    manifest = verify_inventory(root, VERSION+"-inputs")
    summary = read_json(root/"summary.json")
    check_seal(summary)
    if (summary["schema_version"] != VERSION+"-inputs" or manifest["summary_sha256"] != summary["content_sha256"]
            or summary["parent_sha256"] != parent["content_sha256"] or summary["profile"] != parent["profile"]
            or summary["production_promotion"] is not False or summary["task_closure_eligible"] is not False
            or (parent["profile"] == "research" and (parent["content_sha256"] != PARENT or not parent["task_closure_eligible"]))):
        raise ValueError("R037 parent/source/truth binding mismatch")
    check_snapshot(root, summary["implementation_sha256"])
    return summary, development, header, maps, pace


def execute_case(inputs: Path, header: dict, development: dict, maps: dict, pace: tuple, case: dict,
                 actor: str, scenario: str, step: float, *, laps: int, controller=None, progress=None) -> tuple[dict, dict]:
    model = development["models"][development["selected"]]
    speed = initial_speed(inputs/"reference/development/dataset", header, case, ("test",))
    key = actor+"__"+case["lap_id"]+"__"+scenario+"__"+str(step)
    if progress:
        progress("Running "+key)
    kind = "transparent" if actor == "transparent" else "learned"
    result, arrays = run_continuous(maps[case["track_id"]], pace, speed, kind, development["selected_lead_s"], model,
                                   laps=laps, scenario=scenario if scenario in ("nominal", "pulse_left", "pulse_right", "challenge") else "nominal",
                                   max_step=step, controller=controller)
    result.update(case_id=key, actor=actor, scenario=scenario, lap_id=case["lap_id"], driver_id=case["driver_id"],
                  event_id=case["event_id"], track_id=case["track_id"], track_length_m=maps[case["track_id"]].length_m,
                  initial_speed_mps=speed)
    if progress:
        progress(str({k: result[k] for k in ("case_id", "passed", "failure", "completion_time_s")}))
    return result, arrays


def compute_recovery(inputs: Path, progress=None) -> tuple[dict, dict]:
    source, development, header, maps, pace = load_recovery_inputs(inputs)
    if source["implementation_sha256"] != source_hashes():
        raise ValueError("R037 source changed after input freeze")
    catalog = [c for c in header["cases"] if c["role"] == "test"]
    laps = 5 if header["profile"] == "research" else 3
    cases, stored, refinement = [], {}, []
    for case in catalog:
        nominal = {}
        for actor in ("transparent", "learned"):
            for scenario in ("nominal", "pulse_left", "pulse_right"):
                result, values = execute_case(inputs, header, development, maps, pace, case, actor, scenario, .02, laps=laps, progress=progress)
                if scenario == "nominal":
                    nominal[actor] = result, values
                else:
                    result["recovery"] = recovery_metrics(result, values, nominal[actor][1])
                cases.append(result)
                stored.update({result["case_id"]+"__"+k: v for k, v in values.items()})
        fine, values = execute_case(inputs, header, development, maps, pace, case, "learned", "nominal", .01, laps=laps, progress=progress)
        comparison = compare_continuous_paths(nominal["learned"][1], values)
        finish = abs(fine["completion_time_s"]-nominal["learned"][0]["completion_time_s"]) if fine["completed"] and nominal["learned"][0]["completed"] else None
        refinement.append({"lap_id": case["lap_id"], **comparison, "finish_difference_s": finish,
                           "passed": comparison["passed"] and finish is not None and finish <= .2})
        cases.append(fine)
        stored.update({fine["case_id"]+"__"+k: v for k, v in values.items()})
    challenge, values = execute_case(inputs, header, development, maps, pace, catalog[0], "learned", "challenge", .02, laps=laps, progress=progress)
    cases.append(challenge)
    stored.update({challenge["case_id"]+"__"+k: v for k, v in values.items()})
    required = [r for r in cases if r["scenario"] != "challenge"]
    recovery = [r for r in required if r["scenario"] != "nominal"]
    pace_ok = True
    for case in catalog:
        rows = [r for r in required if r["lap_id"] == case["lap_id"] and r["scenario"] == "nominal" and r["max_step_s"] == .02]
        by_actor = {r["actor"]: r for r in rows}
        pace_ok &= all(r["completed"] for r in rows) and by_actor["learned"]["completion_time_s"] <= 1.01*by_actor["transparent"]["completion_time_s"]
    gate = {"required_cases": len(catalog)*7, "evaluated_required_cases": len(required),
            "all_required_stable": all(r["passed"] for r in required),
            "recovery_passed": bool(recovery and all(len(r["recovery"]) == 2 and all(v["passed"] for v in r["recovery"]) for r in recovery)),
            "refinement_passed": all(r["passed"] for r in refinement), "pace_noninferiority_passed": bool(pace_ok)}
    gate["passed"] = bool(len(required) == gate["required_cases"] and all(gate[k] for k in ("all_required_stable", "recovery_passed", "refinement_passed", "pace_noninferiority_passed")))
    return {"profile": header["profile"], "input_sha256": source["content_sha256"], "cases": cases, "refinements": refinement,
            "gate": gate, "production_promotion": False, "continuous_laps": laps}, stored


def run_recovery(inputs: Path, output: Path, progress=None) -> dict:
    if output.exists() or output.resolve().is_relative_to(inputs.resolve()):
        raise ValueError("R037 output must be fresh and outside inputs")
    hashes = source_hashes()
    load_recovery_inputs(inputs)
    output.mkdir(parents=True)
    shutil.copytree(inputs, output/"inputs")
    result, arrays = compute_recovery(output/"inputs", progress)
    result["independent_audit"] = audit_continuous(result["cases"], arrays, actor="learned", full_scenario="nominal", progress=progress)
    passed = result["profile"] == "research" and result["gate"]["passed"] and result["independent_audit"]["passed"]
    result.update(task_closure_eligible=passed, decision="ACCEPT_CONDITIONAL_MULTILAP_RECOVERY" if passed else "SIMULATED_EXECUTION_ONLY" if result["profile"] == "smoke" else "REJECT_MULTILAP_RECOVERY")
    write_manifest(output/"results.json", result)
    np.savez_compressed(output/"trajectories.npz", **arrays)
    if source_hashes() != hashes:
        raise ValueError("R037 implementation changed during study")
    return finish_run(output, VERSION, {"schema_version": VERSION, "profile": result["profile"], "decision": result["decision"],
                      "task_closure_eligible": passed, "production_promotion": False, "input_sha256": result["input_sha256"],
                      "results_sha256": payload_sha256(result), "implementation_sha256": hashes, "commit": commit_id()})


def load_recovery(root: Path) -> tuple[dict, dict]:
    source, _, header, _, _ = load_recovery_inputs(root/"inputs")
    manifest = verify_inventory(root, VERSION)
    summary, result = read_json(root/"summary.json"), read_json(root/"results.json")
    check_seal(summary)
    if (summary["schema_version"] != VERSION or summary["content_sha256"] != manifest["summary_sha256"]
            or summary["input_sha256"] != source["content_sha256"] or summary["results_sha256"] != payload_sha256(result)
            or summary["implementation_sha256"] != source["implementation_sha256"]
            or summary["profile"] != header["profile"] or result["profile"] != header["profile"]
            or result["input_sha256"] != source["content_sha256"]
            or any(summary[k] != result[k] for k in ("decision", "task_closure_eligible", "production_promotion"))
            or summary["production_promotion"] is not False):
        raise ValueError("R037 run source/result/truth binding mismatch")
    return summary, result


def verify_recovery(root: Path, progress=None) -> dict:
    summary, saved = load_recovery(root)
    result, arrays = compute_recovery(root/"inputs", progress)
    for key, value in result.items():
        compare_numeric(value, saved[key], "R037/"+key)
    maximum = 0.
    with np.load(root/"trajectories.npz", allow_pickle=False) as archive:
        if set(archive.files) != set(arrays):
            raise ValueError("R037 trajectory catalog mismatch")
        for key, value in arrays.items():
            if archive[key].shape != value.shape or not np.allclose(archive[key], value, atol=1e-8, rtol=1e-7):
                raise ValueError("R037 scientific trajectory mismatch: "+key)
            if value.size:
                maximum = max(maximum, float(np.max(abs(archive[key]-value))))
    audit = audit_continuous(result["cases"], arrays, actor="learned", full_scenario="nominal", progress=progress)
    compare_numeric(audit, saved["independent_audit"])
    passed = result["profile"] == "research" and result["gate"]["passed"] and audit["passed"]
    decision = "ACCEPT_CONDITIONAL_MULTILAP_RECOVERY" if passed else "SIMULATED_EXECUTION_ONLY" if result["profile"] == "smoke" else "REJECT_MULTILAP_RECOVERY"
    if saved["task_closure_eligible"] != passed or saved["decision"] != decision:
        raise ValueError("R037 false completion")
    return {"verified": True, "summary_sha256": summary["content_sha256"], "task_closure_eligible": passed,
            "decision": decision, "cases": len(result["cases"]), "maximum_replay_difference": maximum, "independent_audit": audit}
