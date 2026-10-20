"""Frozen R029 v2 native-support study, synthetic controls and scientific replay."""
from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.examples import track_reconstruction_demo
from apexsim.examples.track_reconstruction_demo import _annotations, _close_values, _save_artifacts
from apexsim.provenance import file_sha256, payload_sha256
from apexsim.research import position_laps, reference_geometry, supported_geometry
from apexsim.research.position_laps import EVENT_TRACKS, MASK_SEALS, extract_position_lap
from apexsim.research.reference_geometry import GeometryConfig, ReferenceCurve
from apexsim.research.supported_geometry import fit_supported_case

FROZEN_LAPS = {
    ("F1_2024_R01", "4"): list(range(15, 25)),
    ("F1_2024_R01", "44"): [2, 3, 4, 5, 6, 7, 8, 9, 14, 15],
    ("F1_2024_R16", "4"): list(range(2, 12)),
    ("F1_2024_R16", "44"): list(range(2, 12)),
    ("F1_2023_R01", "4"): [7, 8, 9, 19, 20, 21],
    ("F1_2023_R01", "44"): list(range(6, 12)),
    ("F1_2023_R14", "4"): list(range(9, 15)),
    ("F1_2023_R14", "44"): list(range(5, 11)),
}
COUNTS = {"research_v2": (10, 10, 12), "development_v2": (10, 10, 0), "smoke_v2": (4, 3, 6)}
COUNTS.update({"research_v2_1": (10, 10, 12), "development_v2_1": (10, 10, 0), "smoke_v2_1": (4, 3, 6)})


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _decision(profile: str, passed: bool) -> str:
    if profile.startswith("smoke_"):
        return "SIMULATED_EXECUTION_ONLY"
    if profile.startswith("development_"):
        return "DEVELOPMENT_ONLY"
    partial = profile.endswith("_v2_1")
    if passed:
        return "PASS_FROZEN_OBSERVED_SUPPORT_GEOMETRY"+("_V2_1" if partial else "")
    return "REJECT_FROZEN_V2_1_GEOMETRY_GATES" if partial else "REJECT_FROZEN_V2_GEOMETRY_GATES"


def select_v2_laps(mask: dict, event: str, driver: str, role: str) -> list[dict]:
    rows = sorted([r for s in mask["segments"] if s["event_id"] == event and s["driver"] == driver for r in s["rows"]], key=lambda r: r["lap"])
    selected = rows[:10] if event[3:7] == "2024" else rows[3:9]
    if [r["lap"] for r in selected] != FROZEN_LAPS[(event, driver)]:
        raise ValueError("R029 v2 frozen source selection differs; replacement forbidden")
    return [{"event_id": event, "driver_id": driver, "lap_number": r["lap"], "native_row": r["native_row"],
             "track_id": EVENT_TRACKS[event], "role": role} for r in selected]


