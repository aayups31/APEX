"""R029 frozen two-circuit reference-geometry study, source lineage and portable replay."""
from __future__ import annotations

import json
import platform
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from apexsim import track_geometry
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import position_laps, reference_geometry
from apexsim.research.position_laps import (
    EVENT_TRACKS,
    MASK_SEALS,
    boundary_position,
    extract_position_lap,
    position_arrays,
)
from apexsim.research.reference_geometry import (
    CANDIDATES,
    GeometryConfig,
    ReferenceCurve,
    evaluate_reference,
    fit_reference,
    reconstruction_gate,
    register_lap,
)


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def select_laps(mask: dict, event: str, driver: str, role: str) -> list[dict]:
    selected = sorted((r for s in mask["segments"] if s["event_id"] == event and s["driver"] == driver for r in s["rows"]), key=lambda row: row["lap"])
    if len(selected) < 3:
        raise ValueError("Insufficient preregistered eligible laps; replacement is forbidden")
    return [{"event_id": event, "driver_id": driver, "lap_number": r["lap"], "native_row": r["native_row"],
             "track_id": EVENT_TRACKS[event], "role": role} for r in selected[:3]]


def fit_case(laps: list[dict], track: str) -> tuple[dict, dict]:
    training = [lap for lap in laps if lap["metadata"]["role"] == "train"]
    validation = [lap for lap in laps if lap["metadata"]["role"] == "validation"]
    tests = [lap for lap in laps if lap["metadata"]["role"] == "test"]
    if (len(training), len(validation), len(tests)) != (3, 3, 6):
        raise ValueError("R029 requires the frozen3/3/6 lap roles per circuit")
    reference = training[0]["xy_m"]
    aligned = {}
    registrations = {}
    for lap in laps:
        key = lap["metadata"]["lap_id"]
        aligned[key], registrations[key] = register_lap(lap["xy_m"], reference)
    train_xy = [aligned[lap["metadata"]["lap_id"]] for lap in training]
    candidates, curves = [], []
    for config in CANDIDATES:
        curve = fit_reference(train_xy, config, track)
        values = [float(np.mean(curve.project(aligned[lap["metadata"]["lap_id"]], refine=False)["distance_m"]**2)) for lap in validation]
        candidates.append({"config": asdict(config), "validation_lap_mse_m2": values, "mean_validation_mse_m2": float(np.mean(values))})
        curves.append(curve)
    selected = min(range(len(candidates)), key=lambda i: candidates[i]["mean_validation_mse_m2"])
    curve = curves[selected]
    metrics, saved = [], {}
    for lap in laps:
        metadata = lap["metadata"]
        key = metadata["lap_id"]
        result, predictions = evaluate_reference(curve, aligned[key], train_xy[0])
        metrics.append({**metadata, "registration": registrations[key], **result})
        saved[key+"_aligned_xy"] = aligned[key]
        for name, values in predictions.items():
            saved[key+"_"+name] = values
    gate = reconstruction_gate(curve, train_xy, [m for m in metrics if m["role"] == "test"])
    query = np.linspace(0, curve.length_m, 2048, endpoint=False)
    full_xy, tangent, _ = curve.geometry(query)
    normal = np.column_stack((-tangent[:, 1], tangent[:, 0]))
    offsets, lengths = [], []
    for left_out in range(3):
        alternate = fit_reference([xy for i, xy in enumerate(train_xy) if i != left_out], curve.config, track)
        # Compare corresponding normalized phase along each curve's true station.
        other_xy, _, _ = alternate.geometry(query/curve.length_m*alternate.length_m)
        offsets.append(np.sum((other_xy-full_xy)*normal, axis=1))
        lengths.append(alternate.length_m)
    offsets = np.array(offsets)
    saved.update(coefficients=curve.coefficients, arc_u=curve.arc_u, arc_s=curve.arc_s,
                 sensitivity_station_m=query, sensitivity_normal_offsets_m=offsets)
    summary = {"track_id": track, "selected_config": asdict(curve.config), "candidate_selection": candidates,
               "selected_candidate_index": selected, "length_m": curve.length_m, "gate": gate, "lap_metrics": metrics,
               "frame_anchor_lap_id": training[0]["metadata"]["lap_id"], "frame_truth": "LOCAL_SOURCE_XY; HELD_OUT_RIGID_POSE_REGISTRATION",
               "sensitivity": {"method": "three leave-one-training-lap fits; not a calibrated confidence band",
                               "p95_absolute_normal_offset_m": float(np.quantile(abs(offsets), .95)),
                               "max_absolute_normal_offset_m": float(np.max(abs(offsets))), "leave_one_lap_lengths_m": lengths},
               "geometry_truth": "RECONSTRUCTED_REFERENCE_RACING_TRACE_NOT_SURVEYED_CENTERLINE"}
    return summary, saved


