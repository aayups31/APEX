"""R026 frozen-checkpoint inference on new, source-bound development events."""
from __future__ import annotations

import json
import platform
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.jolpica import verify_jolpica_archive
from apexsim.data.tyre_dataset import build_tyre_dataset
from apexsim.examples.tyre_forecast_benchmark import (
    checkpoint_prediction,
    detailed_metrics,
    verify_forecast_benchmark,
)
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import forecast_benchmark, temporal_fusion, track_generalization
from apexsim.research.forecast_benchmark import (
    ForecastScaler,
    ForecastWindows,
    build_forecast_windows,
    neural_model,
    neural_quantile_prediction,
    project_nonnegative,
    transparent_prediction,
)
from apexsim.research.track_generalization import (
    CALENDAR_SEAL,
    COHORT,
    EVENTS,
    PROXY_CONFIG_SEAL,
    REFERENCE_SEAL,
    classify_tracks,
    frozen_family_decision,
    generalization_scores,
)
from apexsim.research.tyre_energy_dataset import (
    build_tyre_energy_dataset,
    read_tyre_energy_dataset,
    validate_samples,
)


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_generalization_dataset(archives: list[Path], calendar: Path, output: Path) -> dict:
    """Same public proxy physics/priors; only explicit event membership is extended."""
    if output.exists() or output.with_name(output.name+"-eligible.json").exists():
        raise FileExistsError("Generalization dataset and mask outputs must be fresh")
    catalog = verify_jolpica_archive(calendar)
    if catalog["content_sha256"] != CALENDAR_SEAL:
        raise ValueError("R026 requires the frozen 2023 calendar")
    events = {e["event_id"]: e for e in _read(calendar/"events.json")["events"]}
    seen = set()
    for archive in archives:
        manifest = _read(archive/"manifest.json")
        query = manifest["query"]
        event = f"F1_{query['year']}_R{query['round_number']:02d}"
        assert_development_event(query["year"], query["round_number"], event_id=event)
        if event not in COHORT or event in seen or query["session"] != "R":
            raise ValueError("R026 requires unique exact preregistered races")
        identity = manifest["identity"]
        expected = events[event]
        if (expected["circuit_id"] != COHORT[event] or identity["event_name"] != expected["race_name"]
                or not identity["api_path"].startswith(f"/static/2023/{expected['race_date']}_")):
            raise ValueError("R026 calendar/archive circuit/date identity mismatch")
        seen.add(event)
    if seen != set(EVENTS):
        raise ValueError("R026 requires all four preregistered races")
    mask = build_tyre_dataset(archives, calendar)
    if any(s["track_id"] != COHORT[s["event_id"]] for s in mask["segments"]):
        raise ValueError("R026 eligible source circuit mismatch")
    path = output.with_name(output.name+"-eligible.json")
    write_manifest(path, mask)
    return build_tyre_energy_dataset(archives, path, output, expected_events=EVENTS)


def _tracks(reference: dict, profile: str) -> dict:
    if profile == "research":
        if set(reference["vocabulary"]["track_id"]) != {"UNKNOWN", "bahrain", "albert_park"}:
            raise ValueError("Frozen reference training track membership changed")
        return COHORT
    training = [t for t in reference["vocabulary"]["track_id"] if t != "UNKNOWN"]
    if len(training) != 2:
        raise ValueError("Generalization smoke requires two reference training circuits")
    return dict(zip(EVENTS, (*training, "SIM_UNSEEN_MONZA", "SIM_UNSEEN_SINGAPORE"), strict=True))


def _family_members(reference: dict) -> dict:
    return {kind: [r["name"] for r in reference["records"] if r["kind"] == kind] for kind in reference["models_requested"]}


def _interval_metrics(actual: np.ndarray, quantiles: np.ndarray, metadata: list[dict], strata: dict) -> dict:
    reports = {}
    for stratum, events in strata.items():
        selected = np.array([m["event_id"] in events for m in metadata])
        y, q = actual[selected], quantiles[selected]
        reports[stratum] = {"nominal_coverage": .8, "coverage": float(np.mean((y >= q[..., 0]) & (y <= q[..., 2]))),
                            "mean_width_kj": float(np.mean(q[..., 2]-q[..., 0])), "calibrated": False}
    return reports


