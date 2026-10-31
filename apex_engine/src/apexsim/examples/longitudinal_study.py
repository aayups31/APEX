"""R030 train/validation freeze followed by separate held-out section evaluation."""
from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

import numpy as np

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.examples.longitudinal_dataset import (
    PROTOCOL,
    check_seal,
    dataset_guard,
    inventory,
    load_sections,
    read_json,
    save_sections,
    sealed_write,
    verify_inventory,
    verify_longitudinal_dataset,
)
from apexsim.examples.longitudinal_dataset import (
    VERSION as DATASET_VERSION,
)
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import longitudinal_calibration, longitudinal_data, longitudinal_scores
from apexsim.research.longitudinal_calibration import (
    ROLLING_PRIOR,
    SpecificPowerDrag,
    fit_candidates,
    fit_cell,
    fit_legacy,
    integrate_speed,
    replay_section,
)
from apexsim.research.longitudinal_data import LongitudinalSection
from apexsim.research.longitudinal_scores import aggregate_errors, error_breakdowns, paired_lap_interval

VERSION = "apex-longitudinal-calibration-v1"
BASELINES = ("constant_speed", "constant_acceleration", "physical_prior", "legacy_huber")


def load_inputs(root: Path) -> tuple[dict, list[LongitudinalSection]]:
    summary = read_json(root/"summary.json")
    check_seal(summary)
    metadata = read_json(root/"section_metadata.json")
    for row in metadata:
        event = row["event_id"]
        assert_development_event(int(event[3:7]), int(event[-2:]), event_id=event)
    if summary["profile"] == "research":
        if not (root/"geometry/manifest.json").is_file():
            raise ValueError("R030 public inputs require frozen native/geometry provenance")
        dataset_guard(root)
        verified = verify_longitudinal_dataset(root)
        if not verified["source_gate_passed"]:
            raise ValueError("R030 public dataset failed frozen source coverage gate")
    elif (summary["profile"] != "smoke" or summary.get("input_truth") != "SIMULATED"
          or any(m.get("fixture_source") != "SIMULATED_NATIVE_SECTIONS" for m in metadata)):
        raise ValueError("R030 invalid research/smoke source classification")
    manifest = verify_inventory(root, DATASET_VERSION+"-manifest")
    if manifest["summary_sha256"] != summary["content_sha256"]:
        raise ValueError("R030 input summary/inventory binding mismatch")
    return summary, load_sections(root)


def _hashes() -> dict:
    return {Path(p).name: file_sha256(p) for p in (__file__, longitudinal_calibration.__file__, longitudinal_data.__file__, longitudinal_scores.__file__)}


def _close(actual, expected, path="R030") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"R030 replay keys mismatch: {path}")
        for key in expected:
            _close(actual[key], expected[key], path+"/"+key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"R030 replay list mismatch: {path}")
        for i, (a, b) in enumerate(zip(actual, expected, strict=True)):
            _close(a, b, path+"/"+str(i))
    elif isinstance(expected, float):
        if not isinstance(actual, (float, int)) or not np.isclose(actual, expected, rtol=1e-6, atol=1e-7):
            raise ValueError(f"R030 replay numerical mismatch: {path}")
    elif actual != expected:
        raise ValueError(f"R030 replay value mismatch: {path}")


def _method_predictions(sections: list[LongitudinalSection], method: str, models: dict,
                        *, max_step_s: float = .05) -> list[np.ndarray]:
    cells = models["legacy"] if method == "legacy_huber" else models["candidates"][method]["cells"] if method in models["candidates"] else None
    return [replay_section(s, method, cells, max_step_s=max_step_s) for s in sections]


