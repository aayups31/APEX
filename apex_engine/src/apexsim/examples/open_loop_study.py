"""R034 immutable matched-horizon report; unavailable full-car scopes stay null."""
from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from apexsim.examples.longitudinal_dataset import load_sections
from apexsim.examples.recorded_replay import guard_inputs, load_recorded_replay, verify_recorded_replay
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research.evidence import check_seal, compare_numeric, finish_run, read_json, verify_inventory
from apexsim.research.longitudinal_data import EVENT_ROLES, LongitudinalSection
from apexsim.research.open_loop_errors import (
    HORIZONS,
    METHODS,
    error_record,
    hierarchical_scores,
    horizon_grid,
    predict_horizon,
    regime_labels,
)

VERSION = "apex-open-loop-errors-v1"
RECORDED_SEAL = "42cede289de897d6153ae3f66d84631de5394911fa979d5df453316b92912620"
DEVELOPMENT_SEAL = "82fc70acfef2a5c730ba908d6659ff35a1730aac1d5663612029c03333081e99"
MODELS_SHA = "598d646b23e1eeb8ea0d6a88a5f2f4d54656ef7af91e4de01597abc2460c713b"
PROTOCOL = Path(__file__).resolve().parents[4]/"research/protocols/OPEN_LOOP_REPLAY_ERRORS.md"
UNAVAILABLE = ["MISSING_MEASURED_STEERING_BODY_STATE", "NO_ALL_REGIME_CAR_CALIBRATION", "NONCONTIGUOUS_NATIVE_LAP_COHORT"]


def inputs(root: Path) -> tuple[dict, list, dict]:
    header = guard_inputs(root/"recorded")  # guard events before binary/inventory reads
    summary, _ = load_recorded_replay(root/"recorded")
    development, models = read_json(root/"development.json"), read_json(root/"models.json")
    check_seal(development)
    if header["profile"] == "research":
        if (summary["content_sha256"] != RECORDED_SEAL or development["content_sha256"] != DEVELOPMENT_SEAL
                or payload_sha256(models) != MODELS_SHA or development["selected"] != "shared_drag"):
            raise ValueError("R034 requires frozen accepted sources and unchanged selected model")
        sections = load_sections(root/"recorded/longitudinal")
    else:
        if development.get("profile") != "smoke" or development["models_sha256"] != payload_sha256(models):
            raise ValueError("R034 simulated model provenance mismatch")
        sections = []
        for lap in header["laps"]:
            frame = pd.read_parquet(root/"recorded/frames"/(lap["lap_id"]+".parquet"))
            t, v = frame.session_time_s.to_numpy(float), frame.speed_mps.to_numpy(float)
            rows = np.arange(5, 18, dtype=np.int64)
            sections.append(LongitudinalSection({**lap, "role": EVENT_ROLES[lap["event_id"]], "section_id": lap["lap_id"]+"_section"},
                                                 t[rows], v[rows], np.ones(13), np.zeros(13, dtype=np.int64), rows, rows,
                                                 t[1:6], v[1:6]))
    return header, sections, models


def native_stint(root: Path, lap: dict, public: bool) -> dict:
    """Retain source membership, including unselected intervening laps; never glue."""
    if not public:
        return {"stint_id": None, "native_stint_lap_numbers": [], "membership_truth": "UNKNOWN_SIMULATED_FIXTURE"}
    table = pd.read_parquet(root/"recorded/longitudinal/native"/lap["event_id"]/"tables/laps.parquet")
    row = table.iloc[lap["native_row"]]
    stint = row.Stint
    if pd.isna(stint):
        return {"stint_id": None, "native_stint_lap_numbers": [], "membership_truth": "UNKNOWN_SOURCE_STINT"}
    numbers = sorted(int(v) for v in table.loc[(table.DriverNumber.astype(str) == lap["driver_id"]) & (table.Stint == stint), "LapNumber"].dropna())
    return {"stint_id": lap["event_id"]+"/"+lap["driver_id"]+"/"+str(int(stint)), "native_stint_lap_numbers": numbers,
            "membership_truth": "FASTF1_PARSED_SOURCE"}


def aggregate_catalog(rows: list[dict], group_key: str) -> list[dict]:
    catalog = []
    for group in sorted({r[group_key] for r in rows}):
        selected = [r for r in rows if r[group_key] == group]
        catalog.append({group_key: group, "mode": "SECTION_AGGREGATE_NOT_CONTINUOUS_REPLAY",
                        "by_horizon_method": {str(h): {m: hierarchical_scores([r for r in selected if r["horizon_s"] == h and r["method"] == m])
                                                      for m in METHODS} for h in HORIZONS}})
    return catalog


