"""R021/R022 immutable tyre-pace study; all public inputs are development-only."""
from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict
from pathlib import Path

import numpy as np

from apexsim.data import tyre_dataset
from apexsim.data.tyre_dataset import FuelPrior
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import hierarchical_tyre, tyre_evaluation, tyre_pace
from apexsim.research.hierarchical_tyre import (
    HierarchicalTyreModel,
    HierarchySettings,
    apply_calibration,
    calibration_scales,
)
from apexsim.research.tyre_evaluation import coverage_bootstrap, grouped_metrics
from apexsim.research.tyre_pace import fit_pace, forecast_rows

EVENTS = ("F1_2024_R01", "F1_2024_R03", "F1_2024_R06", "F1_2024_R16", "F1_2024_R18")


def evaluate_tyre_study(dataset: dict, settings: HierarchySettings | None = None) -> tuple[dict, dict, HierarchicalTyreModel]:
    """Run fixed whole-event origins and separate train/calibration/test hierarchy."""
    segments = dataset["segments"]
    tyre_pace.validate_segments(segments)
    events = sorted({s["event_id"] for s in segments}, key=lambda e: min(s["race_date"] for s in segments if s["event_id"] == e))
    if tuple(events) != EVENTS:
        raise ValueError("Tyre study requires the five preregistered event identities/order")
    fits, rolling = [], []
    for end in range(1, len(EVENTS)):
        train = [s for s in segments if s["event_id"] in EVENTS[:end]]
        evaluate = [s for s in segments if s["event_id"] == EVENTS[end]]
        params, report = fit_pace(train)
        fits.append({"evaluation_event": EVENTS[end], **report})
        for method in ("state_space", "persistence", "last_three_trend"):
            rows = forecast_rows(evaluate, params, method)
            rolling.extend({**r, "training_events": list(EVENTS[:end])} for r in rows)
    train = [s for s in segments if s["event_id"] in EVENTS[:2]]
    noise, noise_report = fit_pace(train)
    hierarchy = HierarchicalTyreModel(noise, settings)
    posterior = hierarchy.fit(train)
    calibration = hierarchy.forecast([s for s in segments if s["event_id"] == EVENTS[2]])
    scales = calibration_scales(calibration)
    test = hierarchy.forecast([s for s in segments if s["event_id"] in EVENTS[3:]])
    test = apply_calibration(test, scales)
    by_horizon = grouped_metrics(test, ("horizon",))
    calibration_gate = all(r["predictions"] >= 100 and .80 <= r["calibrated_90_coverage"] <= .98
                           and 0 < r["calibrated_90_mean_width_s"] <= 20 for r in by_horizon)
    summary = {"schema_version": "apex-tyre-degradation-study-v1", "classification": "ADAPTATION",
               "research_foundation_maturity": "R1", "production_kernel_maturity": "R0", "promotion_recommended": False,
               "R021_passed": bool(rolling), "R022_passed": bool(calibration_gate and posterior["max_supported_split_rhat"] <= 1.10),
               "fuel_prior": dataset["fuel_prior"], "input_dataset_sha256": dataset["content_sha256"],
               "rolling_metrics": grouped_metrics(rolling, ("method", "horizon")),
               "rolling_event_metrics": grouped_metrics(rolling, ("method", "event_id", "horizon")),
               "rolling_compound_metrics": grouped_metrics(rolling, ("method", "compound", "horizon")),
               "hierarchical_posterior": posterior, "hierarchical_noise_fit": noise_report,
               "hierarchical_split": {"train": list(EVENTS[:2]), "calibration": [EVENTS[2]], "test": list(EVENTS[3:])},
               "calibration_scales": scales, "calibration_metrics": grouped_metrics(apply_calibration(calibration, scales), ("horizon",)),
               "hierarchical_test_metrics": by_horizon, "hierarchical_event_metrics": grouped_metrics(test, ("event_id", "horizon")),
               "hierarchical_compound_metrics": grouped_metrics(test, ("compound", "horizon")),
               "coverage_uncertainty": [{"horizon": h, **coverage_bootstrap([r for r in test if r["horizon"] == h])} for h in (1, 3, 5)],
               "limitations": ["Fuel mass is a fixed prior; inferred pace drift is not measured physical wear.",
                               "Eligibility is a retrospective clean-lap target mask, not an online quality forecast.",
                               "Five development events only; permanent benchmark unused.",
                               "Conditional Bayesian hierarchy uses plug-in training Q/R; global posterior is fixed during local state filtering.",
                               "Validation-calibrated prediction intervals are separate from unmodified Bayesian parameter intervals.",
                               "No production promotion, private-data reproduction or full R2 simulator accuracy claim."]}
    artifacts = {"rolling_fits": fits, "rolling_predictions": rolling, "hierarchical_calibration_predictions": calibration,
                 "hierarchical_test_predictions": test}
    return summary, artifacts, hierarchy