def run_track_reconstruction_v2(archives: list[Path], mask_2024: Path, mask_2023: Path, output: Path, *, stage: str = "research", observed_boundaries: bool = False) -> dict:
    """Fit observed vertices with explicit source holes; public acceptance requires all gates."""
    if stage not in ("research", "development"):
        raise ValueError("R029 v2 stage must be research or development")
    if output.exists():
        raise FileExistsError("R029 v2 output must be fresh")
    if any(output.resolve().is_relative_to(p.resolve()) for p in [*archives, mask_2024, mask_2023]):
        raise ValueError("R029 v2 output must be outside immutable inputs")
    sources = {}
    for path in archives:
        query = _read(path/"manifest.json")["query"]
        event = f"F1_{query['year']}_R{query['round_number']:02d}"
        assert_development_event(query["year"], query["round_number"], event_id=event)
        if event not in EVENT_TRACKS or event in sources or query["session"] != "R":
            raise ValueError("R029 v2 exact unique preregistered race archives required")
        sources[event] = path, verify_fastf1_archive(path)
    if set(sources) != set(EVENT_TRACKS):
        raise ValueError("R029 v2 requires all four preregistered source archives")
    masks = {2024: _read(mask_2024), 2023: _read(mask_2023)}
    for year, mask in masks.items():
        if mask.get("content_sha256") != MASK_SEALS[year] or mask["content_sha256"] != payload_sha256({k:v for k,v in mask.items() if k != "content_sha256"}):
            raise ValueError("R029 v2 requires original frozen eligibility masks")
    watched = [mask_2024, mask_2023, Path(__file__), Path(position_laps.__file__), Path(reference_geometry.__file__),
               Path(supported_geometry.__file__), Path(track_reconstruction_demo.__file__)]
    watched += [path/"manifest.json" for path,_ in sources.values()]
    before = {str(p): file_sha256(p) for p in watched}
    profile = stage+("_v2_1" if observed_boundaries else "_v2")
    cases, inputs = {}, {}
    for track, current, older in (("bahrain", "F1_2024_R01", "F1_2023_R01"), ("monza", "F1_2024_R16", "F1_2023_R14")):
        traces, native = [], {}
        for event in ((current, older) if stage == "research" else (current,)):
            path, manifest = sources[event]
            mask = masks[int(event[3:7])]
            binding = next(s for s in mask["sources"] if s["event_id"] == event)
            if binding["archive_sha256"] != manifest["content_sha256"]:
                raise ValueError("R029 v2 source/mask archive binding mismatch")
            native[event] = pd.read_parquet(path/"tables/laps.parquet")
            for driver in ("4", "44"):
                positions = pd.read_parquet(path/f"tables/pos_data/{driver}.parquet")
                native[event+"_"+driver] = positions
                role = ("train" if driver == "4" else "validation") if event == current else "test"
                for selection in select_v2_laps(mask, event, driver, role):
                    traces.append(extract_position_lap(native[event], positions, selection, allow_interior_gaps=True,
                                                       observed_boundaries=observed_boundaries and role == "test"))
        result, arrays = fit_supported_case(traces, track, expected_counts=COUNTS[profile], refine_test_pose=observed_boundaries)
        anchor = next(m for m in result["lap_metrics"] if m["lap_id"] == result["frame_anchor_lap_id"])
        curve = ReferenceCurve(arrays["coefficients"], GeometryConfig(**result["selected_config"]), track)
        result["annotations"] = _annotations(curve, traces, native[current], native[current+"_4"], anchor["registration"])
        cases[track] = result
        inputs[track] = {"laps": traces, "arrays": arrays}
    for path, original in sources.values():
        if verify_fastf1_archive(path)["content_sha256"] != original["content_sha256"]:
            raise ValueError("R029 v2 source changed during study")
    if before != {str(p): file_sha256(p) for p in watched}:
        raise ValueError("R029 v2 code/input changed during study")
    passed = stage == "research" and all(c["gate"]["passed"] for c in cases.values())
    summary = {"schema_version": "apex-reference-geometry-study-v2.1" if observed_boundaries else "apex-reference-geometry-study-v2", "classification": "ADAPTATION", "profile": profile,
               "R029_complete": passed, "task_closure_eligible": passed, "promotion": False,
               "decision": _decision(profile, passed),
               "cases": cases, "sources": [{"event_id": e, "archive_sha256": m["content_sha256"], "manifest": m} for e,(_,m) in sources.items()],
               "mask_sha256": {str(y): m["content_sha256"] for y,m in masks.items()},
               "implementation_sha256": {p.name: before[str(p)] for p in watched[2:7]},
               "environment": {"python": platform.python_version(), "numpy": np.__version__, "scipy": __import__("scipy").__version__},
               "prior_v1_decision": "REJECT_FROZEN_SOURCE_SUPPORT",
               "limitations": ["Reference racing trace, not surveyed road centerline/boundaries", "Rigid full-lap registration evaluates shape, not absolute or online localization",
                               "Missing intervals stay unsupported; chord phase is reconstructed", "Coarse supported curvature is a proxy; no surveyed curvature truth",
                               "Ten-lap sensitivity is descriptive, not calibrated confidence; two development circuits only", "Official DRS, road width/elevation, surveyed centerline and full pit route UNKNOWN",
                               "Prior development-event reuse disclosed; reserved benchmarks untouched", "No vehicle/world-model validation, production or R3 maturity promotion"]}
    if observed_boundaries:
        summary["prior_strict_v2_decision"] = "REJECT_STRICT_V2_BOUNDARY_SUPPORT"
        summary["limitations"].append("Unsupported test anchors UNKNOWN; >=98% retained time span; errors conditional on optimized rigid pose")
    summary["content_sha256"] = payload_sha256(summary)
    _save_artifacts(output, summary, inputs)
    return summary


