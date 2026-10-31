"""R033 immutable native replay preparation, coverage and offline scientific replay."""
from __future__ import annotations

import platform
import shutil
import subprocess
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.examples import longitudinal_dataset
from apexsim.examples.longitudinal_dataset import dataset_guard, load_sections, verify_longitudinal_dataset
from apexsim.provenance import RUN_ID_PATTERN, file_sha256, payload_sha256, write_manifest
from apexsim.research import evidence, longitudinal_data, recorded_alignment, recorded_alignment_audit
from apexsim.research.evidence import check_seal, compare_numeric, finish_run, read_json, verify_inventory
from apexsim.research.longitudinal_data import EVENT_ROLES, EVENT_TRACKS
from apexsim.research.recorded_alignment import UNKNOWN_FIELDS, align_lap, longitudinal_inputs
from apexsim.research.recorded_alignment_audit import audit_aligned_lap

VERSION = "apex-recorded-replay-alignment-v1"
DATASET_SEAL = "2559478bf6a00a40f1850222035a86bf0046e14b857d1c81973513e209b3b9ab"
PROTOCOL = Path(__file__).resolve().parents[4]/"research/protocols/RECORDED_REPLAY_ALIGNMENT.md"


def field_contract() -> dict:
    """Machine-readable units/truth at the research observation boundary."""
    return {"schema_version": VERSION+"-fields", "coordinate_frame": "native source XY meters; vehicle body frame UNKNOWN",
            "native_observations": {"speed_mps": "m/s; parsed Speed/3.6; not measured body vx",
                                    "throttle": "fraction; parsed Throttle/100", "brake_on": "boolean only; pressure/force UNKNOWN",
                                    "rpm": "revolutions/min; parsed engine speed", "gear": "integer; parsed transmission gear",
                                    "drs_open": "nullable integer 0/1; documented raw code map",
                                    "x_m": "m; backward native X*.1", "y_m": "m; backward native Y*.1",
                                    "session_time_s": "s; parsed SessionTime", "sample_utc": "UTC timestamp; native Date"},
            "reconstructed": {"position_age_s": "s; car time minus native position time",
                              "position_previous_gap_s": "s; previous same-lap position interval",
                              "covered_interval_s": "s; supported left-observation native interval"},
            "offline_reference": {"reference_curvature_1pm": "1/m; frozen registered R029 reference, not body yaw",
                                  "reference_projection_error_m": "m; frozen reference distance"},
            "unknown_nullable_fields": list(UNKNOWN_FIELDS), "full_bicycle_adapter": "ABSTAIN_MISSING_MEASUREMENTS"}


def guard_inputs(root: Path) -> dict:
    """Guard all event identities before any raw/binary inventory or payload access."""
    header = read_json(root/"inputs.json")
    if header.get("schema_version") != VERSION+"-inputs":
        raise ValueError("R033 source header schema mismatch")
    for lap in header["laps"]:
        event = lap["event_id"]
        assert_development_event(int(event[3:7]), int(event[-2:]), event_id=event)
        if event not in EVENT_ROLES or lap["track_id"] != EVENT_TRACKS[event] or lap["driver_id"] not in ("4", "44"):
            raise ValueError("R033 source header event/track/driver mismatch")
        if not RUN_ID_PATTERN.fullmatch(lap["lap_id"]):
            raise ValueError("R033 unsafe source lap identifier")
    if header["profile"] == "research":
        geometry = dataset_guard(root/"longitudinal")
        source = read_json(root/"longitudinal/summary.json")
        check_seal(source)
        expected_laps = [lap for track in ("bahrain", "monza") for lap in read_json(root/"longitudinal/geometry"/f"{track}_lap_metadata.json")]
        if (source["content_sha256"] != DATASET_SEAL or header["input_truth"] != "FASTF1_PARSED_SOURCE"
                or header["laps"] != expected_laps or len(expected_laps) != 88):
            raise ValueError("R033 requires frozen accepted public cohort/geometry provenance")
        for source_info in geometry["sources"]:
            event = source_info["event_id"]
            manifest = read_json(root/"longitudinal/native"/event/"manifest.json")
            for driver in ("4", "44"):
                if file_sha256(root/"positions"/event/f"{driver}.parquet") != manifest["files"][f"tables/pos_data/{driver}.parquet"]["sha256"]:
                    raise ValueError("R033 native position differs from frozen archive")
    elif (header["profile"] != "smoke" or header["input_truth"] != "SIMULATED_NATIVE_STREAMS"
          or len(header["laps"]) != 8 or any(lap.get("fixture_source") != "SIMULATED_NATIVE_STREAMS" for lap in header["laps"])):
        raise ValueError("R033 invalid source profile or simulated provenance")
    return header


