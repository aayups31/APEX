"""R038 second calibration and independent-event confirmation."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.openf1_archive import verify_openf1_archive
from apexsim.examples.imitation_study import initial_speed
from apexsim.examples.recovery_study import load_recovery_inputs
from apexsim.examples.support_study import FAULTS, HARD, decision_metrics, load_support_detector
from apexsim.examples.support_study import hashes as original_source_hashes
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.closed_loop import compare_continuous_paths, run_continuous
from apexsim.research.closed_loop_audit import audit_continuous
from apexsim.research.evidence import (
    check_seal,
    compare_numeric,
    finish_run,
    read_json,
    seal,
    verify_inventory,
)
from apexsim.research.support_audit import audit_switches
from apexsim.research.support_fallback import RuntimeController

VERSION = "apex-support-confirmation-v2"
PROTOCOL = Path(__file__).resolve().parents[4]/"research/protocols/SUPPORT_FALLBACK_V2.md"


def source_hashes() -> dict:
    return {p.name: file_sha256(p) for p in (Path(__file__), PROTOCOL)}


def calibration(detector: Path) -> dict:
    parent, envelope = load_support_detector(detector)
    if parent["implementation_sha256"] != original_source_hashes():
        raise ValueError("R038 v1 controller source changed")
    inputs = detector/"recovery/inputs"
    _, development, header, maps, pace = load_recovery_inputs(inputs)
    model = development["models"][development["selected"]]
    rows = []
    for event in ("F1_2023_R01", "F1_2023_R14", "F1_2024_R01"):
        case = next(c for c in header["cases"] if c["event_id"] == event and c["role"] in ("train", "validation"))
        speed = initial_speed(inputs/"reference/development/dataset", header, case, ("train", "validation"))
        print("Calibrating on", case["lap_id"], flush=True)
        result, arrays = run_continuous(maps[case["track_id"]], pace, speed, "learned",
                                        development["selected_lead_s"], model, laps=3)
        if not result["passed"]:
            raise ValueError(f"Calibration trajectory failed for {case['lap_id']}")
        scores = np.max(abs((arrays["features"]-envelope["center"])/envelope["half_range"]), axis=1)
        rows.append({"lap_id": case["lap_id"], "event_id": event, "role": case["role"],
                     "commands": len(scores), "score_q999": float(np.quantile(scores, .999))})
    original = envelope["cutoff"]
    cutoff = max(original, 1.10*max(r["score_q999"] for r in rows))
    if cutoff > 2*original:
        raise ValueError("Development calibration exceeds the frozen cutoff ceiling")
    return seal({"schema_version": VERSION+"-calibration", "parent_sha256": parent["content_sha256"],
                   "source_hashes": source_hashes(), "development_cases": rows, "test_outcomes_used": False,
                   "original_cutoff": original, "envelope": {**envelope, "cutoff": cutoff}})


def calibrate(detector: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    frozen = calibration(detector)
    write_manifest(output, frozen)
    return frozen


def cohort(archive: Path) -> tuple[str, list[dict]]:
    assert_development_event(2025, 16, event_id="F1_2025_R16")
    manifest = verify_openf1_archive(archive)
    if manifest["query"]["session_key"] != 9908:
        raise ValueError("R038 v2 requires the frozen 2025 Monza qualifying session")

    def records(name):
        with (archive/"tables"/(name+".jsonl")).open(encoding="utf-8") as handle:
            return [json.loads(line) for line in handle]

    laps = records("laps")
    car = pd.DataFrame(records("car_data"))
    car["timestamp"] = pd.to_datetime(car["date"], format="ISO8601", utc=True)
    selected = []
    for driver in (4, 44):
        samples = car[car.driver_number == driver].sort_values("timestamp", kind="stable")
        eligible = sorted((lap for lap in laps if lap["driver_number"] == driver
                           and lap.get("date_start") and (lap.get("lap_duration") or 0) > 0),
                          key=lambda lap: pd.Timestamp(lap["date_start"]))
        for lap in eligible:
            start = pd.Timestamp(lap["date_start"])
            after = samples[samples.timestamp >= start].head(1)
            if after.empty:
                continue
            sample = after.iloc[0]
            delay = (sample.timestamp-start).total_seconds()
            speed = float(sample.speed)/3.6
            if delay > 1 or not np.isfinite(speed) or not 5 <= speed <= 110:
                continue
            selected.append({"lap_id": f"F1_2025_R16_{driver}_{lap['lap_number']}", "driver_id": str(driver),
                             "initial_speed_mps": speed, "source_date": sample.date, "delay_s": delay})
            if sum(row["driver_id"] == str(driver) for row in selected) == 2:
                break
    if len(selected) != 4 or len({row["lap_id"] for row in selected}) != 4:
        raise ValueError("R038 v2 requires four distinct observed initial conditions")
    return manifest["content_sha256"], selected


class ConfirmationController(RuntimeController):
    """Keep the original raw feature-fault amplitude when the cutoff changes."""

    def __init__(self, actor, scenario, envelope, model, original_cutoff):
        super().__init__(actor, scenario, envelope, model)
        self.feature_offset = 10*envelope["half_range"][2]*(original_cutoff-envelope["cutoff"])

    def __call__(self, state, track, profile, station, lateral, previous, index, nominal, row, log):
        starts = self.next_event < 2 and station >= (1.25, 2.60)[self.next_event]*track.length_m
        if self.fault == "feature_shift" and (self.remaining > 0 or starts):
            row = row.copy()
            row[2] += self.feature_offset
        return super().__call__(state, track, profile, station, lateral, previous, index, nominal, row, log)


def compute(detector: Path, frozen_path: Path, archive: Path) -> tuple[dict, dict]:
    parent, original = load_support_detector(detector)
    if parent["implementation_sha256"] != original_source_hashes():
        raise ValueError("R038 v1 controller source changed")
    frozen = read_json(frozen_path)
    check_seal(frozen)
    envelope = frozen["envelope"]
    cutoff = max(original["cutoff"], 1.10*max(r["score_q999"] for r in frozen["development_cases"]))
    if (frozen["schema_version"] != VERSION+"-calibration" or frozen["source_hashes"] != source_hashes()
            or frozen["parent_sha256"] != parent["content_sha256"] or frozen["test_outcomes_used"] is not False
            or frozen["original_cutoff"] != original["cutoff"] or envelope != {**original, "cutoff": cutoff}
            or cutoff > 2*original["cutoff"]):
        raise ValueError("R038 v2 detector freeze mismatch")
    archive_hash, conditions = cohort(archive)
    _, development, _, maps, pace = load_recovery_inputs(detector/"recovery/inputs")
    model = development["models"][development["selected"]]
    track = maps["monza"]
    cases, arrays, refinements, nominal_checks = [], {}, [], []
    for condition in conditions:
        local = {}
        recipes = [(a, "nominal", .02) for a in ("unguarded", "guarded", "transparent")]
        recipes += [(a, f, .02) for f in FAULTS for a in ("unguarded", "guarded")]
        recipes += [("guarded", "residual_bias", .01), *(("guarded", f, .02) for f in HARD)]
        for actor, scenario, step in recipes:
            key = f"{actor}__{condition['lap_id']}__{scenario}__{step}"
            print("Running", key, flush=True)
            controller = ConfirmationController(actor, scenario, envelope, model, original["cutoff"])
            kind = "transparent" if actor == "transparent" else "learned"
            row, path = run_continuous(track, pace, condition["initial_speed_mps"], kind,
                                       development["selected_lead_s"], model, laps=3, max_step=step, controller=controller)
            row.update(case_id=key, actor=actor, scenario=scenario, max_step_s=step,
                       track_length_m=track.length_m, track_id="monza", event_id="F1_2025_R16",
                       supervision=decision_metrics(row), **condition)
            cases.append(row)
            arrays.update({key+"__"+name: value for name, value in path.items()})
            local[actor, scenario, step] = row, path
        guarded = local["guarded", "nominal", .02][0]
        baseline = local["unguarded", "nominal", .02][0]
        nominal_checks.append(bool(guarded["completed"] and baseline["completed"]
            and guarded["completion_time_s"] <= 1.01*baseline["completion_time_s"]
            and guarded["supervision"]["fallback_fraction"] <= .05
            and np.mean([v["rmse_m"]**2 for v in guarded["laps"]])**.5
            <= max(.15, 1.1*np.mean([v["rmse_m"]**2 for v in baseline["laps"]])**.5)))
        coarse, a = local["guarded", "residual_bias", .02]
        fine, b = local["guarded", "residual_bias", .01]
        comparison = compare_continuous_paths(a, b)
        finish = abs(coarse["completion_time_s"]-fine["completion_time_s"]) if coarse["completed"] and fine["completed"] else None
        refinements.append({**comparison, "finish_difference_s": finish,
                            "passed": comparison["passed"] and finish is not None and finish <= .2})
    guarded = [r for r in cases if r["actor"] in ("guarded", "transparent") and r["scenario"] not in HARD]
    faulted = [r for r in guarded if r["scenario"] in FAULTS]
    hard = [r for r in cases if r["scenario"] in HARD]
    audit = audit_continuous(cases, arrays, actor="guarded", full_scenario="residual_bias", progress=print)
    switches = audit_switches(cases, arrays, print)
    gate = {"nominal": all(nominal_checks), "stable": all(r["passed"] for r in guarded),
            "faults": len(faulted) == 16 and all(r["supervision"]["first_fault_detections"] == 2
                and r["supervision"]["all_faulted_actions_rejected"] and r["supervision"]["returned_to_learned"] for r in faulted),
            "hard": len(hard) == 12 and all(r["abstained"] and r["progress_m"] == 0 and len(r["decisions"]) == 1 for r in hard),
            "refinement": all(r["passed"] for r in refinements), "independent": audit["passed"] and switches["passed"]}
    return {"archive_sha256": archive_hash, "calibration_sha256": frozen["content_sha256"], "conditions": conditions,
            "cases": cases, "refinements": refinements, "gate": gate, "independent_audit": audit,
            "switch_audit": switches, "passed": len(cases) == 52 and all(gate.values())}, arrays


def run(detector: Path, frozen: Path, archive: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    result, arrays = compute(detector, frozen, archive)
    write_manifest(output/"results.json", result)
    np.savez_compressed(output/"trajectories.npz", **arrays)
    return finish_run(output, VERSION, {"schema_version": VERSION, "source_hashes": source_hashes(),
                      "calibration_sha256": result["calibration_sha256"], "archive_sha256": result["archive_sha256"],
                      "passed": result["passed"], "production_promotion": False})


def verify(detector: Path, frozen: Path, archive: Path, output: Path) -> dict:
    inventory = verify_inventory(output, VERSION)
    summary = read_json(output/"summary.json")
    check_seal(summary)
    if inventory["summary_sha256"] != summary["content_sha256"] or summary["source_hashes"] != source_hashes():
        raise ValueError("R038 v2 run binding mismatch")
    compare_numeric(calibration(detector), read_json(frozen))
    result, arrays = compute(detector, frozen, archive)
    if any(summary[key] != result[key] for key in ("archive_sha256", "calibration_sha256", "passed")):
        raise ValueError("R038 v2 summary decision mismatch")
    compare_numeric(result, read_json(output/"results.json"))
    with np.load(output/"trajectories.npz", allow_pickle=False) as saved:
        if set(saved.files) != set(arrays):
            raise ValueError("R038 v2 missing trajectory arrays")
        for key, array in arrays.items():
            np.testing.assert_array_equal(saved[key], array)
    return {"verified": True, "cases": len(result["cases"]), "summary_sha256": summary["content_sha256"],
            "passed": result["passed"], "maximum_replay_difference": 0.0}