def compute(root: Path) -> tuple[dict, dict]:
    header, sections, models = inputs(root)
    public = header["profile"] == "research"
    rows, ledger, arrays = [], [], {}
    laps = {lap["lap_id"]: dict(lap, **native_stint(root, lap, public)) for lap in header["laps"]}
    for section in sections:
        meta = section.metadata
        for h in HORIZONS:
            key = meta["section_id"]+"_h"+str(h)
            supported = h <= float(np.ptp(section.time_s))+1e-9
            ledger.append({"section_id": meta["section_id"], "lap_id": meta["lap_id"], "event_id": meta["event_id"],
                           "driver_id": meta["driver_id"], "horizon_s": h, "supported": supported,
                           "reason": None if supported else "HORIZON_OUTSIDE_FROZEN_SECTION"})
            if not supported:
                continue
            t, u, z, target = horizon_grid(section, h)
            for name, values in (("time", t), ("throttle", u), ("drs", z), ("target", target)):
                arrays[key+"_"+name] = values
            for method in METHODS:
                prediction = predict_horizon(section, h, method, models)
                arrays[key+"_"+method] = prediction
                rows.append({"section_id": meta["section_id"], "lap_id": meta["lap_id"], "event_id": meta["event_id"],
                             "driver_id": meta["driver_id"], "stint_id": laps[meta["lap_id"]]["stint_id"] or "UNKNOWN/"+meta["lap_id"],
                             "role": EVENT_ROLES[meta["event_id"]], "regimes": regime_labels(section), "horizon_s": h, "method": method,
                             **error_record(t, target, prediction)})
    lap_catalog = []
    for lap in laps.values():
        frame = pd.read_parquet(root/"recorded/frames"/(lap["lap_id"]+".parquet"))
        t, v = frame.session_time_s.to_numpy(float), frame.speed_mps.to_numpy(float)
        t = t-t[0]
        diagnostic = error_record(t, v, np.full(len(v), v[0]))
        lap_catalog.append({**lap, "sampled_duration_s": float(t[-1]), "source_lap_duration_s": lap["lap_end_s"]-lap["lap_start_s"],
                            "sampled_lap_constant_speed_diagnostic": diagnostic, "diagnostic_truth": "UNVALIDATED_KINEMATIC_BASELINE",
                            "supported_sections": sum(s.metadata["lap_id"] == lap["lap_id"] for s in sections),
                            "full_lap_physics_error": None, "full_lap_abstention_reasons": UNAVAILABLE,
                            "mode": "SECTION_AGGREGATE_NOT_CONTINUOUS_REPLAY"})
    stint_catalog = []
    for key in sorted({r["stint_id"] for r in lap_catalog if r["stint_id"] is not None}):
        selected = [r for r in lap_catalog if r["stint_id"] == key]
        numbers = sorted(r["lap_number"] for r in selected)
        native = selected[0]["native_stint_lap_numbers"]
        stint_catalog.append({"stint_id": key, "selected_laps": numbers, "native_stint_laps": native,
                              "missing_native_laps": sorted(set(native)-set(numbers)), "complete_source_stint": numbers == native,
                              "full_stint_physics_error": None, "abstention_reasons": UNAVAILABLE,
                              "mode": "SECTION_AGGREGATE_NOT_CONTINUOUS_REPLAY"})
    scores = {role: {str(h): {m: hierarchical_scores([r for r in rows if r["role"] == role and r["horizon_s"] == h and r["method"] == m])
                             for m in METHODS} for h in HORIZONS} for role in ("train", "validation", "test")}
    regimes = {regime: {str(h): {m: hierarchical_scores([r for r in rows if r["role"] == "test" and regime in r["regimes"]
                                                        and r["horizon_s"] == h and r["method"] == m]) for m in METHODS} for h in HORIZONS}
               for regime in sorted({label for r in rows for label in r["regimes"]})}
    supported = sum(r["supported"] for r in ledger)
    gate = (len(ledger) == len(sections)*len(HORIZONS) and len(rows) == supported*len(METHODS)
            and all({r["driver_id"] for r in rows if r["role"] == "test" and r["horizon_s"] == h} == {"4", "44"} for h in HORIZONS))
    eligible = public and gate and len(sections) == 150 and len(laps) == 88
    result = {"profile": header["profile"], "decision": "ACCEPT_SCOPED_ERROR_REPORT" if eligible else "SIMULATED_EXECUTION_ONLY" if not public else "REJECT_ERROR_REPORT",
              "task_closure_eligible": eligible, "report_gate_passed": gate, "production_promotion": False,
              "sections": len(sections), "source_laps": len(laps), "supported_horizon_cases": supported, "abstained_horizon_cases": len(ledger)-supported,
              "target_truth": "RECONSTRUCTED_ENDPOINT_FROM_NATIVE_SPEED", "selected": "shared_drag", "refitted": False,
              "scores": scores, "test_regimes": regimes, "support_ledger": ledger, "records": rows, "lap_catalog": lap_catalog,
              "stint_catalog": stint_catalog, "lap_section_aggregates": aggregate_catalog(rows, "lap_id"),
              "stint_section_aggregates": aggregate_catalog(rows, "stint_id"), "complete_measured_car_replay": False,
              "unsupported_physical_regimes": ["BRAKING", "CORNERING", "LOW_SPEED", "CONTINUOUS_LAP", "CONTINUOUS_STINT"],
              "limitations": ["Reused development events, not protected benchmark", "Generic full-car states/control unknown",
                              "Section aggregates are not continuous lap/stint predictions", "Sampled-lap diagnostic has native gaps and no physics validity"]}
    return result, arrays