def load_sources(root: Path, header: dict) -> tuple[dict, dict]:
    """Read only managed source snapshots, after every event has been guarded."""
    cars, positions = {}, {}
    if header["profile"] == "research":
        verify_longitudinal_dataset(root/"longitudinal")
    for event in EVENT_ROLES:
        for driver in ("4", "44"):
            key = event, driver
            car_path = (root/"longitudinal/native"/event/"tables/car_data"/f"{driver}.parquet" if header["profile"] == "research"
                        else root/"simulated_native"/f"{event}_{driver}_car.parquet")
            pos_path = (root/"positions"/event/f"{driver}.parquet" if header["profile"] == "research"
                        else root/"simulated_native"/f"{event}_{driver}_position.parquet")
            cars[key], positions[key] = pd.read_parquet(car_path), pd.read_parquet(pos_path)
    return cars, positions


def geometry_context(root: Path, header: dict) -> dict:
    context = {}
    if header["profile"] != "research":
        return context
    for track in ("bahrain", "monza"):
        base = root/"longitudinal/geometry"
        with (np.load(base/f"{track}_lap_inputs.npz", allow_pickle=False) as native,
              np.load(base/f"{track}_geometry_predictions.npz", allow_pickle=False) as prediction):
            for lap in read_json(base/f"{track}_lap_metadata.json"):
                key = lap["lap_id"]
                context[key] = {"native_parents": native[key+"_native_parents"], "curvature_1pm": prediction[key+"_curvature_1pm"],
                                "distance_m": prediction[key+"_distance_m"]}
    return context


def aggregate_coverage(metrics: list[dict], sections: list[dict], profile: str) -> dict:
    """All rows/full lap durations are denominators; no outcome-driven exclusions."""
    groups = {}
    keys = ("native_car_rows", "controls_observed_rows", "engine_observed_rows", "position_observed_rows", "joint_observed_rows", "covered_interval_s", "lap_duration_s")
    total = {key: sum(m[key] for m in metrics) for key in keys}
    for m in metrics:
        group = groups.setdefault(m["event_id"]+"/"+m["driver_id"], dict.fromkeys(keys, 0))
        for key in keys:
            group[key] += m[key]
    for values in groups.values():
        values["joint_row_coverage"] = values["joint_observed_rows"]/values["native_car_rows"]
    n = total["native_car_rows"]
    fractions = {"controls_observed": total["controls_observed_rows"]/n, "engine_observed": total["engine_observed_rows"]/n,
                 "position_observed": total["position_observed_rows"]/n, "joint_observed": total["joint_observed_rows"]/n,
                 "joint_interval_duration": total["covered_interval_s"]/total["lap_duration_s"]}
    supported = sum(s["supported"] for s in sections)
    passed = bool(len(groups) == 8 and fractions["controls_observed"] > .99 and fractions["engine_observed"] > .99
                  and fractions["joint_observed"] > .9 and fractions["joint_interval_duration"] > .9
                  and all(g["joint_row_coverage"] > .9 for g in groups.values())
                  and all(m["joint_row_coverage"] > .85 for m in metrics) and supported/len(sections) > .99
                  and sum(m["future_position_matches"] for m in metrics) == 0)
    public = profile == "research"
    passed = passed and (not public or (len(metrics) == 88 and len(sections) == 150))
    return {"schema_version": VERSION+"-results", "profile": profile, "input_truth": "FASTF1_PARSED_SOURCE" if public else "SIMULATED_NATIVE_STREAMS",
            "decision": ("ACCEPT_SCOPED_RECORDED_OBSERVATION_ALIGNMENT" if passed else "REJECT_RECORDED_OBSERVATION_ALIGNMENT") if public else "SIMULATED_EXECUTION_ONLY",
            "coverage_gate_passed": passed, "task_closure_eligible": passed and public, "production_promotion": False,
            "source_laps": len(metrics), "totals": total, "coverage_fractions": fractions, "event_driver_groups": groups,
            "per_lap": metrics, "longitudinal_sections": len(sections), "supported_longitudinal_sections": supported,
            "longitudinal_input_coverage": supported/len(sections), "future_position_matches": sum(m["future_position_matches"] for m in metrics),
            "full_bicycle_measured_state_control_coverage": 0., "unknown_model_fields": list(UNKNOWN_FIELDS),
            "geometry_truth": "FROZEN_OFFLINE_REGISTERED_REFERENCE; NOT_MEASURED_CHASSIS_STATE" if public else "NO_REFERENCE_GEOMETRY",
            "limitations": ["Public parsed channels may be reconstructed upstream; physical source latency is unknown",
                            "Boolean brake is not brake force/pressure; RPM/gear are not power-unit torque or ERS state",
                            "No observed steering/body lateral state/fuel/battery; full measured bicycle replay unavailable",
                            "Reused development cohort; no prediction error, full-lap autonomy or production promotion"]}