def verify_track_reconstruction_v2(output: Path) -> dict:
    """Verify inventory/hashes, refit every stored lap and replay all arrays and decisions."""
    manifest = _read(output/"manifest.json")
    if manifest.get("schema_version") != "apex-reference-geometry-manifest-v1" or manifest["content_sha256"] != payload_sha256({k:v for k,v in manifest.items() if k != "content_sha256"}):
        raise ValueError("R029 v2 artifact manifest/schema mismatch")
    if set(manifest["files"]) != {p.name for p in output.iterdir()}-{"manifest.json"}:
        raise ValueError("R029 v2 artifact inventory mismatch")
    for name, item in manifest["files"].items():
        if Path(name).name != name or file_sha256(output/name) != item["sha256"] or (output/name).stat().st_size != item["bytes"]:
            raise ValueError("R029 v2 artifact hash mismatch")
    summary = _read(output/"summary.json")
    if summary["content_sha256"] != manifest["summary_sha256"] or summary["content_sha256"] != payload_sha256({k:v for k,v in summary.items() if k != "content_sha256"}) or summary.get("schema_version") not in ("apex-reference-geometry-study-v2", "apex-reference-geometry-study-v2.1"):
        raise ValueError("R029 v2 summary hash/schema mismatch")
    profile = summary["profile"]
    if profile not in COUNTS:
        raise ValueError("R029 v2 profile mismatch")
    partial = profile.endswith("_v2_1")
    smoke = profile.startswith("smoke_")
    research = profile.startswith("research_")
    if (summary["schema_version"] == "apex-reference-geometry-study-v2.1") != partial:
        raise ValueError("R029 v2 protocol/profile mismatch")
    if not smoke and (set(summary["cases"]) != {"bahrain", "monza"} or len(summary["sources"]) != 4 or {s["event_id"] for s in summary["sources"]} != set(EVENT_TRACKS) or summary["mask_sha256"] != {str(y):s for y,s in MASK_SEALS.items()}):
        raise ValueError("R029 v2 research source/cohort mismatch")
    if smoke and (summary["sources"] or summary["mask_sha256"] or summary.get("input_truth") != "SIMULATED"):
        raise ValueError("R029 v2 simulated source identity mismatch")
    for source in summary["sources"]:
        native = source["manifest"]
        q = native["query"]
        assert_development_event(q["year"], q["round_number"], event_id=source["event_id"])
        if native["content_sha256"] != source["archive_sha256"] or native["content_sha256"] != payload_sha256({k:v for k,v in native.items() if k != "content_sha256"}):
            raise ValueError("R029 v2 native source manifest mismatch")
    for track, stored in summary["cases"].items():
        metadata = _read(output/f"{track}_lap_metadata.json")
        if not smoke:
            cohorts = {}
            for m in metadata:
                event, driver = m["event_id"], m["driver_id"]
                if event not in EVENT_TRACKS or driver not in ("4", "44") or EVENT_TRACKS[event] != track:
                    raise ValueError("R029 v2 frozen lap identity mismatch")
                role = ("train" if driver == "4" else "validation") if event[3:7] == "2024" else "test"
                if role != m["role"]:
                    raise ValueError("R029 v2 lap role mismatch")
                cohorts.setdefault((event, driver), []).append(m["lap_number"])
            expected = {k:v for k,v in FROZEN_LAPS.items() if EVENT_TRACKS[k[0]] == track and (research or k[0][3:7] == "2024")}
            if cohorts != expected:
                raise ValueError("R029 v2 frozen lap cohort mismatch")
        with np.load(output/f"{track}_lap_inputs.npz", allow_pickle=False) as raw:
            laps = []
            for m in metadata:
                key = m["lap_id"]
                xy, time = raw[key+"_xy"], raw[key+"_time"]
                if not np.isfinite(time).all() or np.any(np.diff(time) <= 0) or not np.isfinite(xy).all():
                    raise ValueError("R029 v2 native input quality mismatch")
                if not smoke:
                    if m["native_samples"] < 100 or len(xy) != m["native_samples"]+m["boundary_samples"]:
                        raise ValueError("R029 v2 native sample count mismatch")
                    if partial and m["role"] == "test":
                        coverage = (time[-1]-time[0])/m["lap_duration_s"]
                        known = sum(a["status"] == "SUPPORTED_BOUNDED_ANCHOR" for a in m["boundary_status"])
                        if coverage < .98 or not np.isclose(coverage, m["observed_time_fraction"], rtol=1e-10, atol=1e-9) or known != m["boundary_samples"] or not np.isclose(time[0]-m["lap_start_s"], m["unobserved_start_s"]) or not np.isclose(m["lap_end_s"]-time[-1], m["unobserved_end_s"]):
                            raise ValueError("R029 v2 partial native timing replay mismatch")
                    if m["raw_closure_gap_m"] is None:
                        if not partial or m["role"] != "test" or m["boundary_samples"] >= 2 or m["observed_time_fraction"] < .98 or not np.isclose(np.linalg.norm(xy[-1]-xy[0]), m["observed_endpoint_gap_m"]):
                            raise ValueError("R029 v2 partial boundary support mismatch")
                    elif m["boundary_samples"] != 2 or not np.isclose(np.linalg.norm(xy[-1]-xy[0]), m["raw_closure_gap_m"]) or m["raw_closure_gap_m"] > 30:
                        raise ValueError("R029 v2 source closure mismatch")
                laps.append({"metadata": m, "xy_m": xy, "time_s": time, "native_parents": raw[key+"_native_parents"], "interval_supported": np.diff(time) <= .75})
        replay, arrays = fit_supported_case(laps, track, expected_counts=COUNTS[profile], refine_test_pose=partial)
        for name in ("selected_config", "selected_candidate_index", "candidate_selection", "length_m", "gate", "lap_metrics", "coverage", "sensitivity"):
            if not _close_values(replay[name], stored[name]):
                raise ValueError(f"R029 v2 scientific diagnostics replay mismatch: {name}")
        with np.load(output/f"{track}_geometry_predictions.npz", allow_pickle=False) as predictions:
            if set(predictions.files) != set(arrays):
                raise ValueError("R029 v2 prediction inventory mismatch")
            for name, values in arrays.items():
                if not np.allclose(predictions[name], values, rtol=1e-10, atol=1e-9, equal_nan=True):
                    raise ValueError(f"R029 v2 scientific array replay mismatch: {name}")
        if "annotations" in stored:
            curve = ReferenceCurve(arrays["coefficients"], GeometryConfig(**replay["selected_config"]), track)
            for name in ("width_m", "elevation_m", "official_drs_zones", "pit_lane_route", "surveyed_centerline"):
                if stored["annotations"][name]["status"] != "UNKNOWN" or stored["annotations"][name]["value"] is not None:
                    raise ValueError("R029 v2 unsupported ancillary claim")
            for annotation in stored["annotations"].values():
                for observation in annotation.get("observations", []):
                    if "registered_xy_m" in observation:
                        projection = curve.project(np.array([observation["registered_xy_m"]]))
                        if not np.isclose(projection["station_m"][0], observation["station_m"], atol=1e-8, rtol=1e-10) or not np.isclose(projection["distance_m"][0], observation["distance_to_reference_m"], atol=1e-8):
                            raise ValueError("R029 v2 annotation projection mismatch")
    eligible = research and all(c["gate"]["passed"] for c in summary["cases"].values())
    if summary["task_closure_eligible"] != eligible or summary["R029_complete"] != eligible or summary["promotion"]:
        raise ValueError("R029 v2 acceptance/promotion mismatch")
    expected_decision = _decision(profile, eligible)
    if summary["decision"] != expected_decision:
        raise ValueError("R029 v2 decision mismatch")
    return {"verified": True, "task_closure_eligible": eligible, "decision": summary["decision"], "summary_sha256": summary["content_sha256"]}


