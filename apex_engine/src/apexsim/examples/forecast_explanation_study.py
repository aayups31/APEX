"""R027/R028 sealed, portable frozen-model explanation and scenario experiment."""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import numpy as np
import torch

from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import forecast_counterfactuals, forecast_explanations
from apexsim.research.forecast_benchmark import EVENTS, ForecastScaler, ForecastWindows, project_nonnegative
from apexsim.research.forecast_counterfactuals import (
    SCENARIOS,
    TrainingEnvelope,
    build_catalogue,
    counterfactual_result,
    history_violations,
    robust_counterfactual_result,
)
from apexsim.research.forecast_explanations import (
    PLAYERS,
    FrozenForecastPredictor,
    donor_indices,
    guard_origins,
    replace_players,
    select_origins,
    source_key,
    temporal_explanation,
)
from apexsim.research.track_generalization import COHORT, REFERENCE_SEAL

REFERENCE_INVENTORY = "77e0de71402a8ca9a5c9a73afac0540d68e435d6c1211b9eea19b3b595559616"
EVALUATION_SEAL = "f565de0903a71ca19a6dc753fc96ffeb82410d11c00e317bb071ee3fc02bec18"
EVALUATION_INVENTORY = "7584f03bf8d8b54c9b9106451b063a9e2f019f0e00aa26fbc717b6a54a8eaaab"
VERSION = "apex-forecast-explanation-study-v1"
PROTOCOL = Path(__file__).resolve().parents[4]/"research/protocols/FORECAST_EXPLANATIONS.md"


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _check_seal(payload: dict) -> None:
    if payload.get("content_sha256") != payload_sha256({k: v for k, v in payload.items() if k != "content_sha256"}):
        raise ValueError("Explanation content seal mismatch")


def _inventory(output: Path) -> dict:
    return {p.relative_to(output).as_posix(): {"sha256": file_sha256(p), "bytes": p.stat().st_size}
            for p in sorted(output.rglob("*")) if p.is_file() and p != output/"manifest.json"}


def _verify_inventory(output: Path, expected_schema: str) -> dict:
    manifest = _read(output/"manifest.json")
    _check_seal(manifest)
    if manifest.get("schema_version") != expected_schema:
        raise ValueError("Explanation input manifest schema mismatch")
    for name in manifest["files"]:
        path = output/name
        if (not name or "\\" in name or Path(name).is_absolute() or ".." in Path(name).parts
                or path.is_symlink() or not path.resolve().is_relative_to(output.resolve())):
            raise ValueError("Unsafe explanation artifact path")
    if _inventory(output) != manifest["files"]:
        raise ValueError("Explanation artifact inventory/hash mismatch")
    return manifest


def _input_metadata(reference: Path, evaluation: Path, profile: str, *, payloads: bool) -> tuple:
    """Guard canonical/protected origin metadata before hashing/reading any NPZ/model."""
    if profile not in ("research", "smoke"):
        raise ValueError("Invalid explanation study profile")
    ref, ev = _read(reference/"summary.json"), _read(evaluation/"summary.json")
    rm, em = _read(reference/"manifest.json"), _read(evaluation/"manifest.json")
    ref_meta, ev_meta = _read(reference/"window_metadata.json"), _read(evaluation/"window_metadata.json")
    guard_origins(ref_meta)
    guard_origins(ev_meta)
    for item in (ref, ev, rm, em):
        _check_seal(item)
    if (rm["summary_sha256"] != ref["content_sha256"] or em["summary_sha256"] != ev["content_sha256"]
            or ev["reference_summary_sha256"] != ref["content_sha256"]
            or {m["event_id"] for m in ref_meta} != set(EVENTS)
            or {m["event_id"] for m in ev_meta} != set(COHORT)):
        raise ValueError("Explanation frozen source membership/binding mismatch")
    if profile == "research" and (
        ref["content_sha256"] != REFERENCE_SEAL or ev["content_sha256"] != EVALUATION_SEAL
        or rm["content_sha256"] != REFERENCE_INVENTORY or em["content_sha256"] != EVALUATION_INVENTORY
        or ref["profile"] != "research" or ev["profile"] != "research"
    ):
        raise ValueError("Public explanation study requires frozen real source inventories")
    if profile == "smoke" and (ref["profile"] != "smoke" or ev["profile"] != "smoke"):
        raise ValueError("Smoke explanation inputs must be labelled SIMULATED")
    if payloads:
        _verify_inventory(reference, "apex-tyre-forecast-manifest-v1")
        _verify_inventory(evaluation, "apex-track-generalization-manifest-v1")
        for record in ref["records"]:
            name = record["checkpoint"]
            if Path(name).name != name or file_sha256(reference/name) != file_sha256(evaluation/name):
                raise ValueError("Explanation checkpoint bytes differ across source studies")
    return ref, ev, rm, em, ref_meta, ev_meta