def section_references(root: Path, header: dict) -> list[dict]:
    if header["profile"] == "research":
        return [{"section_id": s.metadata["section_id"], "lap_id": s.metadata["lap_id"], "source_rows": s.car_rows,
                 "time_s": s.time_s, "throttle": s.throttle, "drs_open": s.drs_open, "initial_speed_mps": float(s.speed_mps[0])}
                for s in load_sections(root/"longitudinal")]
    return [{"section_id": lap["lap_id"]+"_section", "lap_id": lap["lap_id"], "source_rows": np.arange(5, 18, dtype=np.int64)} for lap in header["laps"]]


def compute_alignment(root: Path) -> tuple[dict, dict[str, pd.DataFrame], list[dict]]:
    header = guard_inputs(root)
    cars, positions = load_sources(root, header)
    contexts = geometry_context(root, header)
    frames, metrics = {}, []
    for lap in header["laps"]:
        key = lap["event_id"], lap["driver_id"]
        frame, quality = align_lap(cars[key], positions[key], lap, contexts.get(lap["lap_id"]))
        frames[lap["lap_id"]] = frame
        metrics.append(quality)
    bundles = []
    for ref in section_references(root, header):
        try:
            item = longitudinal_inputs(frames[ref["lap_id"]], ref["source_rows"], ref["section_id"])
        except ValueError as exc:
            bundles.append({"section_id": ref["section_id"], "lap_id": ref["lap_id"], "supported": False, "reason": str(exc)})
            continue
        if header["profile"] == "research" and (item.initial_speed_mps != ref["initial_speed_mps"]
                or any(not np.array_equal(getattr(item, k), ref[k]) for k in ("time_s", "throttle", "drs_open"))):
            raise ValueError("R033 aligned longitudinal controls differ from frozen R030 native inputs")
        bundles.append({"lap_id": ref["lap_id"], "supported": True, **{key: value.tolist() if isinstance(value, np.ndarray) else value for key, value in asdict(item).items()}})
    return aggregate_coverage(metrics, bundles, header["profile"]), frames, bundles


def _finish_dataset(root: Path) -> dict:
    files = [Path(__file__), Path(recorded_alignment.__file__), Path(recorded_alignment_audit.__file__),
             Path(longitudinal_dataset.__file__), Path(longitudinal_data.__file__), Path(evidence.__file__), PROTOCOL]
    hashes = {p.name: file_sha256(p) for p in files}
    started = time.perf_counter()
    result, frames, bundles = compute_alignment(root)
    if hashes != {p.name: file_sha256(p) for p in files}:
        raise ValueError("R033 source changed during evaluation")
    (root/"frames").mkdir()
    (root/"sources").mkdir()
    for name, frame in frames.items():
        frame.to_parquet(root/"frames"/(name+".parquet"), index=False)
    for path in files:
        (root/"sources"/path.name).write_bytes(path.read_bytes())
    write_manifest(root/"results.json", result)
    write_manifest(root/"field_contract.json", field_contract())
    write_manifest(root/"longitudinal_inputs.json", bundles)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], text=True, capture_output=True, check=True).stdout.strip()
    return finish_run(root, VERSION, {"schema_version": VERSION+"-dataset", "profile": result["profile"], "input_truth": result["input_truth"],
                                     "commit": commit, "decision": result["decision"], "coverage_gate_passed": result["coverage_gate_passed"],
                                     "task_closure_eligible": result["task_closure_eligible"], "production_promotion": False,
                                     "results_sha256": payload_sha256(result), "input_header_sha256": payload_sha256(read_json(root/"inputs.json")),
                                     "longitudinal_inputs_sha256": payload_sha256(bundles), "implementation_sha256": hashes,
                                     "runtime_seconds": time.perf_counter()-started,
                                     "environment": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__}})


