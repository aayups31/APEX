"""R038 training-only support fit and complete conditional fallback campaign."""
from __future__ import annotations

import shutil
from itertools import pairwise
from pathlib import Path

import numpy as np

from apexsim.examples.imitation_study import commit_id, load_development
from apexsim.examples.recovery_study import execute_case, load_recovery, load_recovery_inputs
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research.closed_loop import compare_continuous_paths
from apexsim.research.closed_loop_audit import audit_continuous
from apexsim.research.evidence import check_seal, compare_numeric, finish_run, read_json, verify_inventory
from apexsim.research.support_audit import audit_detector
from apexsim.research.support_fallback import RuntimeController, fit_envelope

VERSION = "apex-support-fallback-v1"
PROTOCOL = Path(__file__).resolve().parents[4]/"research/protocols/SUPPORT_FALLBACK.md"
FAULTS = ("feature_shift", "residual_bias", "nonfinite")
HARD = ("missing_map", "untrusted_state", "vehicle_mismatch")


def sources() -> list[Path]:
    from apexsim.research import support_audit, support_fallback
    return [Path(__file__), Path(support_audit.__file__), Path(support_fallback.__file__), PROTOCOL]


def hashes() -> dict:
    return {p.name: file_sha256(p) for p in sources()}


def detector_data(recovery: Path) -> tuple[np.ndarray, np.ndarray, dict]:
    root = recovery/"inputs/reference/development"
    _, result, _, _, _ = load_development(root)
    if any(r["role"] != "train" for r in result["base_episode_ledger"]):
        raise ValueError("R038 detector fitting forbids non-training episodes")
    with np.load(root/"training.npz", allow_pickle=False) as archive:
        training = archive["base_x"].copy()
    trials = [r for r in result["trials"] if r["role"] == "validation" and r["actor"] == result["selected"]]
    if not trials or any(r["event_id"] != "F1_2024_R01" for r in trials):
        raise ValueError("R038 detector cutoff requires frozen validation-only episodes")
    with np.load(root/"rollouts.npz", allow_pickle=False) as archive:
        validation = np.concatenate([archive[r["case_id"]+"__features"] for r in trials])
    ledger = {"training_episodes": result["base_episode_ledger"], "validation_cases": [r["case_id"] for r in trials],
              "training_rows": len(training), "validation_rows": len(validation), "test_outcomes_used_for_fit": False,
              "source_training_sha256": file_sha256(root/"training.npz"), "source_rollouts_sha256": file_sha256(root/"rollouts.npz")}
    return training, validation, ledger


def fit_support(recovery: Path, verification: Path, output: Path) -> dict:
    if output.exists() or output.resolve().is_relative_to(recovery.resolve()):
        raise ValueError("R038 detector output must be fresh and outside recovery")
    parent, result = load_recovery(recovery)
    receipt = read_json(verification)
    if (not receipt.get("verified") or receipt.get("summary_sha256") != parent["content_sha256"]
            or not receipt.get("independent_audit", {}).get("passed") or not result["gate"]["passed"]
            or (parent["profile"] == "research" and not parent["task_closure_eligible"])):
        raise ValueError("R038 requires passing R037 and its bound full replay")
    training, validation, ledger = detector_data(recovery)
    model = fit_envelope(training, validation)
    independent = audit_detector(training, validation, model)
    output.mkdir(parents=True)
    shutil.copytree(recovery, output/"recovery")
    write_manifest(output/"recovery_verification.json", receipt)
    write_manifest(output/"detector.json", {"model": model, "ledger": ledger, "independent_audit": independent})
    (output/"sources").mkdir()
    for path in sources():
        shutil.copyfile(path, output/"sources"/path.name)
    return finish_run(output, VERSION+"-detector", {"schema_version": VERSION+"-detector", "profile": parent["profile"],
                      "recovery_sha256": parent["content_sha256"], "recovery_verification_sha256": payload_sha256(receipt),
                      "model_sha256": payload_sha256(model), "ledger_sha256": payload_sha256(ledger),
                      "implementation_sha256": hashes(), "test_outcomes_used": False,
                      "production_promotion": False, "task_closure_eligible": False, "commit": commit_id()})