def compute_development(sections: list[LongitudinalSection], profile: str) -> tuple[dict, list[dict], dict[str, np.ndarray]]:
    """Fit only training, select only validation; never evaluates test targets."""
    training = [s for s in sections if s.metadata["role"] == "train"]
    validation = [s for s in sections if s.metadata["role"] == "validation"]
    models = {"candidates": fit_candidates(training), "legacy": fit_legacy(training)}
    eligible = [name for name, value in models["candidates"].items() if value["eligible"]]
    if not eligible or not validation:
        raise ValueError("R030 no identifiable candidate or validation source support")
    metrics, arrays = {}, {}
    for method in [*BASELINES, *eligible]:
        predictions = _method_predictions(validation, method, models)
        metrics[method] = aggregate_errors(validation, predictions)
        arrays.update({method+f"__s{i}": value for i, value in enumerate(predictions)})
    selected = min(eligible, key=lambda name: (metrics[name]["rmse_mps"], name != "shared_drag"))
    models.update(selected=selected, validation_metrics=metrics, selection_split="validation", test_outcomes_used=False)
    # Training-only cluster draws; preserve failed/active-bound fits, no test repair.
    rng = np.random.default_rng(3030)
    cells = {cell: [s for s in training if s.cell == cell] for cell in sorted({s.cell for s in training})}
    draws = []
    for _ in range(200 if profile == "research" else 8):
        fitted, failures = {}, {}
        for cell, values in cells.items():
            ids = sorted({s.metadata["lap_id"] for s in values})
            picked = [s for i in rng.integers(0, len(ids), len(ids)) for s in values if s.metadata["lap_id"] == ids[i]]
            try:
                fitted[cell] = fit_cell(picked, selected, bootstrap=True)
            except ValueError as exc:
                failures[cell] = str(exc)
        draws.append({"cells": fitted, "failures": failures})
    models["rolling_prior_sensitivity"] = {}
    for factor in (.5, 1.5):
        current = {}
        for cell, values in cells.items():
            try:
                current[cell] = fit_cell(values, selected, rolling=ROLLING_PRIOR*factor)
            except ValueError as exc:
                current[cell] = {"failure": str(exc)}
        models["rolling_prior_sensitivity"][str(factor)] = current
    return models, draws, arrays


def _commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _save_manifest(output: Path, summary: dict, schema: str) -> None:
    sealed_write(output/"summary.json", summary)
    sealed_write(output/"manifest.json", {"schema_version": schema, "summary_sha256": summary["content_sha256"], "files": inventory(output)})


def fit_longitudinal_study(dataset: Path, output: Path) -> dict:
    """Create an immutable train/validation checkpoint before held-out evaluation."""
    if output.exists():
        raise FileExistsError("R030 development output must be fresh")
    if output.resolve().is_relative_to(dataset.resolve()):
        raise ValueError("R030 development output must be outside input dataset")
    source, sections = load_inputs(dataset)
    before = _hashes()
    models, bootstrap, arrays = compute_development(sections, source["profile"])
    if before != _hashes():
        raise ValueError("R030 implementation changed during training/validation")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(dataset, output/"dataset")
    shutil.copyfile(PROTOCOL, output/"protocol.md")
    write_manifest(output/"models.json", models)
    write_manifest(output/"bootstrap_models.json", bootstrap)
    np.savez_compressed(output/"validation_predictions.npz", **arrays)
    summary = {"schema_version": VERSION+"-development", "profile": source["profile"],
               "dataset_sha256": source["content_sha256"], "models_sha256": payload_sha256(models),
               "bootstrap_sha256": payload_sha256(bootstrap), "selected": models["selected"],
               "validation_rmse_mps": {n: v["rmse_mps"] for n, v in models["validation_metrics"].items()},
               "implementation_sha256": before, "commit": _commit(), "test_outcomes_used": False,
               "promotion": False, "task_closure_eligible": False,
               "environment": {"python": platform.python_version(), "numpy": np.__version__, "scipy": __import__("scipy").__version__}}
    _save_manifest(output, summary, VERSION+"-development-manifest")
    return summary