def make_cohort(reference: Path, evaluation: Path, profile: str = "research") -> dict:
    """Freeze origin/donor keys using JSON metadata only, before model outcomes."""
    ref, ev, rm, em, ref_meta, ev_meta = _input_metadata(reference, evaluation, profile, payloads=False)
    training = [m for m in ref_meta if m["event_id"] in EVENTS[:2]]
    indices, neighbors, coverage = select_origins(ev_meta, 16 if profile == "research" else 2)
    cases = []
    for index, neighbor in zip(indices, neighbors, strict=True):
        donors = donor_indices(training, ev_meta[index])
        cases.append({"origin_index": index, "nearby_index": neighbor, "origin": ev_meta[index],
                      "nearby_origin": ev_meta[neighbor], "training_donor_indices": donors,
                      "donor_origins": [training[d] for d in donors]})
    cohort = {"schema_version": VERSION+"-cohort", "profile": profile,
              "reference_summary_sha256": ref["content_sha256"], "reference_inventory_sha256": rm["content_sha256"],
              "evaluation_summary_sha256": ev["content_sha256"], "evaluation_inventory_sha256": em["content_sha256"],
              "selection": "source-key SHA256 salt2728; max2/sequence; native spacing8; next-sample neighbor",
              "coverage": coverage, "cases": cases, "outcomes_used": False}
    cohort["content_sha256"] = payload_sha256(cohort)
    return cohort


def freeze_cohort(reference: Path, evaluation: Path, output: Path, profile: str = "research") -> dict:
    """Write a new metadata-only preregistration; no fitting or binary reads."""
    if output.exists():
        raise FileExistsError("Explanation cohort output must be fresh")
    cohort = make_cohort(reference, evaluation, profile)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(output, cohort)
    return {"origins": len(cohort["cases"]), "content_sha256": cohort["content_sha256"], "outcomes_used": False}


def _windows(path: Path, metadata: list[dict], vocabulary: dict) -> ForecastWindows:
    with np.load(path/"windows.npz", allow_pickle=False) as stored:
        result = ForecastWindows(stored["dynamic"], stored["static"], stored["target"], metadata, vocabulary)
    offset = 0
    for field in ("driver_id", "compound", "track_id"):
        values = vocabulary[field]
        block = result.static[:, offset:offset+len(values)]
        if not np.all((block == 0) | (block == 1)) or not np.all(block.sum(axis=1) == 1):
            raise ValueError("Explanation static category encoding is invalid")
        for i, row in enumerate(metadata):
            if field in row:
                expected = values.index(row[field]) if row[field] in values else 0
                if block[i, expected] != 1:
                    raise ValueError("Explanation static identity differs from source metadata")
        offset += len(values)
    for row in metadata:
        if (row["target_native_rows"] != [row["origin_native_row"]+h for h in (1, 3, 5)]
                or not np.isfinite(row["elapsed_horizons_s"]).all() or min(row["elapsed_horizons_s"]) <= 0):
            raise ValueError("Explanation native horizon contract failed")
    return result