def _annotations(curve: ReferenceCurve, laps: list[dict], native_laps: pd.DataFrame, positions: pd.DataFrame, registration: dict) -> dict:
    annotations = {name: {"status": "UNKNOWN", "value": None, "reason": reason} for name, reason in (
        ("width_m", "No surveyed track boundary evidence"), ("elevation_m", "Native Z is not a validated elevation/grade map"),
        ("official_drs_zones", "Driver activation does not identify official zones"), ("pit_lane_route", "A full pit lane is not reconstructed"),
        ("surveyed_centerline", "Observed racing traces do not identify a surveyed centerline"))}
    annotations["start_finish"] = {"status": "RECONSTRUCTED", "station_m": 0., "source": "selected native lap timing anchors"}
    arrays = position_arrays(positions)
    observations = {name: [] for name in ("sector1_end", "sector2_end", "pit_entry", "pit_exit")}
    for lap in laps:
        if lap["metadata"]["role"] != "train":
            continue
        metadata = lap["metadata"]
        one, two = metadata["sector_durations_s"]
        for name, offset in (("sector1_end", one), ("sector2_end", one+two if one is not None and two is not None else None)):
            if offset is not None:
                observations[name].append((metadata["lap_start_s"]+offset, metadata["native_row"]))
    for index, row in native_laps.iterrows():
        if str(row.DriverNumber) == "4":
            for field, name in (("PitInTime", "pit_entry"), ("PitOutTime", "pit_exit")):
                if pd.notna(row[field]):
                    observations[name].append((float(row[field].total_seconds()), int(index)))
    # All source coordinates share the first training lap's native session frame.
    rotation, translation = np.array(registration["rotation"]), np.array(registration["translation_m"])
    for name, values in observations.items():
        projected = []
        for time, row in values:
            try:
                point, parents, weight = boundary_position(arrays, time, allow_pit_status=name.startswith("pit_"))
                result = curve.project((point@rotation+translation)[None, :])
                supported = result["distance_m"][0] <= 50
                projected.append({"native_lap_row": row, "session_time_s": time, "native_position_parents": list(parents),
                                  "source_xy_m": point.tolist(), "registered_xy_m": (point@rotation+translation).tolist(),
                                  "interpolation_weight": weight, "station_m": float(result["station_m"][0]),
                                  "distance_to_reference_m": float(result["distance_m"][0]),
                                  "status": "RECONSTRUCTED_TIMING_PROJECTION" if supported else "UNKNOWN_OFF_REFERENCE"})
            except ValueError as exc:
                projected.append({"native_lap_row": row, "session_time_s": time, "status": "UNKNOWN_UNSUPPORTED_POSITION", "reason": str(exc)})
        supported_values = [p["station_m"] for p in projected if p["status"] == "RECONSTRUCTED_TIMING_PROJECTION"]
        spread = None
        if supported_values:
            angle = np.array(supported_values)/curve.length_m*2*np.pi
            center = float(np.arctan2(np.sin(angle).mean(), np.cos(angle).mean())%(2*np.pi)*curve.length_m/(2*np.pi))
            offsets = (np.array(supported_values)-center+curve.length_m/2)%curve.length_m-curve.length_m/2
            spread = {"circular_mean_station_m": center, "p95_absolute_station_offset_m": float(np.quantile(abs(offsets), .95)), "supported_observations": len(supported_values)}
        annotations[name] = {"status": "RECONSTRUCTED_TIMING_PROJECTIONS" if supported_values else "UNKNOWN",
                             "observations": projected, "spread": spread, "route_or_official_zone_claim": False}
    return annotations