def verify_longitudinal_development(output: Path) -> dict:
    """Refit the same training clusters; replay validation selection without test scoring."""
    source, sections = load_inputs(output/"dataset")
    manifest = verify_inventory(output, VERSION+"-development-manifest")
    summary = read_json(output/"summary.json")
    check_seal(summary)
    models, draws, arrays = compute_development(sections, source["profile"])
    stored_models = read_json(output/"models.json")
    stored_draws = read_json(output/"bootstrap_models.json")
    _close(stored_models, models)
    _close(stored_draws, draws)
    with np.load(output/"validation_predictions.npz", allow_pickle=False) as stored:
        if set(stored.files) != set(arrays) or any(not np.allclose(stored[k], v, rtol=1e-6, atol=1e-7) for k, v in arrays.items()):
            raise ValueError("R030 validation prediction replay mismatch")
    if (manifest["summary_sha256"] != summary["content_sha256"] or summary["dataset_sha256"] != source["content_sha256"]
            or summary["models_sha256"] != payload_sha256(stored_models) or summary["bootstrap_sha256"] != payload_sha256(stored_draws)
            or summary["selected"] != models["selected"] or summary["test_outcomes_used"] is not False
            or summary["task_closure_eligible"] is not False):
        raise ValueError("R030 development selection/source binding changed")
    return {"verified": True, "selected": models["selected"], "test_outcomes_used": False,
            "summary_sha256": summary["content_sha256"], "profile": source["profile"]}


def make_longitudinal_smoke_dataset(output: Path) -> Path:
    """SIMULATED independent sections, no claim of native full-lap/geometry evidence."""
    if output.exists():
        raise FileExistsError("R030 smoke dataset must be fresh")
    sections = []
    from apexsim.research.longitudinal_data import EVENT_ROLES, EVENT_TRACKS

    for event, role in EVENT_ROLES.items():
        track = EVENT_TRACKS[event]
        for driver in ("4", "44"):
            model = SpecificPowerDrag(780.+(driver == "44")*20+(track == "monza")*15,
                                      .00055+(driver == "44")*.00002, .00015)
            for lap in range(1, 7):
                for part in range(2):
                    z = (lap+part) % 2
                    time = np.arange(17)*.25
                    speed = integrate_speed(40.+lap*3+part*4, time, np.ones(17), np.full(17, z), model.acceleration)
                    absolute = time+lap*100+part*10
                    meta = {"event_id": event, "track_id": track, "driver_id": driver, "role": role,
                            "lap_id": f"{event}_{driver}_{lap}", "section_id": f"{event}_{driver}_{lap}_{part}",
                            "lap_number": lap, "fixture_source": "SIMULATED_NATIVE_SECTIONS"}
                    rows = np.arange(13, dtype=np.int64)+lap*100+part*20+4
                    sections.append(LongitudinalSection(meta, absolute[4:], speed[4:], np.ones(13), np.full(13, z, dtype=np.int64),
                                                        rows, rows.copy(), absolute[:5], speed[:5]))
    output.mkdir(parents=True)
    save_sections(output, sections)
    summary = {"schema_version": DATASET_VERSION, "profile": "smoke", "input_truth": "SIMULATED", "source_gate_passed": True,
               "sections": len(sections), "promotion": False, "fitting_performed": False}
    _save_manifest(output, summary, DATASET_VERSION+"-manifest")
    return output