def run_track_reconstruction_v2_smoke(output: Path, *, observed_boundaries: bool = False) -> dict:
    """Simulated complementary missing intervals; never public source/geometry acceptance."""
    if output.exists():
        raise FileExistsError("R029 v2 smoke output must be fresh")
    cases, inputs = {}, {}
    for track, radii in (("sim_circle", (500., 500.)), ("sim_ellipse", (600., 400.))):
        laps = []
        time = np.linspace(0., 90., 257)
        theta = time/90.*2*np.pi
        original = np.column_stack((radii[0]*np.cos(theta), radii[1]*np.sin(theta)))
        for i, role in enumerate(("train",)*4+("validation",)*3+("test",)*6):
            keep = np.ones(len(time), bool)
            lo = 20+40*(i%4)
            keep[lo:lo+3] = False
            partial_test = observed_boundaries and i == 7
            if partial_test:
                keep[-2:] = False
            angle = .02*i
            rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
            xy = original[keep]@rotation+np.array([2.*i, -3.*i])
            metadata = {"lap_id": f"{track}_{i}", "role": role, "driver_id": "4" if role == "train" else "44", "lap_number": i+1,
                        "track_id": track, "input_truth": "SIMULATED", "raw_closure_gap_m": None if partial_test else float(np.linalg.norm(xy[-1]-xy[0]))}
            if partial_test:
                metadata.update(boundary_samples=1, observed_time_fraction=float((time[keep][-1]-time[keep][0])/90.),
                                observed_endpoint_gap_m=float(np.linalg.norm(xy[-1]-xy[0])), boundary_truth="SIMULATED_PARTIAL_OBSERVATION")
            laps.append({"metadata": metadata, "xy_m": xy, "time_s": time[keep], "interval_supported": np.diff(time[keep]) <= .75,
                         "native_parents": np.column_stack((np.flatnonzero(keep), np.flatnonzero(keep)))})
        result, arrays = fit_supported_case(laps, track, expected_counts=COUNTS["smoke_v2"], refine_test_pose=observed_boundaries)
        cases[track], inputs[track] = result, {"laps": laps, "arrays": arrays}
    summary = {"schema_version": "apex-reference-geometry-study-v2.1" if observed_boundaries else "apex-reference-geometry-study-v2", "classification": "ADAPTATION", "profile": "smoke_v2_1" if observed_boundaries else "smoke_v2",
               "input_truth": "SIMULATED", "sources": [], "mask_sha256": {}, "cases": cases,
               "R029_complete": False, "task_closure_eligible": False, "promotion": False, "decision": "SIMULATED_EXECUTION_ONLY"}
    summary["content_sha256"] = payload_sha256(summary)
    _save_artifacts(output, summary, inputs)
    return summary