def _aggregate(cases: list[dict], metadata: list[dict], training_tracks: list[str]) -> dict:
    """Equal-event local diagnostics; fixed-event sequence bootstrap, not seed resampling."""
    groups = {e: [i for i, m in enumerate(metadata) if m["event_id"] == e] for e in sorted({m["event_id"] for m in metadata})}
    strata = {s: [e for e, indices in groups.items()
                  if (metadata[indices[0]]["track_id"] in training_tracks) == (s == "seen")]
              for s in ("seen", "unseen")}
    result = {}
    for label, events in ({e: [e] for e in groups} | strata).items():
        indices = [i for e in events for i in groups[e]]
        supported = [i for i in indices if "ranking" in cases[i]["explanation"]]
        reliable = [i for i in supported if cases[i]["explanation"]["status"] == "RELIABLE_MODEL_DIAGNOSTIC"]
        cf = [i for i in indices if cases[i]["counterfactual"]["selected_index"] is not None]
        event_means, bootstrap = [], []
        cluster_maps = []
        for event in events:
            local = [i for i in supported if metadata[i]["event_id"] == event]
            if local:
                event_means.append(np.mean([np.mean(cases[i]["explanation"]["importance_kj_by_player_horizon_wheel"], axis=(1, 2)) for i in local], axis=0))
                clusters: dict[str, list[int]] = {}
                for i in local:
                    clusters.setdefault(metadata[i]["sequence_id"], []).append(i)
                cluster_maps.append(list(clusters.values()))
        rng = np.random.default_rng(2728)
        for _ in range(500):
            values = []
            for clusters in cluster_maps:
                selected = [i for c in rng.integers(0, len(clusters), len(clusters)) for i in clusters[c]]
                values.append(np.mean([cases[i]["explanation"]["heldout_top_mean_kj"]-
                                       cases[i]["explanation"]["heldout_random_expectation_kj"] for i in selected]))
            if values:
                bootstrap.append(float(np.mean(values)))
        result[label] = {"events": events, "origins": len(indices), "donor_supported": len(supported),
                         "reliable_explanations": len(reliable), "counterfactual_successes": len(cf),
                         "counterfactual_abstentions": dict(Counter(cases[i]["counterfactual"]["status"] for i in indices if i not in cf)),
                         "speed_only_successes": sum(cases[i]["counterfactual"]["speed_only_index"] is not None for i in indices),
                         "throttle_only_successes": sum(cases[i]["counterfactual"]["throttle_only_index"] is not None for i in indices),
                         "equal_event_importance_kj": np.mean(event_means, axis=0).tolist() if event_means else None,
                         "mean_nearby_top_three_overlap": float(np.mean([cases[i]["explanation"]["nearby_top_three_overlap"] for i in supported])) if supported else None,
                         "mean_donor_top_three_overlap": float(np.mean([cases[i]["explanation"]["donor_top_three_overlap"] for i in supported])) if supported else None,
                         "heldout_top_minus_random_fixed_event_sequence_bootstrap_95_kj": np.quantile(bootstrap, [.025, .975]).tolist() if bootstrap else None}
    return result