def prepare_recorded_replay(longitudinal: Path, archives: list[Path], output: Path) -> dict:
    """Freeze exact source tables and align all prior laps; no fitting or acquisition."""
    if output.exists():
        raise FileExistsError("R033 output must be fresh")
    if any(output.resolve().is_relative_to(p.resolve()) for p in (longitudinal, *archives)):
        raise ValueError("R033 output must be outside immutable inputs")
    geometry = dataset_guard(longitudinal)
    expected = {s["event_id"]: s["archive_sha256"] for s in geometry["sources"]}
    paths = {}
    # All event headers are guarded before any binary table/cache access.
    for path in archives:
        manifest = read_json(path/"manifest.json")
        q = manifest["query"]
        event = f"F1_{q['year']}_R{q['round_number']:02d}"
        assert_development_event(q["year"], q["round_number"], event_id=event)
        check_seal(manifest)
        if event not in expected or event in paths or q["session"] != "R" or manifest["content_sha256"] != expected[event]:
            raise ValueError("R033 requires four unique frozen original archive headers")
        paths[event] = path
    if set(paths) != set(expected):
        raise ValueError("R033 incomplete frozen native source cohort")
    verified = verify_longitudinal_dataset(longitudinal)
    if verified["summary_sha256"] != DATASET_SEAL or not verified["source_gate_passed"]:
        raise ValueError("R033 requires accepted frozen R030 source dataset")
    for path in paths.values():
        manifest = read_json(path/"manifest.json")
        for driver in ("4", "44"):
            name = f"tables/pos_data/{driver}.parquet"
            if file_sha256(path/name) != manifest["files"][name]["sha256"]:
                raise ValueError("R033 original native position table hash mismatch")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(longitudinal, output/"longitudinal")
    for event, path in paths.items():
        (output/"positions"/event).mkdir(parents=True)
        for driver in ("4", "44"):
            shutil.copyfile(path/f"tables/pos_data/{driver}.parquet", output/"positions"/event/f"{driver}.parquet")
    laps = [lap for track in ("bahrain", "monza") for lap in read_json(longitudinal/"geometry"/f"{track}_lap_metadata.json")]
    write_manifest(output/"inputs.json", {"schema_version": VERSION+"-inputs", "profile": "research", "input_truth": "FASTF1_PARSED_SOURCE", "laps": laps})
    return _finish_dataset(output)


def make_recorded_smoke(output: Path) -> dict:
    if output.exists():
        raise FileExistsError("R033 output must be fresh")
    (output/"simulated_native").mkdir(parents=True)
    laps = []
    for event in EVENT_ROLES:
        for driver in ("4", "44"):
            ct, pt = 100+np.arange(50)*.24, 100.08+np.arange(56)*.22
            base = pd.Timestamp("2023-01-01T00:00:00Z")
            car = pd.DataFrame({"SessionTime": pd.to_timedelta(ct, unit="s"), "Date": base+pd.to_timedelta(ct, unit="s"),
                                "Source": "car", "Speed": 180., "Throttle": 100., "Brake": False, "DRS": 8., "RPM": 11000., "nGear": 6.})
            pos = pd.DataFrame({"SessionTime": pd.to_timedelta(pt, unit="s"), "Date": base+pd.to_timedelta(pt, unit="s"),
                                "Source": "pos", "Status": "OnTrack", "X": np.arange(len(pt))*110., "Y": 40.})
            car.to_parquet(output/"simulated_native"/f"{event}_{driver}_car.parquet", index=False)
            pos.to_parquet(output/"simulated_native"/f"{event}_{driver}_position.parquet", index=False)
            laps.append({"event_id": event, "driver_id": driver, "track_id": EVENT_TRACKS[event], "lap_id": event+"_"+driver+"_smoke",
                         "lap_number": 3, "native_row": 0, "lap_start_s": 100., "lap_end_s": 112., "fixture_source": "SIMULATED_NATIVE_STREAMS"})
    write_manifest(output/"inputs.json", {"schema_version": VERSION+"-inputs", "profile": "smoke", "input_truth": "SIMULATED_NATIVE_STREAMS", "laps": laps})
    return _finish_dataset(output)


def load_recorded_replay(root: Path) -> tuple[dict, dict]:
    guard_inputs(root)
    manifest = verify_inventory(root, VERSION)
    summary, result = read_json(root/"summary.json"), read_json(root/"results.json")
    check_seal(summary)
    header = read_json(root/"inputs.json")
    if (summary["schema_version"] != VERSION+"-dataset" or manifest["summary_sha256"] != summary["content_sha256"]
            or summary["results_sha256"] != payload_sha256(result) or summary["input_header_sha256"] != payload_sha256(header)
            or summary["longitudinal_inputs_sha256"] != payload_sha256(read_json(root/"longitudinal_inputs.json"))
            or summary["profile"] != header["profile"] or summary["input_truth"] != header["input_truth"]
            or result["profile"] != header["profile"] or result["input_truth"] != header["input_truth"]
            or summary["decision"] != result["decision"] or summary["production_promotion"] is not False
            or result["production_promotion"] is not False or summary["coverage_gate_passed"] != result["coverage_gate_passed"]
            or read_json(root/"field_contract.json") != field_contract()
            or summary["task_closure_eligible"] != result["task_closure_eligible"]):
        raise ValueError("R033 stored source/truth/result binding mismatch")
    for name, digest in summary["implementation_sha256"].items():
        if "/" in name or "\\" in name or ":" in name or name in (".", "..") or file_sha256(root/"sources"/name) != digest:
            raise ValueError("R033 implementation snapshot mismatch")
    return summary, result