def load_support_detector(root: Path):
    parent, result = load_recovery(root/"recovery")
    manifest = verify_inventory(root, VERSION+"-detector")
    summary, saved = read_json(root/"summary.json"), read_json(root/"detector.json")
    receipt = read_json(root/"recovery_verification.json")
    check_seal(summary)
    if (summary["schema_version"] != VERSION+"-detector" or manifest["summary_sha256"] != summary["content_sha256"]
            or summary["recovery_sha256"] != parent["content_sha256"] or not result["gate"]["passed"]
            or summary["profile"] != parent["profile"] or summary["model_sha256"] != payload_sha256(saved["model"])
            or summary["ledger_sha256"] != payload_sha256(saved["ledger"])
            or summary["recovery_verification_sha256"] != payload_sha256(receipt)
            or receipt.get("summary_sha256") != parent["content_sha256"] or not receipt.get("verified")
            or not receipt.get("independent_audit", {}).get("passed")
            or summary["test_outcomes_used"] is not False or summary["production_promotion"] is not False
            or summary["task_closure_eligible"] is not False or (parent["profile"] == "research" and not parent["task_closure_eligible"])):
        raise ValueError("R038 detector source/fit/truth binding mismatch")
    if set(summary["implementation_sha256"]) != {p.name for p in sources()}:
        raise ValueError("R038 implementation catalog mismatch")
    for name, digest in summary["implementation_sha256"].items():
        if Path(name).name != name or file_sha256(root/"sources"/name) != digest:
            raise ValueError("R038 implementation snapshot mismatch")
    training, validation, ledger = detector_data(root/"recovery")
    compare_numeric(ledger, saved["ledger"], "R038 role ledger")
    compare_numeric(fit_envelope(training, validation), saved["model"], "R038 refitted envelope")
    independent = audit_detector(training, validation, saved["model"])
    compare_numeric(independent, saved["independent_audit"])
    return summary, saved["model"]


def decision_metrics(case: dict) -> dict:
    decisions = case["decisions"]
    faults = [r for r in decisions if r["fault_active"]]
    switches = sum(a["mode"] != b["mode"] for a, b in pairwise(decisions))
    return {"fallback_fraction": sum(r["mode"] == "fallback" for r in decisions)/max(1, len(decisions)),
            "switches": switches, "faulted_commands": len(faults),
            "first_fault_detections": sum(r["first_fault_command"] and r["mode"] == "fallback" for r in decisions),
            "all_faulted_actions_rejected": bool(faults and all(r["mode"] == "fallback" for r in faults)),
            "returned_to_learned": bool(decisions and decisions[-1]["mode"] == "learned")}


def compute_support(detector: Path, progress=None) -> tuple[dict, dict]:
    source, envelope = load_support_detector(detector)
    if source["implementation_sha256"] != hashes():
        raise ValueError("R038 implementation changed after detector freeze")
    inputs = detector/"recovery/inputs"
    _, development, header, maps, pace = load_recovery_inputs(inputs)
    model = development["models"][development["selected"]]
    catalog = [c for c in header["cases"] if c["role"] == "test"]
    cases, stored, refinements = [], {}, []
    for case in catalog:
        local = {}
        recipes = [(actor, "nominal", .02) for actor in ("unguarded", "guarded", "transparent")]
        recipes += [(actor, fault, .02) for fault in FAULTS for actor in ("unguarded", "guarded")]
        recipes += [("guarded", "residual_bias", .01), *(("guarded", fault, .02) for fault in HARD)]
        for actor, fault, step in recipes:
            controller = RuntimeController(actor, fault, envelope, model)
            result, values = execute_case(inputs, header, development, maps, pace, case, actor, fault, step,
                                          laps=3, controller=controller, progress=progress)
            result["supervision"] = decision_metrics(result)
            cases.append(result)
            stored.update({result["case_id"]+"__"+k: v for k, v in values.items()})
            local[(actor, fault, step)] = result, values
        coarse, a = local[("guarded", "residual_bias", .02)]
        fine, b = local[("guarded", "residual_bias", .01)]
        comparison = compare_continuous_paths(a, b)
        finish = abs(coarse["completion_time_s"]-fine["completion_time_s"]) if coarse["completed"] and fine["completed"] else None
        refinements.append({"lap_id": case["lap_id"], **comparison, "finish_difference_s": finish,
                            "passed": comparison["passed"] and finish is not None and finish <= .2})
    guarded = [r for r in cases if r["actor"] == "guarded" and r["scenario"] not in HARD]
    nominal = [r for r in guarded if r["scenario"] == "nominal"]
    faulted = [r for r in guarded if r["scenario"] in FAULTS]
    transparent = [r for r in cases if r["actor"] == "transparent"]
    hard = [r for r in cases if r["scenario"] in HARD]
    nominal_ok = True
    for row in nominal:
        baseline = next(r for r in cases if r["actor"] == "unguarded" and r["scenario"] == "nominal" and r["lap_id"] == row["lap_id"])
        nominal_ok &= (row["completed"] and baseline["completed"] and row["completion_time_s"] <= 1.01*baseline["completion_time_s"]
                       and row["supervision"]["fallback_fraction"] <= .05
                       and np.mean([v["rmse_m"]**2 for v in row["laps"]])**.5 <= max(.15, 1.1*np.mean([v["rmse_m"]**2 for v in baseline["laps"]])**.5))
    gate = {"physical_cases": len(catalog)*10, "hard_boundary_cases": len(hard),
            "all_guarded_and_transparent_stable": all(r["passed"] for r in guarded+transparent),
            "nominal_noninferiority_false_alarm_passed": bool(nominal_ok),
            "fault_detection_rejection_and_release_passed": bool(faulted and all(r["supervision"]["first_fault_detections"] == 2
                       and r["supervision"]["all_faulted_actions_rejected"] and r["supervision"]["returned_to_learned"] for r in faulted)),
            "hard_abstention_passed": len(hard) == len(catalog)*3 and all(r["abstained"] and r["progress_m"] == 0
                       and len(r["decisions"]) == 1 and r["decisions"][0]["mode"] == "abstain" for r in hard),
            "refinement_passed": all(r["passed"] for r in refinements)}
    gate["passed"] = bool(len(cases) == len(catalog)*13 and all(gate[k] for k in (
        "all_guarded_and_transparent_stable", "nominal_noninferiority_false_alarm_passed", "fault_detection_rejection_and_release_passed", "hard_abstention_passed", "refinement_passed")))
    return {"profile": header["profile"], "detector_sha256": source["content_sha256"], "cases": cases, "refinements": refinements,
            "gate": gate, "production_promotion": False, "continuous_laps": 3}, stored