def evaluate_study(reference: Path, evaluation: Path, cohort: dict,
                   progress: Callable[[str], None] | None = None) -> tuple[dict, dict[str, dict[str, np.ndarray]]]:
    """Replay the whole experiment from sealed inputs; no output writes or fitting."""
    _check_seal(cohort)
    profile = cohort["profile"]
    ref, ev, _, _, ref_meta, ev_meta = _input_metadata(reference, evaluation, profile, payloads=True)
    if cohort != make_cohort(reference, evaluation, profile):
        raise ValueError("Explanation cohort is not the frozen metadata-only selection")
    windows = _windows(reference, ref_meta, ref["vocabulary"])
    training = windows.subset(EVENTS[:2])
    evaluation_windows = _windows(evaluation, ev_meta, ref["vocabulary"])
    stored_scaler = _read(reference/"scaler.json")
    scaler = ForecastScaler(*(np.array(stored_scaler[k]) for k in ("input_mean", "input_std", "target_mean", "target_std")))
    if scaler.as_dict() != ForecastScaler.fit(training).as_dict():
        raise ValueError("Explanation reference scaler is not training-only")
    support = TrainingEnvelope.fit(training)
    indices = [c["origin_index"] for c in cohort["cases"]]
    neighbors = [c["nearby_index"] for c in cohort["cases"]]
    if not indices:
        raise ValueError("Explanation cohort contains no eligible origins")
    x, nearby = evaluation_windows.dynamic[indices], evaluation_windows.dynamic[neighbors]
    static, metadata = evaluation_windows.static[indices], [ev_meta[i] for i in indices]
    catalogues = [build_catalogue(history, support) for history in x]
    diagnostics, cf_rows, cf_static, cf_slots = [], [], [], []
    for i, (case, history, catalogue) in enumerate(zip(cohort["cases"], x, catalogues, strict=True)):
        donors = training.dynamic[case["training_donor_indices"]]
        violations: Counter = Counter()
        for donor in donors:
            for player in range(12):
                violations.update(history_violations(replace_players(history, donor, (player,))))
        diagnostics.append({"diagnostic_splices": len(donors)*12, "splice_constraint_violations": dict(violations),
                            "donor_tracks": [ref["vocabulary"]["track_id"][int(np.argmax(training.static[d, -len(ref["vocabulary"]["track_id"]):]))]
                                             for d in case["training_donor_indices"]],
                            "source_violations": catalogue.source_violations,
                            "candidate_rejections": dict(Counter(r for reasons in catalogue.reasons for r in reasons)),
                            "candidate_reasons": catalogue.reasons})
        for j in np.flatnonzero(catalogue.valid):
            cf_rows.append(catalogue.histories[j])
            cf_static.append(static[i])
            cf_slots.append((i, j))
    records = [{"name": k, "kind": k} for k in ("persistence", "trend")]+ref["records"]
    with np.load(evaluation/"predictions.npz", allow_pickle=False) as saved:
        original_baselines = {record["name"]: saved[record["name"]+"_raw"][indices] for record in records}
    reports, raw_outputs = {}, {}
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        for record in records:
            name = record["name"]
            if progress:
                progress("evaluating "+name)
            predictor = FrozenForecastPredictor(reference/record["checkpoint"] if "checkpoint" in record else None,
                                                 record, scaler, ref["vocabulary"])
            base_raw = predictor(x, static)
            cf_raw = np.zeros((len(x), len(SCENARIOS), 3, 4))
            if cf_rows:
                predicted = predictor(np.asarray(cf_rows), np.asarray(cf_static))
                for (i, j), value in zip(cf_slots, predicted, strict=True):
                    cf_raw[i, j] = value
            arrays: dict[str, np.ndarray] = {"baseline_raw": base_raw, "counterfactual_raw": cf_raw}
            temporal_arrays: dict[str, list[np.ndarray]] = {}
            supported_indices, cases = [], []
            for i, case in enumerate(cohort["cases"]):
                donors = case["training_donor_indices"]
                if donors:
                    explanation, raw = temporal_explanation(predictor, x[i], static[i], training.dynamic[donors], nearby[i])
                    supported_indices.append(i)
                    for key, values in raw.items():
                        temporal_arrays.setdefault(key, []).append(values)
                    if not np.allclose(base_raw[i], raw["base_raw"][0], rtol=1e-6, atol=1e-7):
                        raise ValueError("Explanation baseline differs across inference batches")
                    # Secondary observed-target diagnostic, after ranking and independent audit.
                    actual = evaluation_windows.target[indices[i]]
                    projected = np.maximum(raw["perturb_raw"], 0)
                    explanation["secondary_loss_increase_kj2_by_player"] = (
                        np.mean((projected-actual)**2, axis=(0, 2, 3))-np.mean((np.maximum(base_raw[i], 0)-actual)**2)
                    ).tolist()
                else:
                    explanation = {"status": "ABSTAIN_DONOR_SUPPORT"}
                result = counterfactual_result(catalogues[i], cf_raw[i], base_raw[i])
                cases.append({"origin_key": list(source_key(case["origin"])),
                              "explanation": explanation, "counterfactual": result})
            for key, values in temporal_arrays.items():
                arrays["temporal_"+key] = np.stack(values)
            arrays["temporal_origin_indices"] = np.array(supported_indices, dtype=np.int64)
            valid_cf = np.array([cf_raw[i, j] for i, j in cf_slots])
            all_raw = np.concatenate((base_raw.ravel(), valid_cf.ravel()))
            _, projection = project_nonnegative(all_raw)
            reports[name] = {"kind": record["kind"], "cases": cases, "raw_output_projection": projection,
                             "maximum_baseline_difference_to_original_r026_kj": float(np.max(abs(base_raw-original_baselines[name]))),
                             "inference_accumulation": "FP64_FIXED_ROW_EINSUM" if record["kind"] in ("linear", "ridge") else
                                                       "FP64_NEURAL_UNCHANGED_FROZEN_WEIGHTS" if record["kind"] in ("gru", "lstm", "tft") else "FROZEN_NATIVE_MODEL",
                             "aggregates": _aggregate(cases, metadata, ref["vocabulary"]["track_id"])}
            raw_outputs[name] = arrays
    finally:
        torch.set_num_threads(old_threads)
    # One shared scenario must cross every primary seed, rather than an ensemble mean.
    primary = [r["name"] for r in ref["records"] if r["kind"] == ref["validation_selected_family"]]
    robust = [robust_counterfactual_result(catalogues[i],
              np.stack([raw_outputs[name]["counterfactual_raw"][i] for name in primary]),
              np.stack([raw_outputs[name]["baseline_raw"][i] for name in primary])) for i in range(len(x))]
    seed_stability = {}
    for kind in ref["models_requested"]:
        names = [r["name"] for r in ref["records"] if r["kind"] == kind]
        if len(names) == 2:
            overlap = []
            for i in range(len(x)):
                a, b = (reports[name]["cases"][i]["explanation"] for name in names)
                if "ranking" in a and "ranking" in b:
                    overlap.append(len(set(a["ranking"][:3]) & set(b["ranking"][:3]))/3)
            seed_stability[kind] = {"paired_origins": len(overlap), "mean_top_three_overlap": float(np.mean(overlap)) if overlap else None}
    useful = {}
    for stratum in ("seen", "unseen"):
        selected = [i for i, m in enumerate(metadata)
                    if (m["track_id"] in ref["vocabulary"]["track_id"]) == (stratum == "seen")]
        useful[stratum] = {"robust_primary_counterfactuals": sum(robust[i]["selected_index"] is not None for i in selected),
                           "reliable_primary_explanations": sum(reports[name]["cases"][i]["explanation"]["status"] == "RELIABLE_MODEL_DIAGNOSTIC"
                                                                for name in primary for i in selected)}
    coverage = cohort["coverage"]
    coverage_pass = (len(indices) >= 64 and len(coverage) == 8 and all(c["selected"] >= 8 for c in coverage.values()))
    useful_pass = all(min(values.values()) > 0 for values in useful.values())
    result = {"schema_version": VERSION, "profile": profile, "classification": "ADAPTATION",
              "target_quality": "PROXY_NOT_MEASURED", "promotion": False,
              "input_truth": ev.get("input_truth", "UNKNOWN"),
              "cohort_sha256": cohort["content_sha256"], "origins": len(indices), "models": reports,
              "source_and_scenario_diagnostics": diagnostics,
              "training_marginal_envelope": {"minimum": support.minimum.tolist(), "maximum": support.maximum.tolist()},
              "players": [{"name": p.name, "start": p.start, "stop": p.stop, "fields": list(p.fields)} for p in PLAYERS],
              "scenarios": [list(s) for s in SCENARIOS], "selected_family": ref["validation_selected_family"],
              "primary_frozen_seeds": primary, "robust_primary_counterfactuals": robust,
              "same_family_seed_stability": seed_stability, "useful_evidence_by_stratum": useful,
              "history_span_s_quantiles": np.quantile(x[:, 1:, 8].sum(axis=1), [0, .5, .95, 1]).tolist(),
              "elapsed_horizon_s_quantiles": np.quantile([m["elapsed_horizons_s"] for m in metadata], [0, .5, .95, 1], axis=0).tolist(),
              "gates": {"public_cohort_coverage": coverage_pass, "primary_useful_evidence": useful_pass,
                        "all_emitted_counterfactuals_audited": True, "all_explanations_independently_audited": True},
              "task_closure_eligible": profile == "research" and coverage_pass and useful_pass,
              "decision": "ACCEPT_SCOPED_PUBLIC_MODEL_EXPLANATIONS" if profile == "research" and coverage_pass and useful_pass
                          else "SIMULATED_EXECUTION_ONLY" if profile == "smoke" else "REJECT_FROZEN_EXPLANATION_GATES",
              "limitations": ["Public wheel-energy PROXY; no measured wheel targets or causal vehicle intervention",
                              "Temporal splices can violate coupled equations; diagnostic reliability is not physical feasibility",
                              "Feasibility conditional on kinematic/proxy priors and training marginal bounds only",
                              "Actuator/friction-circle/complete path/thermal/race-control feasibility UNKNOWN",
                              "Reused four development events; fixed-event bootstrap is not a population guarantee",
                              "Finite55-candidate optimality only; no strategy or production promotion"]}
    return result, raw_outputs