def compute_evaluation(sections: list[LongitudinalSection], models: dict, draws: list[dict],
                       profile: str) -> tuple[dict, dict[str, np.ndarray]]:
    """Score the frozen selected model once; no fitting/selection on test outcomes."""
    test = [s for s in sections if s.metadata["role"] == "test"]
    if not test:
        raise ValueError("R030 held-out source cohort is empty")
    selected = models["selected"]
    predictions, metrics, arrays = {}, {}, {}
    for method in (*BASELINES, selected):
        values = _method_predictions(test, method, models)
        predictions[method] = values
        metrics[method] = aggregate_errors(test, values)
        arrays.update({method+f"__s{i}": value for i, value in enumerate(values)})
    best = min(BASELINES, key=lambda name: (metrics[name]["rmse_mps"], name))
    paired = paired_lap_interval(metrics[selected], metrics[best], test, resamples=500 if profile == "research" else 20)
    improvements = {name: 1-metrics[selected]["rmse_mps"]/metrics[name]["rmse_mps"]
                    if metrics[name]["rmse_mps"] > 0 else None for name in BASELINES}
    fine = _method_predictions(test, selected, models, max_step_s=.025)
    maximum_refinement = max(float(np.max(abs(a-b))) for a, b in zip(fine, predictions[selected], strict=True))
    arrays.update({f"refined__s{i}": value for i, value in enumerate(fine)})
    bootstrap_predictions = []
    failed_draws = 0
    for draw in draws:
        if draw["failures"]:
            failed_draws += 1
            continue
        try:
            values = [replay_section(s, selected, draw["cells"]) for s in test]
        except ValueError:
            failed_draws += 1
            continue
        bootstrap_predictions.append(values)
    coverage, widths = [], []
    if bootstrap_predictions:
        for i, section in enumerate(test):
            quantiles = np.quantile([p[i] for p in bootstrap_predictions], [.025, .5, .975], axis=0)
            arrays[f"bootstrap_quantiles__s{i}"] = quantiles
            actual = section.speed_mps[1:]
            coverage.extend(((actual >= quantiles[0, 1:]) & (actual <= quantiles[2, 1:])).tolist())
            widths.extend((quantiles[2, 1:]-quantiles[0, 1:]).tolist())
    per_driver = all(metrics[selected]["per_driver"][driver]["mse_m2ps2"] < metrics[baseline]["per_driver"][driver]["mse_m2ps2"]
                     for driver in metrics[selected]["per_driver"] for baseline in ("constant_speed", "physical_prior"))
    parameter_intervals = {}
    for cell in sorted(models["candidates"][selected]["cells"]):
        fitted = [d["cells"][cell] for d in draws if cell in d["cells"]]
        names = list(models["candidates"][selected]["cells"][cell]["parameters"])
        parameter_intervals[cell] = {"valid_cell_fits": len(fitted),
            "interval_95": {name: np.quantile([f["parameters"][name] for f in fitted], [.025, .975]).tolist() for name in names} if fitted else None,
            "active_bound_fraction": float(np.mean([any(f["active_bounds"]) for f in fitted])) if fitted else None}
    gates = {"five_percent_vs_every_baseline": all(v is not None and v >= .05 for v in improvements.values()),
             "paired_best_baseline_interval_negative": paired["interval_95_m2ps2"][1] < 0,
             "each_driver_beats_persistence_and_prior": bool(per_driver),
             "timestep_refinement": maximum_refinement <= .002,
             "no_selected_physical_domain_violations": metrics[selected]["raw_out_of_physical_domain_nodes"] == 0}
    passed = all(gates.values())
    result = {"schema_version": VERSION+"-evaluation", "profile": profile, "classification": "ADAPTATION",
              "selected": selected, "selection_used_test": False, "test_sections": len(test),
              "test_laps": len({s.metadata["lap_id"] for s in test}), "metrics": metrics,
              "breakdowns": {m: error_breakdowns(test, p) for m, p in predictions.items()},
              "best_frozen_baseline": best, "rmse_improvement_vs_baselines": improvements,
              "paired_lap_bootstrap": paired, "maximum_refinement_difference_mps": maximum_refinement,
              "training_parameter_bootstrap": {"draws": len(draws), "valid_draws": len(bootstrap_predictions),
                  "failed_draws": failed_draws, "nominal_parameter_interval": .95,
                  "empirical_test_point_coverage": float(np.mean(coverage)) if coverage else None,
                  "mean_interval_width_mps": float(np.mean(widths)) if widths else None,
                  "interpretation": "PARAMETER_ONLY_DESCRIPTIVE; NOT_CALIBRATED_OBSERVATION_UNCERTAINTY"},
              "parameter_intervals_by_cell": parameter_intervals,
              "initial_speed_outside_training_range": [s.metadata["section_id"] for s in test
                  if not models["candidates"][selected]["cells"][s.cell]["training_speed_range_mps"][0] <= s.speed_mps[0]
                  <= models["candidates"][selected]["cells"][s.cell]["training_speed_range_mps"][1]],
              "gates": gates, "task_closure_eligible": profile == "research" and passed,
              "decision": "ACCEPT_SCOPED_LONGITUDINAL_CALIBRATION" if profile == "research" and passed else
                          "SIMULATED_EXECUTION_ONLY" if profile == "smoke" else "REJECT_FROZEN_LONGITUDINAL_GATES",
              "promotion": False,
              "limitations": ["High-speed full-throttle low-curvature sections only; no brake/lateral/full-lap controller validation",
                              "Effective ratios confound mass/ERS/wind/grade/setup; absolute physical parameters UNKNOWN",
                              "One held-out event; reused development data and supplied offline registered geometry",
                              "Euler interval identification; RK4 held-control section replay without speed resets",
                              "Parameter bootstrap omits source noise/model discrepancy; coverage reported, not guaranteed",
                              "No production or formal R2/R3 maturity promotion"]}
    return result, arrays