def run_open_loop_study(recorded: Path, development: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("R034 output must be fresh")
    if any(output.resolve().is_relative_to(p.resolve()) for p in (recorded, development)):
        raise ValueError("R034 output must be outside inputs")
    verify_recorded_replay(recorded)
    output.mkdir(parents=True)
    shutil.copytree(recorded, output/"recorded")
    for source, target in (("summary.json", "development.json"), ("models.json", "models.json")):
        shutil.copyfile(development/source, output/target)
    inputs(output)
    paths = [Path(__file__), Path(__import__("apexsim.research.open_loop_errors", fromlist=["__file__"]).__file__),
             Path(__import__("apexsim.research.open_loop_audit", fromlist=["__file__"]).__file__), PROTOCOL]
    hashes = {p.name: file_sha256(p) for p in paths}
    result, arrays = compute(output)
    if hashes != {p.name: file_sha256(p) for p in paths}:
        raise ValueError("R034 implementation changed during evaluation")
    (output/"sources").mkdir()
    for p in paths:
        shutil.copyfile(p, output/"sources"/p.name)
    np.savez_compressed(output/"predictions.npz", **arrays)
    write_manifest(output/"results.json", result)
    return finish_run(output, VERSION, {"schema_version": VERSION, "profile": result["profile"], "decision": result["decision"],
                                       "task_closure_eligible": result["task_closure_eligible"], "production_promotion": False,
                                       "results_sha256": payload_sha256(result), "models_sha256": payload_sha256(read_json(output/"models.json")),
                                       "recorded_sha256": read_json(recorded/"summary.json")["content_sha256"], "implementation_sha256": hashes,
                                       "commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip(),
                                       "environment": {"python": platform.python_version(), "numpy": np.__version__}})


def load_study(root: Path) -> tuple[dict, dict]:
    inputs(root)
    manifest = verify_inventory(root, VERSION)
    summary, result = read_json(root/"summary.json"), read_json(root/"results.json")
    check_seal(summary)
    if (manifest["summary_sha256"] != summary["content_sha256"] or summary["schema_version"] != VERSION
            or summary["results_sha256"] != payload_sha256(result) or summary["models_sha256"] != payload_sha256(read_json(root/"models.json"))
            or summary["recorded_sha256"] != read_json(root/"recorded/summary.json")["content_sha256"]
            or any(summary[k] != result[k] for k in ("profile", "decision", "task_closure_eligible", "production_promotion"))
            or result["production_promotion"] is not False):
        raise ValueError("R034 source/result binding mismatch")
    for name, digest in summary["implementation_sha256"].items():
        if Path(name).name != name or ":" in name or "\\" in name or file_sha256(root/"sources"/name) != digest:
            raise ValueError("R034 implementation snapshot mismatch")
    return summary, result


def verify_open_loop_study(root: Path) -> dict:
    summary, saved = load_study(root)
    verify_recorded_replay(root/"recorded")
    result, arrays = compute(root)
    compare_numeric(result, saved)
    maximum = 0.
    with np.load(root/"predictions.npz", allow_pickle=False) as stored:
        if set(stored.files) != set(arrays):
            raise ValueError("R034 prediction catalog mismatch")
        for key, values in arrays.items():
            compare_numeric(stored[key].tolist(), values.tolist(), key)
            maximum = max(maximum, float(np.max(abs(stored[key]-values))))
    return {"verified": True, "summary_sha256": summary["content_sha256"], "task_closure_eligible": result["task_closure_eligible"],
            "maximum_replay_difference": maximum, "sections": result["sections"], "source_laps": result["source_laps"]}