def _implementation_hashes() -> dict:
    return {Path(p).name: file_sha256(p) for p in (__file__, forecast_explanations.__file__, forecast_counterfactuals.__file__)}


def run_explanation_study(reference: Path, evaluation: Path, cohort_path: Path, output: Path,
                          progress: Callable[[str], None] | None = None) -> dict:
    """Snapshot fixed sources, evaluate frozen models, seal all artifacts; never overwrite."""
    if output.exists():
        raise FileExistsError("Explanation study output must be fresh")
    if any(output.resolve().is_relative_to(p.resolve()) for p in (reference, evaluation)):
        raise ValueError("Explanation output must be outside input sources")
    cohort = _read(cohort_path)
    started = time.perf_counter()
    _check_seal(cohort)
    _input_metadata(reference, evaluation, cohort["profile"], payloads=True)
    if cohort != make_cohort(reference, evaluation, cohort["profile"]):
        raise ValueError("Explanation cohort differs from preregistration")
    before = _implementation_hashes()
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(reference, output/"reference")
    shutil.copytree(evaluation, output/"evaluation")
    shutil.copyfile(cohort_path, output/"cohort.json")
    shutil.copyfile(PROTOCOL, output/"protocol.md")
    shutil.copyfile(PROTOCOL.with_name("FORECAST_EXPLANATIONS_NUMERICS.md"), output/"numerical-correction.md")
    result, raw = evaluate_study(output/"reference", output/"evaluation", cohort, progress)
    if before != _implementation_hashes():
        raise ValueError("Explanation implementation changed during evaluation")
    for name, arrays in raw.items():
        np.savez_compressed(output/(name+".npz"), **arrays)
    write_manifest(output/"results.json", result)
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    summary = {"schema_version": VERSION+"-summary", "profile": cohort["profile"],
               "decision": result["decision"], "task_closure_eligible": result["task_closure_eligible"],
               "origins": result["origins"], "methods": list(raw), "cohort_sha256": cohort["content_sha256"],
               "results_sha256": payload_sha256(result), "protocol_file_sha256": file_sha256(output/"protocol.md"),
               "implementation_sha256": before, "commit": commit,
               "evaluation_seconds": time.perf_counter()-started,
               "environment": {"python": platform.python_version(), "numpy": np.__version__, "torch": torch.__version__, "cpu_threads": 1},
               "promotion": False, "target_quality": "PROXY_NOT_MEASURED"}
    summary["content_sha256"] = payload_sha256(summary)
    write_manifest(output/"summary.json", summary)
    manifest = {"schema_version": VERSION+"-manifest", "summary_sha256": summary["content_sha256"], "files": _inventory(output)}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(output/"manifest.json", manifest)
    return summary