def run_track_generalization(dataset: Path, reference_path: Path, output: Path, profile: str = "research") -> dict:
    if output.exists():
        raise FileExistsError("Generalization output exists")
    if profile not in ("research", "smoke") or any(output.resolve().is_relative_to(p.resolve()) for p in (dataset, reference_path)):
        raise ValueError("Invalid generalization profile/output boundary")
    quality = _read(dataset/"quality.json")
    source_events = []
    for source in quality["sources"]:
        q = source["query"]
        assert_development_event(q["year"], q["round_number"], event_id=source["event_id"])
        source_events.append(source["event_id"])
    if set(source_events) != set(EVENTS) or len(source_events) != len(EVENTS):
        raise ValueError("R026 source cohort is not the exact preregistered membership")
    verify_forecast_benchmark(reference_path)
    reference = _read(reference_path/"summary.json")
    if profile == "research" and reference["content_sha256"] != REFERENCE_SEAL:
        raise ValueError("R026 research requires frozen public R025 reference weights")
    table, input_manifest = read_tyre_energy_dataset(dataset)
    if profile == "research":
        mask = _read(dataset/"eligible_input.json")
        if mask.get("calendar_sha256") != CALENDAR_SEAL or quality.get("input_truth") == "SIMULATED":
            raise ValueError("R026 public dataset requires the frozen real calendar/eligibility lineage")
        if file_sha256(dataset/"config.json") != PROXY_CONFIG_SEAL:
            raise ValueError("R026 proxy priors/field contracts differ from frozen R024")
    expected_tracks = _tracks(reference, profile)
    frame = table.to_pandas()
    for event in EVENTS:
        tracks = set(frame.loc[frame.event_id == event, "track_id"])
        if tracks != {expected_tracks[event]}:
            raise ValueError("R026 dataset circuit identity disagrees with cohort")
    if set(frame.driver_id) != {"4", "44"}:
        raise ValueError("R026 fixed driver cohort is incomplete")
    windows = build_forecast_windows(frame, expected_events=EVENTS, vocabulary=reference["vocabulary"])
    counts = {event: sum(m["event_id"] == event for m in windows.metadata) for event in EVENTS}
    if profile == "research" and min(counts.values()) < 1000:
        raise ValueError("R026 requires at least1000 complete origins per event")
    keys = [(m["event_id"], m["driver_id"], m["sequence_id"], m["origin_native_row"]) for m in windows.metadata]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate R026 evaluation origin identity")
    source_files = [dataset/"manifest.json", dataset/"samples.parquet", *sorted(reference_path.iterdir()),
                    Path(__file__), Path(forecast_benchmark.__file__), Path(temporal_fusion.__file__), Path(track_generalization.__file__)]
    before = {str(p): file_sha256(p) for p in source_files}
    scaler_payload = _read(reference_path/"scaler.json")
    scaler = ForecastScaler(*(np.array(scaler_payload[k]) for k in ("input_mean", "input_std", "target_mean", "target_std")))
    strata = classify_tracks(windows.metadata, reference["vocabulary"]["track_id"])
    predictions, saved, diagnostics, quantile_metrics = {}, {}, {}, {}
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        for method in ("persistence", "trend"):
            raw = transparent_prediction(windows, method)
            projected, correction = project_nonnegative(raw)
            predictions[method] = projected
            saved.update({method: projected, method+"_raw": raw})
            diagnostics[method] = {"projection": correction, "raw": detailed_metrics(windows.target, raw, windows.metadata),
                                   "projected": detailed_metrics(windows.target, projected, windows.metadata)}
        for record in reference["records"]:
            name = record["name"]
            raw = checkpoint_prediction(reference_path/record["checkpoint"], record, windows, scaler)
            projected, correction = project_nonnegative(raw)
            predictions[name] = projected
            saved.update({name: projected, name+"_raw": raw})
            diagnostics[name] = {"projection": correction, "raw": detailed_metrics(windows.target, raw, windows.metadata),
                                "projected": detailed_metrics(windows.target, projected, windows.metadata)}
            if record["kind"] == "tft":
                with torch.random.fork_rng(devices=[]):
                    model = neural_model("tft", windows.static_widths, record["hidden"])
                    model.load_state_dict(torch.load(reference_path/record["checkpoint"], map_location="cpu", weights_only=True))
                quantiles = neural_quantile_prediction(model, windows, scaler)
                q_projected, q_correction = project_nonnegative(quantiles)
                saved.update({name+"_quantiles_raw": quantiles, name+"_quantiles_projected": q_projected})
                quantile_metrics[name] = {"intervals": _interval_metrics(windows.target, q_projected, windows.metadata, strata),
                                          "projection": q_correction}
    finally:
        torch.set_num_threads(old_threads)
    scores = generalization_scores(windows.target, predictions, windows.metadata, reference["vocabulary"]["track_id"], _family_members(reference))
    if before != {str(p): file_sha256(p) for p in source_files}:
        raise ValueError("Generalization reference/data/code changed during inference")
    summary = {"schema_version": "apex-track-generalization-v1", "profile": profile, "classification": "ADAPTATION",
               "R026_evaluation_complete": True, "task_closure_eligible": profile == "research", "promotion": False,
               "target_quality": "PROXY_NOT_MEASURED", "input_truth": quality.get("input_truth", "FASTF1_PARSED_SOURCE; upstream reconstruction possible"),
               "input_dataset_sha256": input_manifest["content_sha256"], "reference_summary_sha256": reference["content_sha256"],
               "selected_family": reference["validation_selected_family"], "frozen_family_decision": frozen_family_decision(scores, reference["validation_selected_family"]),
               "models_requested": reference["models_requested"], "checkpoint_count": len(reference["records"]),
               "cohort_tracks": expected_tracks, "origins_per_event": counts, "scores": scores, "diagnostics": diagnostics,
               "tft_uncalibrated_quantiles": quantile_metrics, "history_native_samples": 8, "horizons_native_samples": [1, 3, 5],
               "elapsed_horizon_s_quantiles_by_stratum": {s: np.quantile([m["elapsed_horizons_s"] for m in windows.metadata if m["event_id"] in events], [0, .5, .95, 1], axis=0).tolist() for s, events in strata.items()},
               "environment": {"python": platform.python_version(), "numpy": np.__version__, "torch": torch.__version__, "cpu_threads": 1},
               "implementation_sha256": {p.name: before[str(p)] for p in source_files[-4:]},
               "limitations": ["Retrospective 2024-trained/2023-tested development evaluation; not prospective deployment",
                               "Only two circuits/events per stratum; bootstrap intervals are descriptive, not population guarantees",
                               "Driver/car/layout/regime changes confound causal track novelty interpretation",
                               "R024 energy proxies and fixed priors; no measured wheel targets",
                               "Frozen seeds/configs; no retraining, recalibration, test-driven selection or production promotion"]}
    summary["content_sha256"] = payload_sha256(summary)
    output.mkdir(parents=True, exist_ok=False)
    write_manifest(output/"summary.json", summary)
    write_manifest(output/"window_metadata.json", windows.metadata)
    for source, target in (("summary.json", "reference_summary.json"), ("manifest.json", "reference_manifest.json"), ("scaler.json", "scaler.json")):
        shutil.copyfile(reference_path/source, output/target)
    for record in reference["records"]:
        shutil.copyfile(reference_path/record["checkpoint"], output/record["checkpoint"])
    for source, target in (("manifest.json", "input_manifest.json"), ("quality.json", "input_quality.json"), ("config.json", "input_config.json"), ("eligible_input.json", "eligible_input.json")):
        shutil.copyfile(dataset/source, output/target)
    np.savez_compressed(output/"windows.npz", dynamic=windows.dynamic, static=windows.static, target=windows.target)
    np.savez_compressed(output/"predictions.npz", actual=windows.target, **saved)
    manifest = {"schema_version": "apex-track-generalization-manifest-v1", "summary_sha256": summary["content_sha256"],
                "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(output/"manifest.json", manifest)
    return summary


def verify_track_generalization(output: Path) -> dict:
    """Portable stored-window inference replay; original native sources stay separately sealed."""
    manifest = _read(output/"manifest.json")
    if manifest.get("schema_version") != "apex-track-generalization-manifest-v1" or manifest["content_sha256"] != payload_sha256({k:v for k,v in manifest.items() if k != "content_sha256"}):
        raise ValueError("Generalization manifest hash/schema mismatch")
    if set(manifest["files"]) != {p.name for p in output.iterdir()}-{"manifest.json"}:
        raise ValueError("Generalization artifact inventory mismatch")
    for name, item in manifest["files"].items():
        if Path(name).name != name or file_sha256(output/name) != item["sha256"] or (output/name).stat().st_size != item["bytes"]:
            raise ValueError(f"Generalization artifact hash mismatch: {name}")
    summary, reference, ref_manifest = (_read(output/name) for name in ("summary.json", "reference_summary.json", "reference_manifest.json"))
    if (summary["content_sha256"] != manifest["summary_sha256"] or summary["content_sha256"] != payload_sha256({k:v for k,v in summary.items() if k != "content_sha256"})
            or reference["content_sha256"] != summary["reference_summary_sha256"]
            or reference["content_sha256"] != payload_sha256({k:v for k,v in reference.items() if k != "content_sha256"})
            or ref_manifest["content_sha256"] != payload_sha256({k:v for k,v in ref_manifest.items() if k != "content_sha256"})
            or ref_manifest["summary_sha256"] != reference["content_sha256"]):
        raise ValueError("Generalization/reference summary binding mismatch")
    for name in ("scaler.json", *(r["checkpoint"] for r in reference["records"])):
        if file_sha256(output/name) != ref_manifest["files"][name]["sha256"]:
            raise ValueError("Frozen reference weight/scaler binding changed")
    if file_sha256(output/"reference_summary.json") != ref_manifest["files"]["summary.json"]["sha256"]:
        raise ValueError("Frozen reference summary bytes changed")
    input_manifest = _read(output/"input_manifest.json")
    if input_manifest["content_sha256"] != summary["input_dataset_sha256"] or input_manifest["content_sha256"] != payload_sha256({k:v for k,v in input_manifest.items() if k != "content_sha256"}):
        raise ValueError("Generalization dataset seal binding changed")
    for name, stored in (("quality.json", "input_quality.json"), ("config.json", "input_config.json"), ("eligible_input.json", "eligible_input.json")):
        if file_sha256(output/stored) != input_manifest["files"][name]["sha256"]:
            raise ValueError("Generalization input metadata binding changed")
    input_sources = _read(output/"input_quality.json")["sources"]
    source_events = []
    for source in input_sources:
        query = source["query"]
        assert_development_event(query["year"], query["round_number"], event_id=source["event_id"])
        source_events.append(source["event_id"])
    if len(source_events) != len(EVENTS) or set(source_events) != set(EVENTS):
        raise ValueError("Generalization input source membership changed")
    if summary["profile"] not in ("research", "smoke") or summary["task_closure_eligible"] != (summary["profile"] == "research"):
        raise ValueError("Invalid generalization research/smoke eligibility")
    if summary["profile"] == "research" and (
        reference["content_sha256"] != REFERENCE_SEAL or _read(output/"input_quality.json").get("input_truth") == "SIMULATED"
        or _read(output/"eligible_input.json").get("calendar_sha256") != CALENDAR_SEAL
        or file_sha256(output/"input_config.json") != PROXY_CONFIG_SEAL
    ):
        raise ValueError("Generalization research closure lacks frozen public reference/input lineage")
    if summary["cohort_tracks"] != _tracks(reference, summary["profile"]):
        raise ValueError("Generalization cohort circuit definition changed")
    metadata = _read(output/"window_metadata.json")
    if {m["event_id"] for m in metadata} != set(EVENTS) or any(m["track_id"] != summary["cohort_tracks"][m["event_id"]] for m in metadata):
        raise ValueError("Generalization window cohort/circuit mismatch")
    with np.load(output/"windows.npz", allow_pickle=False) as data:
        windows = ForecastWindows(data["dynamic"], data["static"], data["target"], metadata, reference["vocabulary"])
    counts = {event: sum(m["event_id"] == event for m in metadata) for event in EVENTS}
    if counts != summary["origins_per_event"] or (summary["profile"] == "research" and min(counts.values()) < 1000):
        raise ValueError("Generalization event coverage binding failed")
    payload = _read(output/"scaler.json")
    scaler = ForecastScaler(*(np.array(payload[k]) for k in ("input_mean", "input_std", "target_mean", "target_std")))
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        with np.load(output/"predictions.npz", allow_pickle=False) as data:
            if not np.array_equal(data["actual"], windows.target):
                raise ValueError("Generalization saved targets mismatch")
            predictions = {}
            for name in ("persistence", "trend"):
                raw = transparent_prediction(windows, name)
                if not np.array_equal(raw, data[name+"_raw"]) or not np.array_equal(np.maximum(raw, 0), data[name]):
                    raise ValueError("Generalization causal control replay mismatch")
                predictions[name] = data[name]
            for record in reference["records"]:
                name = record["name"]
                raw = checkpoint_prediction(output/record["checkpoint"], record, windows, scaler)
                if not np.allclose(raw, data[name+"_raw"], rtol=1e-6, atol=1e-7) or not np.allclose(np.maximum(raw, 0), data[name], rtol=1e-6, atol=1e-7):
                    raise ValueError("Generalization checkpoint prediction replay mismatch")
                predictions[name] = data[name]
                if record["kind"] == "tft":
                    with torch.random.fork_rng(devices=[]):
                        model = neural_model("tft", windows.static_widths, record["hidden"])
                        model.load_state_dict(torch.load(output/record["checkpoint"], map_location="cpu", weights_only=True))
                    quantiles = neural_quantile_prediction(model, windows, scaler)
                    if not np.allclose(quantiles, data[name+"_quantiles_raw"], rtol=1e-6, atol=1e-7) or not np.allclose(np.maximum(quantiles, 0), data[name+"_quantiles_projected"], rtol=1e-6, atol=1e-7):
                        raise ValueError("Generalization TFT quantile replay mismatch")
                    stored_quantiles = data[name+"_quantiles_projected"]
                    strata = classify_tracks(metadata, reference["vocabulary"]["track_id"])
                    if _interval_metrics(windows.target, stored_quantiles, metadata, strata) != summary["tft_uncalibrated_quantiles"][name]["intervals"]:
                        raise ValueError("Generalization TFT coverage replay mismatch")
            for name, values in predictions.items():
                raw_values = data[name+"_raw"]
                _, correction = project_nonnegative(raw_values)
                diagnostics = {"projection": correction, "raw": detailed_metrics(windows.target, raw_values, metadata),
                               "projected": detailed_metrics(windows.target, values, metadata)}
                if diagnostics != summary["diagnostics"][name]:
                    raise ValueError("Generalization raw/projected diagnostic replay mismatch")
            scores = generalization_scores(windows.target, predictions, metadata, reference["vocabulary"]["track_id"], _family_members(reference))
            if scores != summary["scores"] or frozen_family_decision(scores, reference["validation_selected_family"]) != summary["frozen_family_decision"]:
                raise ValueError("Generalization scores/confidence/decision replay mismatch")
    finally:
        torch.set_num_threads(old_threads)
    if summary["models_requested"] != reference["models_requested"] or summary["checkpoint_count"] != len(reference["records"]):
        raise ValueError("Generalization model family binding mismatch")
    return {"verified": True, "task_closure_eligible": summary["task_closure_eligible"], "checkpoints": len(reference["records"]),
            "summary_sha256": summary["content_sha256"], "decision": summary["frozen_family_decision"]}


def make_generalization_smoke_dataset(reference_path: Path, output: Path) -> Path:
    """SIMULATED eval streams; genuine public provenance reader remains active."""
    if output.exists():
        raise FileExistsError("Generalization smoke input must be fresh")
    reference = _read(reference_path/"summary.json")
    source = reference_path.with_name(reference_path.name+"-simulated-input")
    _, source_manifest = read_tyre_energy_dataset(source)
    tracks = _tracks(reference, "smoke")
    frame = pd.read_parquet(source/"samples.parquet")
    quality = _read(source/"quality.json")
    rows, excluded, sources = [], [], []
    for old, new in zip(reference["split"]["train"]+reference["split"]["test"], EVENTS, strict=True):
        group = frame[frame.event_id == old].copy()
        for field in ("event_id", "session_id", "sequence_id", "segment_id"):
            group[field] = group[field].str.replace(old, new, regex=False)
        group["track_id"] = tracks[new]
        rows.append(group)
        record = next(s for s in quality["sources"] if s["event_id"] == old)
        sources.append({**record, "event_id": new, "query": {"year": 2023, "round_number": int(new[-2:]), "session": "R"}})
        excluded.extend({"event_id": new, "driver_id": s["driver_id"], "native_car_row": s["native_car_rows"]-1, "reason": "SIMULATED_exclusion"} for s in record["streams"])
    import pyarrow as pa
    import pyarrow.parquet as pq

    from apexsim.research.tyre_energy_dataset import VERSION, sample_schema

    table = pa.Table.from_pandas(pd.concat(rows, ignore_index=True), schema=sample_schema(), preserve_index=False)
    table = table.replace_schema_metadata(sample_schema().metadata)
    output.mkdir(parents=True)
    pq.write_table(table, output/"samples.parquet")
    pq.write_table(pa.Table.from_pylist(excluded), output/"rejections.parquet")
    for name in ("eligible_input.json", "config.json"):
        shutil.copyfile(source/name, output/name)
    write_manifest(output/"quality.json", {"validation": validate_samples(table), "target_quality": "PROXY_NOT_MEASURED", "input_truth": "SIMULATED", "sources": sources})
    manifest = {"schema_version": VERSION, "eligible_dataset_sha256": source_manifest["eligible_dataset_sha256"],
                "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(output/"manifest.json", manifest)
    return output