def run_track_reconstruction(archives: list[Path], mask_2024: Path, mask_2023: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Track reconstruction output must be fresh")
    if any(output.resolve().is_relative_to(p.resolve()) for p in [*archives, mask_2024, mask_2023]):
        raise ValueError("Reconstruction output must be outside frozen inputs")
    sources = {}
    for path in archives:
        metadata = _read(path/"manifest.json")
        query = metadata["query"]
        event = f"F1_{query['year']}_R{query['round_number']:02d}"
        assert_development_event(query["year"], query["round_number"], event_id=event)
        if event not in EVENT_TRACKS or event in sources or query["session"] != "R":
            raise ValueError("R029 requires unique exact preregistered race archives")
        sources[event] = (path, verify_fastf1_archive(path))
    if set(sources) != set(EVENT_TRACKS):
        raise ValueError("R029 requires all four preregistered archives")
    masks = {2024: _read(mask_2024), 2023: _read(mask_2023)}
    for year, mask in masks.items():
        if mask.get("content_sha256") != MASK_SEALS[year] or mask["content_sha256"] != payload_sha256({k:v for k,v in mask.items() if k != "content_sha256"}):
            raise ValueError("R029 requires original frozen eligibility masks")
    watched = [mask_2024, mask_2023, Path(__file__), Path(position_laps.__file__), Path(reference_geometry.__file__), Path(track_geometry.__file__)]
    watched += [path/"manifest.json" for path, _ in sources.values()]
    before = {str(p): file_sha256(p) for p in watched}
    cases, inputs, source_records = {}, {}, []
    for track, current, older in (("bahrain", "F1_2024_R01", "F1_2023_R01"), ("monza", "F1_2024_R16", "F1_2023_R14")):
        selected, native = [], {}
        for event in (current, older):
            path, manifest = sources[event]
            mask = masks[int(event[3:7])]
            binding = next(s for s in mask["sources"] if s["event_id"] == event)
            if binding["archive_sha256"] != manifest["content_sha256"]:
                raise ValueError("R029 mask/archive identity binding mismatch")
            laps = pd.read_parquet(path/"tables/laps.parquet")
            native[event] = laps
            roles = (("4", "train"), ("44", "validation")) if event == current else (("4", "test"), ("44", "test"))
            for driver, role in roles:
                positions = pd.read_parquet(path/f"tables/pos_data/{driver}.parquet")
                native[event+"_"+driver] = positions
                for selection in select_laps(mask, event, driver, role):
                    selected.append(extract_position_lap(laps, positions, selection))
            source_records.append({"event_id": event, "archive_sha256": manifest["content_sha256"], "query": manifest["query"],
                                   "identity": manifest["identity"], "environment": manifest["environment"], "source_manifest": manifest["source_manifest"],
                                   "native_files": {k:v for k,v in manifest["files"].items() if k in ("tables/laps.parquet", "tables/pos_data/4.parquet", "tables/pos_data/44.parquet")}})
        result, arrays = fit_case(selected, track)
        anchor = next(m for m in result["lap_metrics"] if m["lap_id"] == result["frame_anchor_lap_id"])
        curve = ReferenceCurve(arrays["coefficients"], GeometryConfig(**result["selected_config"]), track)
        result["annotations"] = _annotations(curve, selected, native[current], native[current+"_4"], anchor["registration"])
        cases[track] = result
        inputs[track] = {"laps": selected, "arrays": arrays}
    for path, original in sources.values():
        if verify_fastf1_archive(path)["content_sha256"] != original["content_sha256"]:
            raise ValueError("R029 source changed during reconstruction")
    if before != {str(p): file_sha256(p) for p in watched}:
        raise ValueError("R029 inputs/code changed during reconstruction")
    passed = all(case["gate"]["passed"] for case in cases.values())
    summary = {"schema_version": "apex-reference-geometry-study-v1", "classification": "ADAPTATION", "profile": "research",
               "R029_complete": passed, "task_closure_eligible": passed, "decision": "PASS_FROZEN_REFERENCE_GEOMETRY" if passed else "REJECT_FROZEN_GEOMETRY_GATES",
               "promotion": False, "cases": cases, "sources": source_records, "mask_sha256": {str(y): m["content_sha256"] for y, m in masks.items()},
               "implementation_sha256": {p.name: before[str(p)] for p in watched[2:6]},
               "environment": {"python": platform.python_version(), "numpy": np.__version__, "scipy": __import__("scipy").__version__},
               "limitations": ["Reconstructed racing trace, not surveyed centerline/boundaries", "Held-out whole-lap rigid pose registration; shape evaluation, not absolute georeferencing",
                               "Coarse curvature consistency proxy is not physical survey truth", "Three training laps and two development circuits; sensitivity is not calibrated confidence",
                               "Official DRS, physical width/elevation and complete pit route remain UNKNOWN", "No production track/vehicle or R3 maturity promotion"]}
    summary["content_sha256"] = payload_sha256(summary)
    _save_artifacts(output, summary, inputs)
    return summary


def _save_artifacts(output: Path, summary: dict, inputs: dict) -> None:
    output.mkdir(parents=True, exist_ok=False)
    write_manifest(output/"summary.json", summary)
    for track, payload in inputs.items():
        raw, metadata = {}, []
        for lap in payload["laps"]:
            key = lap["metadata"]["lap_id"]
            metadata.append(lap["metadata"])
            raw.update({key+"_xy": lap["xy_m"], key+"_time": lap["time_s"], key+"_native_parents": lap["native_parents"]})
        write_manifest(output/f"{track}_lap_metadata.json", metadata)
        np.savez_compressed(output/f"{track}_lap_inputs.npz", **raw)
        np.savez_compressed(output/f"{track}_geometry_predictions.npz", **payload["arrays"])
    manifest = {"schema_version": "apex-reference-geometry-manifest-v1", "summary_sha256": summary["content_sha256"],
                "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(output/"manifest.json", manifest)


def _close_values(a, b) -> bool:
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(_close_values(value, b[key]) for key, value in a.items())
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_close_values(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, bool | str) or a is None:
        return a == b
    return bool(np.isclose(a, b, rtol=1e-10, atol=1e-9))


def verify_track_reconstruction(output: Path) -> dict:
    manifest = _read(output/"manifest.json")
    if manifest.get("schema_version") != "apex-reference-geometry-manifest-v1" or manifest["content_sha256"] != payload_sha256({k:v for k,v in manifest.items() if k != "content_sha256"}):
        raise ValueError("Reference geometry manifest hash/schema mismatch")
    if set(manifest["files"]) != {p.name for p in output.iterdir()}-{"manifest.json"}:
        raise ValueError("Reference geometry artifact inventory mismatch")
    for name, item in manifest["files"].items():
        if Path(name).name != name or file_sha256(output/name) != item["sha256"] or (output/name).stat().st_size != item["bytes"]:
            raise ValueError(f"Reference geometry artifact hash mismatch: {name}")
    summary = _read(output/"summary.json")
    if summary["content_sha256"] != manifest["summary_sha256"] or summary["content_sha256"] != payload_sha256({k:v for k,v in summary.items() if k != "content_sha256"}):
        raise ValueError("Reference geometry summary binding mismatch")
    if summary["profile"] not in ("research", "smoke"):
        raise ValueError("Reference geometry invalid profile")
    if summary["profile"] == "research" and (set(summary["cases"]) != {"bahrain", "monza"}
            or {s["event_id"] for s in summary["sources"]} != set(EVENT_TRACKS)
            or summary["mask_sha256"] != {str(k): v for k, v in MASK_SEALS.items()}):
        raise ValueError("Reference geometry research source/cohort mismatch")
    for source in summary["sources"]:
        q = source["query"]
        assert_development_event(q["year"], q["round_number"], event_id=source["event_id"])
    for track, saved_summary in summary["cases"].items():
        metadata = _read(output/f"{track}_lap_metadata.json")
        with np.load(output/f"{track}_lap_inputs.npz", allow_pickle=False) as raw:
            laps = [{"metadata": m, "xy_m": raw[m["lap_id"]+"_xy"], "time_s": raw[m["lap_id"]+"_time"], "native_parents": raw[m["lap_id"]+"_native_parents"]} for m in metadata]
        replay, arrays = fit_case(laps, track)
        for key in ("selected_config", "selected_candidate_index", "gate"):
            if not _close_values(replay[key], saved_summary[key]):
                raise ValueError("Reference geometry selection/gate replay mismatch")
        with np.load(output/f"{track}_geometry_predictions.npz", allow_pickle=False) as saved:
            if set(saved.files) != set(arrays):
                raise ValueError("Reference geometry prediction inventory mismatch")
            for key, values in arrays.items():
                if not np.allclose(saved[key], values, rtol=1e-10, atol=1e-9):
                    raise ValueError(f"Reference geometry prediction replay mismatch: {key}")
        if not _close_values(replay["lap_metrics"], saved_summary["lap_metrics"]) or not _close_values(replay["sensitivity"], saved_summary["sensitivity"]):
            raise ValueError("Reference geometry lap/sensitivity diagnostics replay mismatch")
        if "annotations" in saved_summary:
            curve = ReferenceCurve(arrays["coefficients"], GeometryConfig(**replay["selected_config"]), track)
            for annotation in saved_summary["annotations"].values():
                for observation in annotation.get("observations", []):
                    if "registered_xy_m" in observation:
                        p = curve.project(np.array([observation["registered_xy_m"]]))
                        if not np.isclose(p["station_m"][0], observation["station_m"], rtol=1e-10, atol=1e-8) or not np.isclose(p["distance_m"][0], observation["distance_to_reference_m"], atol=1e-8):
                            raise ValueError("Reference geometry annotation projection mismatch")
    passed = all(case["gate"]["passed"] for case in summary["cases"].values())
    if summary["task_closure_eligible"] != (passed and summary["profile"] == "research"):
        raise ValueError("Reference geometry research eligibility mismatch")
    return {"verified": True, "task_closure_eligible": summary["task_closure_eligible"], "decision": summary["decision"], "summary_sha256": summary["content_sha256"]}


def run_track_reconstruction_smoke(output: Path) -> dict:
    """Two SIMULATED shapes, exercising selection/projection/artifacts without public closure."""
    if output.exists():
        raise FileExistsError("Reference geometry smoke output must be fresh")
    cases, inputs = {}, {}
    for track, axes in (("sim_circle", (200., 200.)), ("sim_ellipse", (300., 170.))):
        theta = np.linspace(0, 2*np.pi, 257)
        original = np.column_stack((axes[0]*np.cos(theta), axes[1]*np.sin(theta)))
        laps = []
        for i, role in enumerate(("train",)*3+("validation",)*3+("test",)*6):
            # Deterministic rigid frame changes, no fake source archive verification.
            angle = .02*i
            rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
            xy = original@rotation+np.array([i*2., -i*3.])
            key = f"{track}_{i}"
            metadata = {"lap_id": key, "role": role, "driver_id": "4" if i < 3 else "44", "lap_number": i+1,
                        "track_id": track, "input_truth": "SIMULATED", "raw_closure_gap_m": float(np.linalg.norm(xy[-1]-xy[0]))}
            laps.append({"metadata": metadata, "xy_m": xy, "time_s": np.linspace(0, 90, len(xy)),
                         "native_parents": np.column_stack((np.arange(len(xy)), np.arange(len(xy))))})
        result, arrays = fit_case(laps, track)
        cases[track] = result
        inputs[track] = {"laps": laps, "arrays": arrays}
    summary = {"schema_version": "apex-reference-geometry-study-v1", "profile": "smoke", "input_truth": "SIMULATED",
               "classification": "ADAPTATION", "R029_complete": False, "task_closure_eligible": False, "promotion": False,
               "decision": "SIMULATED_EXECUTION_ONLY", "sources": [], "mask_sha256": {}, "cases": cases}
    summary["content_sha256"] = payload_sha256(summary)
    _save_artifacts(output, summary, inputs)
    return summary