def run_tyre_degradation_demo(dataset_path: Path, output: Path, *, profile: str = "research") -> dict:
    if output.exists():
        raise FileExistsError(f"Tyre study output already exists: {output}")
    if profile not in ("research", "smoke"):
        raise ValueError("Tyre study profile must be research or smoke")
    if output.resolve() == dataset_path.resolve() or output.resolve().is_relative_to(dataset_path.resolve()):
        raise ValueError("Tyre output must not overwrite input")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if dataset.get("content_sha256") != payload_sha256({k: v for k, v in dataset.items() if k != "content_sha256"}):
        raise ValueError("Tyre dataset content hash mismatch")
    if dataset.get("schema_version") != "apex-tyre-pace-dataset-v1" or dataset["fuel_prior"] != asdict(FuelPrior()):
        raise ValueError("Unsupported tyre study schema/primary fuel prior")
    if profile == "research" and (dataset.get("truth_labels", {}).get("lap_values") != "FASTF1_PARSED_SOURCE; upstream reconstruction possible"
                                  or {s["event_id"] for s in dataset.get("sources", [])} != set(EVENTS)):
        raise ValueError("Research closure requires five source-bound public race archives")
    source_paths = [Path(m.__file__) for m in (tyre_dataset, tyre_pace, hierarchical_tyre, tyre_evaluation)] + [Path(__file__), dataset_path]
    before = {str(p): file_sha256(p) for p in source_paths}
    settings = HierarchySettings() if profile == "research" else HierarchySettings(warmup=100, draws=200)
    summary, artifacts, hierarchy = evaluate_tyre_study(dataset, settings)
    sensitivities = []
    if profile == "research":
        for coefficient in (.020, .040):
            copy = json.loads(json.dumps(dataset))
            prior = FuelPrior(time_s_per_kg=coefficient)
            for segment in copy["segments"]:
                for row in segment["rows"]:
                    row["corrected_s"] = row["observed_s"] - prior.effect(row["lap"])
            # Sensitivity concerns R021 only; never select or retrain the hierarchy on test outcomes.
            for end in range(1, len(EVENTS)):
                params, report = fit_pace([s for s in copy["segments"] if s["event_id"] in EVENTS[:end]])
                rows = forecast_rows([s for s in copy["segments"] if s["event_id"] == EVENTS[end]], params)
                sensitivities.append({"time_s_per_kg": coefficient, "evaluation_event": EVENTS[end],
                                      "fit": report, "metrics": grouped_metrics(rows, ("horizon",))})
    summary["fuel_sensitivity"] = sensitivities
    summary["profile"] = profile
    summary["acceptance_scope"] = "frozen public-data study" if profile == "research" else "execution smoke only; not task closure evidence"
    summary["task_closure_eligible"] = bool(profile == "research" and summary["R021_passed"] and summary["R022_passed"])
    if before != {str(p): file_sha256(p) for p in source_paths}:
        raise ValueError("Tyre study inputs/code changed during evaluation")
    summary["implementation_sha256"] = {p.name: file_sha256(p) for p in source_paths[:-1]}
    summary["runtime"] = {"python": platform.python_version(), "numpy": np.__version__,
                          "scipy": __import__("scipy").__version__, "thread_limits": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")}}
    summary["content_sha256"] = payload_sha256(summary)
    output.mkdir(parents=True, exist_ok=False)
    write_manifest(output / "dataset.json", dataset)
    for name, value in artifacts.items():
        write_manifest(output / f"{name}.json", value)
    np.savez(output / "hierarchical_draws.npz", parameters=hierarchy.chains, group_variances=hierarchy.variance_chains)
    write_manifest(output / "config.json", {"fuel_prior": asdict(FuelPrior()), "events": list(EVENTS), "sampler": asdict(hierarchy.settings)})
    write_manifest(output / "summary.json", summary)
    manifest = {"schema_version": "apex-tyre-degradation-manifest-v1", "summary_sha256": summary["content_sha256"],
                "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(output / "manifest.json", manifest)
    return summary


def make_tyre_smoke_dataset() -> dict:
    """Small SIMULATED fixture for offline CLI/artifact CI, never public-data evidence."""
    rng = np.random.default_rng(2021)
    segments = []
    prior = FuelPrior()
    for event_index, event_id in enumerate(EVENTS):
        for driver in ("4", "44"):
            for compound_index, compound in enumerate(tyre_pace.DRY):
                values = 90 + (.06 + .01 * compound_index) * np.arange(14) + rng.normal(0, .08, 14)
                segments.append({"segment_id": f"{event_id}_{driver}_{compound}", "event_id": event_id,
                                 "season": 2024, "round_number": int(event_id[-2:]), "race_date": f"2024-{event_index + 1:02d}-01",
                                 "track_id": f"simulated_{event_index}", "driver": driver, "compound": compound, "stint": 1,
                                 "rows": [{"lap": i + 1, "corrected_s": float(value), "fuel_effect_s": prior.effect(i + 1),
                                           "observed_s": float(value + prior.effect(i + 1))} for i, value in enumerate(values)]})
    dataset = {"schema_version": "apex-tyre-pace-dataset-v1", "segments": segments, "sources": [],
               "fuel_prior": asdict(prior), "truth_labels": {"lap_values": "SIMULATED", "fuel": "PRIOR"}}
    dataset["content_sha256"] = payload_sha256(dataset)
    return dataset


def verify_tyre_study(output: Path) -> dict:
    """Reload completion manifest, sealed JSON and all-chain weights without refitting."""
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "apex-tyre-degradation-manifest-v1" or manifest.get("content_sha256") != payload_sha256(
            {k: v for k, v in manifest.items() if k != "content_sha256"}):
        raise ValueError("Tyre study manifest hash/schema mismatch")
    required = {"dataset.json", "rolling_fits.json", "rolling_predictions.json", "hierarchical_calibration_predictions.json",
                "hierarchical_test_predictions.json", "hierarchical_draws.npz", "config.json", "summary.json"}
    if set(manifest["files"]) != required:
        raise ValueError("Tyre study artifact membership mismatch")
    for name, record in manifest["files"].items():
        path = output / name
        if not path.is_file() or path.stat().st_size != record["bytes"] or file_sha256(path) != record["sha256"]:
            raise ValueError(f"Tyre study artifact hash mismatch: {name}")
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    dataset = json.loads((output / "dataset.json").read_text(encoding="utf-8"))
    for value in (summary, dataset):
        if value["content_sha256"] != payload_sha256({k: v for k, v in value.items() if k != "content_sha256"}):
            raise ValueError("Tyre study payload hash mismatch")
    if summary["content_sha256"] != manifest["summary_sha256"] or summary["input_dataset_sha256"] != dataset["content_sha256"]:
        raise ValueError("Tyre study input/summary binding mismatch")
    posterior = summary["hierarchical_posterior"]
    settings = posterior["settings"]
    shape = (len(settings["seeds"]), settings["draws"])
    with np.load(output / "hierarchical_draws.npz", allow_pickle=False) as weights:
        parameters, variances = weights["parameters"], weights["group_variances"]
        if (parameters.shape != (*shape, len(posterior["parameter_summary"])) or variances.shape != (*shape, 3)
                or not np.isfinite(parameters).all() or not np.isfinite(variances).all() or np.any(variances <= 0)):
            raise ValueError("Invalid tyre posterior artifact")
    return {"verified": True, "profile": summary["profile"], "task_closure_eligible": summary["task_closure_eligible"],
            "content_sha256": summary["content_sha256"], "posterior_shape": list(parameters.shape), "files": len(required)}
