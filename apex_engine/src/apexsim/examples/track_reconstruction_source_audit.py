"""R029 pre-fit source audit with immutable native snapshots and portable replay."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.examples.track_reconstruction_demo import select_laps
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research.position_laps import (
    EVENT_TRACKS,
    MASK_SEALS,
    boundary_position,
    extract_position_lap,
    position_arrays,
)

TIMES = ("LapStartTime", "Time", "LapTime", "PitInTime", "PitOutTime", "Sector1Time", "Sector2Time")
FIELDS = ("DriverNumber", "LapNumber", "IsAccurate", "Deleted", "TrackStatus", "Compound", *TIMES)


def audit_lap(laps: pd.DataFrame, positions: pd.DataFrame, selection: dict) -> dict:
    """Report source support without fitting, filling gaps, or replacing a selected lap."""
    result = {**selection, "source_gate_passed": False}
    try:
        timestamps, _, _, _ = arrays = position_arrays(positions)
        row = laps.iloc[selection["native_row"]]
        start, end = (row[name].total_seconds() for name in ("LapStartTime", "Time"))
        indices = np.flatnonzero((timestamps > start+1e-8)&(timestamps < end-1e-8))
        times = np.r_[start, timestamps[indices], end]
        gaps = np.diff(times)
        # Interior indices refer to the original complete native stream, not resampled data.
        parents = np.r_[-1, indices, -1]
        result.update(native_samples=len(indices), max_gap_s=float(gaps.max()),
                      unsupported_intervals=[{"start_s": float(times[i]), "end_s": float(times[i+1]),
                                              "gap_s": float(gaps[i]), "native_parent_rows": parents[i:i+2].tolist()}
                                             for i in np.flatnonzero(gaps > .75)])
        try:
            first, _, _ = boundary_position(arrays, start)
            last, _, _ = boundary_position(arrays, end)
            result["raw_closure_gap_m"] = float(np.linalg.norm(last-first))
        except ValueError as exc:
            result["boundary_support_failure"] = str(exc)
        result["accepted_metadata"] = extract_position_lap(laps, positions, selection)["metadata"]
        result["source_gate_passed"] = True
    except ValueError as exc:
        result["failure_reason"] = str(exc)
    return result


def _lap_snapshot(row: pd.Series) -> dict:
    snapshot = {}
    for name in FIELDS:
        value = row[name]
        if pd.isna(value):
            snapshot[name] = None
        elif name in TIMES:
            snapshot[name] = int(value.value)
        elif name in ("IsAccurate", "Deleted"):
            snapshot[name] = bool(value)
        elif name == "LapNumber":
            snapshot[name] = float(value)
        else:
            snapshot[name] = str(value)
    return snapshot


def _restore_lap(snapshot: dict, selection: dict) -> pd.DataFrame:
    row = {k: (pd.Timedelta(v, unit="ns") if v is not None else pd.NaT) if k in TIMES else v
           for k, v in snapshot.items()}
    # Preserve the original iloc identity even though other laps are unnecessary for this replay.
    index = selection["native_row"]
    return pd.DataFrame([row], index=[index]).reindex(range(index+1))


def run_source_audit(archives: list[Path], mask_2024: Path, mask_2023: Path, output: Path) -> dict:
    """Audit all 24 frozen laps before fitting; persist rejected native evidence too."""
    if output.exists():
        raise FileExistsError("Source audit output must be fresh")
    paths = [*archives, mask_2024, mask_2023]
    if any(output.resolve().is_relative_to(p.resolve()) for p in paths):
        raise ValueError("Source audit output must be outside immutable inputs")
    sources = {}
    for path in archives:
        metadata = json.loads((path/"manifest.json").read_text())
        query = metadata["query"]
        event = f"F1_{query['year']}_R{query['round_number']:02d}"
        assert_development_event(query["year"], query["round_number"], event_id=event)
        if event not in EVENT_TRACKS or event in sources or query["session"] != "R":
            raise ValueError("Source audit requires exact unique preregistered race archives")
        sources[event] = path, verify_fastf1_archive(path)
    if set(sources) != set(EVENT_TRACKS):
        raise ValueError("Source audit requires all four preregistered archives")
    masks = {2024: json.loads(mask_2024.read_text()), 2023: json.loads(mask_2023.read_text())}
    for year, mask in masks.items():
        if mask.get("content_sha256") != MASK_SEALS[year] or mask["content_sha256"] != payload_sha256({k:v for k,v in mask.items() if k != "content_sha256"}):
            raise ValueError("Source audit requires original frozen masks")
    watched = [mask_2024, mask_2023, Path(__file__), Path(__file__).with_name("track_reconstruction_demo.py"),
               Path(__file__).parent.parent/"research/position_laps.py", Path(__file__).parent.parent/"research/reference_geometry.py"]
    before = {str(p): file_sha256(p) for p in watched}
    inputs, records, audits = {}, [], []
    for event, (path, manifest) in sources.items():
        mask = masks[int(event[3:7])]
        binding = next(s for s in mask["sources"] if s["event_id"] == event)
        if binding["archive_sha256"] != manifest["content_sha256"]:
            raise ValueError("Source audit mask/archive binding mismatch")
        laps = pd.read_parquet(path/"tables/laps.parquet")
        for driver in ("4", "44"):
            key = f"{event}_{driver}"
            positions = pd.read_parquet(path/f"tables/pos_data/{driver}.parquet")
            inputs.update({key+"_time_ns": positions.SessionTime.to_numpy().astype("timedelta64[ns]").astype(np.int64),
                           key+"_xy_native": positions[["X", "Y"]].to_numpy(float),
                           key+"_source": positions.Source.to_numpy().astype(str),
                           key+"_status": positions.Status.to_numpy().astype(str)})
            role = ("train" if driver == "4" else "validation") if event[3:7] == "2024" else "test"
            for selection in select_laps(mask, event, driver, role):
                records.append({"selection": selection, "native_lap": _lap_snapshot(laps.iloc[selection["native_row"]])})
                audits.append(audit_lap(laps, positions, selection))
    for path, original in sources.values():
        if verify_fastf1_archive(path)["content_sha256"] != original["content_sha256"]:
            raise ValueError("Source audit archive changed during audit")
    if before != {str(p): file_sha256(p) for p in watched}:
        raise ValueError("Source audit input/code changed during audit")
    passed = all(a["source_gate_passed"] for a in audits)
    summary = {"schema_version": "apex-reference-geometry-source-audit-v1", "profile": "research_source_audit",
               "decision": "SOURCE_SUPPORT_PASS_ONLY" if passed else "REJECT_FROZEN_SOURCE_SUPPORT",
               "source_gate_passed": passed, "selected_laps": len(audits),
               "supported_laps": sum(a["source_gate_passed"] for a in audits),
               "R029_complete": False, "task_closure_eligible": False, "fit_performed": False, "promotion": False,
               "audits": audits, "mask_sha256": {str(y): m["content_sha256"] for y,m in masks.items()},
               "sources": [{"event_id": e, "archive_sha256": m["content_sha256"], "manifest": m} for e,(_,m) in sources.items()],
               "implementation_sha256": {p.name: before[str(p)] for p in watched[2:]},
               "limitations": ["Source support only; no geometry accuracy or task closure follows", "Snapshots establish local consistency, not provider authentication",
                               "Frozen 0.75s gap limit and selected laps unchanged; no replacement or gap filling"]}
    summary["content_sha256"] = payload_sha256(summary)
    output.mkdir(parents=True)
    write_manifest(output/"summary.json", summary)
    write_manifest(output/"selected_native_laps.json", records)
    np.savez_compressed(output/"native_position_inputs.npz", **inputs)
    manifest = {"schema_version": "apex-reference-source-audit-manifest-v1", "summary_sha256": summary["content_sha256"],
                "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(output/"manifest.json", manifest)
    return summary


def verify_source_audit(output: Path) -> dict:
    """Recompute every frozen source decision from saved native streams and lap rows."""
    from apexsim.examples.track_reconstruction_demo import _close_values

    manifest = json.loads((output/"manifest.json").read_text())
    if manifest.get("schema_version") != "apex-reference-source-audit-manifest-v1" or manifest["content_sha256"] != payload_sha256({k:v for k,v in manifest.items() if k != "content_sha256"}):
        raise ValueError("Source audit manifest/schema mismatch")
    if set(manifest["files"]) != {"summary.json", "selected_native_laps.json", "native_position_inputs.npz"} or set(manifest["files"]) != {p.name for p in output.iterdir()}-{"manifest.json"}:
        raise ValueError("Source audit inventory mismatch")
    for name, item in manifest["files"].items():
        if file_sha256(output/name) != item["sha256"] or (output/name).stat().st_size != item["bytes"]:
            raise ValueError("Source audit artifact hash mismatch")
    summary = json.loads((output/"summary.json").read_text())
    if summary["content_sha256"] != manifest["summary_sha256"] or summary["content_sha256"] != payload_sha256({k:v for k,v in summary.items() if k != "content_sha256"}):
        raise ValueError("Source audit summary mismatch")
    if summary["schema_version"] != "apex-reference-geometry-source-audit-v1" or summary["mask_sha256"] != {str(y):s for y,s in MASK_SEALS.items()} or len(summary["sources"]) != 4 or {s["event_id"] for s in summary["sources"]} != set(EVENT_TRACKS):
        raise ValueError("Source audit frozen cohort mismatch")
    for source in summary["sources"]:
        q = source["manifest"]["query"]
        assert_development_event(q["year"], q["round_number"], event_id=source["event_id"])
        if source["archive_sha256"] != source["manifest"]["content_sha256"] or source["archive_sha256"] != payload_sha256({k:v for k,v in source["manifest"].items() if k != "content_sha256"}):
            raise ValueError("Source audit archive binding mismatch")
    records = json.loads((output/"selected_native_laps.json").read_text())
    audits, cohort = [], {}
    with np.load(output/"native_position_inputs.npz", allow_pickle=False) as raw:
        for record in records:
            selection = record["selection"]
            event, driver = selection["event_id"], selection["driver_id"]
            if event not in EVENT_TRACKS or driver not in ("4", "44") or selection["track_id"] != EVENT_TRACKS[event]:
                raise ValueError("Source audit selected identity mismatch")
            role = ("train" if driver == "4" else "validation") if event[3:7] == "2024" else "test"
            if selection["role"] != role:
                raise ValueError("Source audit selected role mismatch")
            key = f"{event}_{driver}"
            cohort.setdefault(key, []).append(selection["lap_number"])
            positions = pd.DataFrame({"SessionTime": pd.to_timedelta(raw[key+"_time_ns"], unit="ns"),
                                      "X": raw[key+"_xy_native"][:, 0], "Y": raw[key+"_xy_native"][:, 1],
                                      "Source": raw[key+"_source"], "Status": raw[key+"_status"]})
            audits.append(audit_lap(_restore_lap(record["native_lap"], selection), positions, selection))
    if len(cohort) != 8 or any(len(v) != 3 or len(set(v)) != 3 for v in cohort.values()) or not _close_values(audits, summary["audits"]):
        raise ValueError("Source audit native replay mismatch")
    supported = sum(a["source_gate_passed"] for a in audits)
    passed = supported == 24
    decision = "SOURCE_SUPPORT_PASS_ONLY" if passed else "REJECT_FROZEN_SOURCE_SUPPORT"
    if summary["selected_laps"] != 24 or summary["supported_laps"] != supported or summary["source_gate_passed"] != passed or summary["decision"] != decision or any(summary[k] for k in ("fit_performed", "promotion", "R029_complete", "task_closure_eligible")):
        raise ValueError("Source audit acceptance mismatch")
    return {"verified": True, "decision": decision, "supported_laps": supported, "selected_laps": 24,
            "task_closure_eligible": False, "summary_sha256": summary["content_sha256"]}