def evaluate_longitudinal_study(development: Path, output: Path) -> dict:
    """Evaluate an already frozen train/validation checkpoint on its held-out event."""
    if output.exists():
        raise FileExistsError("R030 evaluation output must be fresh")
    if output.resolve().is_relative_to(development.resolve()):
        raise ValueError("R030 evaluation output must be outside development checkpoint")
    verify_longitudinal_development(development)
    dev = read_json(development/"summary.json")
    source, sections = load_inputs(development/"dataset")
    before = _hashes()
    result, arrays = compute_evaluation(sections, read_json(development/"models.json"),
                                       read_json(development/"bootstrap_models.json"), source["profile"])
    if before != _hashes():
        raise ValueError("R030 implementation changed during held-out evaluation")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(development, output/"development")
    write_manifest(output/"results.json", result)
    np.savez_compressed(output/"predictions.npz", **arrays)
    summary = {"schema_version": VERSION+"-study", "profile": source["profile"],
               "development_sha256": dev["content_sha256"], "dataset_sha256": source["content_sha256"],
               "results_sha256": payload_sha256(result), "selected": result["selected"], "decision": result["decision"],
               "task_closure_eligible": result["task_closure_eligible"], "implementation_sha256": before,
               "promotion": False, "commit": _commit()}
    _save_manifest(output, summary, VERSION+"-study-manifest")
    return summary


def verify_longitudinal_study(output: Path) -> dict:
    """Refit training, replay frozen validation choice and all held-out metrics/arrays."""
    verified = verify_longitudinal_development(output/"development")
    manifest = verify_inventory(output, VERSION+"-study-manifest")
    summary = read_json(output/"summary.json")
    check_seal(summary)
    source, sections = load_inputs(output/"development/dataset")
    result, arrays = compute_evaluation(sections, read_json(output/"development/models.json"),
                                       read_json(output/"development/bootstrap_models.json"), source["profile"])
    stored_result = read_json(output/"results.json")
    _close(stored_result, result)
    maximum = 0.
    with np.load(output/"predictions.npz", allow_pickle=False) as stored:
        if set(stored.files) != set(arrays):
            raise ValueError("R030 held-out raw prediction inventory changed")
        for key, value in arrays.items():
            if stored[key].shape != value.shape or not np.allclose(stored[key], value, rtol=1e-6, atol=1e-7):
                raise ValueError("R030 held-out raw prediction replay mismatch")
            maximum = max(maximum, float(np.max(abs(stored[key]-value))))
    if (manifest["summary_sha256"] != summary["content_sha256"] or summary["development_sha256"] != verified["summary_sha256"]
            or summary["dataset_sha256"] != source["content_sha256"] or summary["selected"] != result["selected"]
            or summary["results_sha256"] != payload_sha256(stored_result) or summary["profile"] != source["profile"]
            or summary["decision"] != result["decision"] or summary["task_closure_eligible"] != result["task_closure_eligible"]
            or summary["promotion"] is not False):
        raise ValueError("R030 held-out source/decision binding replay mismatch")
    return {"verified": True, "decision": result["decision"], "task_closure_eligible": result["task_closure_eligible"],
            "maximum_reload_difference_mps": maximum, "summary_sha256": summary["content_sha256"]}