def _compare_payload(actual, expected, path: str = "results") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"Explanation replay keys mismatch: {path}")
        for key in expected:
            _compare_payload(actual[key], expected[key], path+"/"+key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"Explanation replay list mismatch: {path}")
        for i, (a, b) in enumerate(zip(actual, expected, strict=True)):
            _compare_payload(a, b, path+"/"+str(i))
    elif isinstance(expected, float):
        if not isinstance(actual, (float, int)) or not np.isclose(actual, expected, rtol=1e-6, atol=1e-7):
            raise ValueError(f"Explanation replay numeric mismatch: {path}")
    elif actual != expected:
        raise ValueError(f"Explanation replay value mismatch: {path}")


def verify_explanation_study(output: Path, progress: Callable[[str], None] | None = None) -> dict:
    """Reload every checkpoint; regenerate donors, scenarios, faithfulness and decisions."""
    cohort = _read(output/"cohort.json")
    # Protected source metadata is checked before any binary hash or payload read.
    _input_metadata(output/"reference", output/"evaluation", cohort["profile"], payloads=False)
    manifest = _verify_inventory(output, VERSION+"-manifest")
    summary, stored = _read(output/"summary.json"), _read(output/"results.json")
    _check_seal(summary)
    if (manifest["summary_sha256"] != summary["content_sha256"]
            or payload_sha256(stored) != summary["results_sha256"]
            or summary["cohort_sha256"] != cohort["content_sha256"]
            or summary["profile"] != cohort["profile"]
            or summary["protocol_file_sha256"] != file_sha256(output/"protocol.md")):
        raise ValueError("Explanation summary/cohort/results binding mismatch")
    replay, arrays = evaluate_study(output/"reference", output/"evaluation", cohort, progress)
    _compare_payload(stored, replay)
    maximum = 0.
    for name, values in arrays.items():
        with np.load(output/(name+".npz"), allow_pickle=False) as saved:
            if set(saved.files) != set(values):
                raise ValueError("Explanation raw inference inventory changed")
            for key, value in values.items():
                if saved[key].shape != value.shape or not np.allclose(saved[key], value, rtol=1e-6, atol=1e-7):
                    raise ValueError("Explanation checkpoint/raw diagnostic replay mismatch")
                if value.size:
                    maximum = max(maximum, float(np.max(abs(saved[key]-value))))
    if (summary["decision"] != replay["decision"] or summary["methods"] != list(arrays)
            or summary["task_closure_eligible"] != replay["task_closure_eligible"] or summary["promotion"] is not False):
        raise ValueError("Explanation closure decision replay mismatch")
    return {"verified": True, "decision": replay["decision"], "task_closure_eligible": replay["task_closure_eligible"],
            "methods": len(arrays), "origins": replay["origins"], "maximum_reload_difference_kj": maximum,
            "summary_sha256": summary["content_sha256"]}