def run_support(detector: Path, output: Path, progress=None) -> dict:
    if output.exists() or output.resolve().is_relative_to(detector.resolve()):
        raise ValueError("R038 evaluation output must be fresh and outside detector")
    source, _ = load_support_detector(detector)
    output.mkdir(parents=True)
    shutil.copytree(detector, output/"detector")
    result, arrays = compute_support(output/"detector", progress)
    result["independent_audit"] = audit_continuous(result["cases"], arrays, actor="guarded", full_scenario="residual_bias", progress=progress)
    passed = result["profile"] == "research" and result["gate"]["passed"] and result["independent_audit"]["passed"]
    result.update(task_closure_eligible=passed, decision="ACCEPT_CONDITIONAL_SUPPORT_FALLBACK" if passed else "SIMULATED_EXECUTION_ONLY" if result["profile"] == "smoke" else "REJECT_SUPPORT_FALLBACK")
    write_manifest(output/"results.json", result)
    np.savez_compressed(output/"trajectories.npz", **arrays)
    if source["implementation_sha256"] != hashes():
        raise ValueError("R038 source changed during evaluation")
    return finish_run(output, VERSION, {"schema_version": VERSION, "profile": result["profile"], "decision": result["decision"],
                      "task_closure_eligible": passed, "production_promotion": False, "detector_sha256": source["content_sha256"],
                      "implementation_sha256": hashes(), "results_sha256": payload_sha256(result), "commit": commit_id()})


def load_support(root: Path) -> tuple[dict, dict]:
    source, _ = load_support_detector(root/"detector")
    manifest = verify_inventory(root, VERSION)
    summary, result = read_json(root/"summary.json"), read_json(root/"results.json")
    check_seal(summary)
    if (summary["schema_version"] != VERSION or summary["content_sha256"] != manifest["summary_sha256"]
            or summary["detector_sha256"] != source["content_sha256"] or summary["results_sha256"] != payload_sha256(result)
            or summary["implementation_sha256"] != source["implementation_sha256"]
            or result["detector_sha256"] != source["content_sha256"]
            or any(summary[k] != result[k] for k in ("profile", "decision", "task_closure_eligible", "production_promotion"))
            or summary["profile"] != source["profile"] or summary["production_promotion"] is not False):
        raise ValueError("R038 evaluation source/result/truth binding mismatch")
    return summary, result


def verify_support(root: Path, progress=None) -> dict:
    summary, saved = load_support(root)
    result, arrays = compute_support(root/"detector", progress)
    for key, value in result.items():
        compare_numeric(value, saved[key], "R038/"+key)
    maximum = 0.
    with np.load(root/"trajectories.npz", allow_pickle=False) as archive:
        if set(archive.files) != set(arrays):
            raise ValueError("R038 trajectory catalog mismatch")
        for key, value in arrays.items():
            if archive[key].shape != value.shape or not np.allclose(archive[key], value, atol=1e-8, rtol=1e-7):
                raise ValueError("R038 scientific trajectory mismatch: "+key)
            if value.size:
                maximum = max(maximum, float(np.max(abs(archive[key]-value))))
    audit = audit_continuous(result["cases"], arrays, actor="guarded", full_scenario="residual_bias", progress=progress)
    compare_numeric(audit, saved["independent_audit"])
    passed = result["profile"] == "research" and result["gate"]["passed"] and audit["passed"]
    decision = "ACCEPT_CONDITIONAL_SUPPORT_FALLBACK" if passed else "SIMULATED_EXECUTION_ONLY" if result["profile"] == "smoke" else "REJECT_SUPPORT_FALLBACK"
    if saved["task_closure_eligible"] != passed or saved["decision"] != decision:
        raise ValueError("R038 false completion")
    return {"verified": True, "summary_sha256": summary["content_sha256"], "task_closure_eligible": passed,
            "decision": decision, "cases": len(result["cases"]), "maximum_replay_difference": maximum, "independent_audit": audit}