def verify_recorded_replay(root: Path) -> dict:
    summary, stored = load_recorded_replay(root)
    result, frames, bundles = compute_alignment(root)
    compare_numeric(result, stored)
    compare_numeric(bundles, read_json(root/"longitudinal_inputs.json"))
    maximum = 0.
    for key, frame in frames.items():
        saved = pd.read_parquet(root/"frames"/(key+".parquet"))
        try:
            pd.testing.assert_frame_equal(frame, saved, check_exact=False, atol=1e-9, rtol=0)
        except AssertionError as exc:
            raise ValueError("R033 scientific aligned-frame replay mismatch: "+key) from exc
        for column in frame.select_dtypes(include="number").columns:
            differences = abs(frame[column].to_numpy(float, na_value=np.nan)-saved[column].to_numpy(float, na_value=np.nan))
            if np.isfinite(differences).any():
                maximum = max(maximum, float(np.nanmax(differences)))
    return {"verified": True, "summary_sha256": summary["content_sha256"], "decision": result["decision"],
            "source_laps": len(frames), "native_car_rows": result["totals"]["native_car_rows"],
            "task_closure_eligible": result["task_closure_eligible"], "maximum_native_reload_difference": maximum}


def audit_recorded_replay(root: Path) -> dict:
    summary, result = load_recorded_replay(root)
    header = guard_inputs(root)
    cars, positions = load_sources(root, header)
    audits = []
    for lap in header["laps"]:
        key = lap["event_id"], lap["driver_id"]
        frame = pd.read_parquet(root/"frames"/(lap["lap_id"]+".parquet"))
        audit = audit_aligned_lap(cars[key], positions[key], lap, frame)
        quality = next(m for m in result["per_lap"] if m["lap_id"] == lap["lap_id"])
        if audit["joint_observed_rows"] != quality["joint_observed_rows"] or abs(audit["covered_interval_s"]-quality["covered_interval_s"]) > 1e-8:
            raise ValueError("R033 independent saved coverage disagreement")
        audits.append(audit)
    lap_lookup = {lap["lap_id"]: lap for lap in header["laps"]}
    bundles = read_json(root/"longitudinal_inputs.json")
    references = {r["section_id"]: r for r in section_references(root, header)}
    if len(bundles) != len(references) or {b["section_id"] for b in bundles} != set(references):
        raise ValueError("R033 independent section inventory mismatch")
    for bundle in bundles:
        ref = references[bundle["section_id"]]
        if bundle["lap_id"] != ref["lap_id"]:
            raise ValueError("R033 independent section lap identity mismatch")
        if not bundle["supported"]:
            continue
        if bundle["source_car_rows"] != ref["source_rows"].tolist():
            raise ValueError("R033 independent section native row identity mismatch")
        lap = lap_lookup[bundle["lap_id"]]
        raw = cars[lap["event_id"], lap["driver_id"]].iloc[bundle["source_car_rows"]]
        expected = {"initial_speed_mps": float(raw.Speed.iloc[0])/3.6, "throttle": (raw.Throttle.to_numpy(float)/100).tolist(),
                    "time_s": raw.SessionTime.dt.total_seconds().tolist(),
                    "drs_open": [0 if v in (0, 1, 8) else 1 for v in raw.DRS]}
        for key, values in expected.items():
            compare_numeric(bundle[key], values, "independent recorded inputs/"+key, atol=1e-9, rtol=0)
    if sum(a["rows"] for a in audits) != result["totals"]["native_car_rows"]:
        raise ValueError("R033 independent native row accounting mismatch")
    return {"verified": True, "summary_sha256": summary["content_sha256"], "laps": len(audits), "rows": sum(a["rows"] for a in audits),
            "longitudinal_inputs_checked": sum(b["supported"] for b in bundles),
            "maximum_native_conversion_error": max(a["maximum_native_conversion_error"] for a in audits),
            "full_bicycle_measured_state_control_coverage": 0., "task_closure_eligible": result["task_closure_eligible"]}
