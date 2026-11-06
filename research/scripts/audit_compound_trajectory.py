"""Independent scalar trajectory/checkpoint and native-association audit."""
from __future__ import annotations

import argparse
import gzip
import json
from math import isfinite
from pathlib import Path
from statistics import median
from struct import pack, unpack

import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_bounded_confirmation import EVENTS as V9
from audit_compound_context import OPENED, utc
from audit_compound_repair import compare, crossing, panel
from confirm_compound_multiseason import BASE, canonical_file_sha


def features(row: dict, group: str) -> list[float]:
    """Independent scalar equations, without candidate feature/model helpers."""
    current, reference = row["current_history"], row["reference_history"]
    for history in (current, reference):
        if any(p["end_s"] > row["forecast_at_s"] for p in history):
            raise ValueError("Independent trajectory future input")
    if [p["age"] for p in current[-3:]] != row["ages"][:3]:
        raise ValueError("Independent trajectory moved forecast age")
    def line(samples: list[dict]) -> tuple:
        pairs = [(q["pace_s"]-p["pace_s"])/(q["age"]-p["age"])
                 for i, p in enumerate(samples) for q in samples[i+1:]]
        slope = median(pairs)
        offset = median(p["pace_s"]-slope*p["age"] for p in samples)
        return slope, median(abs(p["pace_s"]-offset-slope*p["age"]) for p in samples)
    prefix = row["current_prefix_s"]
    result = [float(row["compounds"][1] == c) for c in ("SOFT", "MEDIUM", "HARD")]
    result += [median(row["reference_target_s"])-median(prefix)-row["prefix_s"],
               4.5*(prefix[2]-prefix[0]), row["prefix_s"]]
    if group != "pace":
        result += [row["ages"][0], len(current), *[9*line(current[-n:])[0] for n in (3, 6, 12)],
                   line(current)[1], median(prefix)-median(p["pace_s"] for p in current)]
    if group == "full":
        slope, spread = line(reference)
        result += [9*slope, spread,
                   median(p["pace_s"] for p in reference[-3:])-median(p["pace_s"] for p in reference[:3])]
    return result


def forecast(row: dict, model: dict) -> dict:
    x = features(row, model["group"])
    z = [(v-m)/s for v, m, s in zip(x, model["mean"], model["scale"], strict=True)]
    if model["family"] == "ridge":
        drift = model["intercept"]+sum(v*c for v, c in zip(z, model["coefficients"], strict=True))
    else:
        # sklearn's tree traversal converts the scaled matrix to float32.
        z = [unpack("f", pack("f", v))[0] for v in z]
        drift = model["initial"]
        for tree in model["trees"]:
            node = 0
            while tree["left"][node] != -1:
                node = tree["left"][node] if z[tree["feature"][node]] <= tree["threshold"][node] else tree["right"][node]
            drift += model["learning_rate"]*tree["value"][node]
    raw = -drift
    fallback = model["support"][row["compounds"][1]] < 3
    correction = 0. if fallback else max(-model["bound_s"], min(model["bound_s"], raw))
    reference = median(row["reference_target_s"])-median(row["current_prefix_s"])
    prediction = reference+correction
    return {"predicted_s": prediction, "reference_persistence_s": reference, "raw_correction_s": raw,
            "applied_correction_s": correction, "correction_bounded": not fallback and abs(raw) > model["bound_s"],
            "fallback": fallback, "fallback_reasons": ["FEWER_THAN_THREE_COMPOUND_EVENTS"] if fallback else [],
            "predicted_crossover": crossing(row["prefix_s"], prediction) and crossing(row["pairwise_prefix_s"], prediction),
            "history_laps": len(row["current_history"]), "truth": "FUEL_CORRECTED_PACE_PROXY_NOT_PHYSICAL_WEAR"}


def audit(data: dict, results: dict) -> dict:
    for item in (data, results):
        check_seal(item)
    if results["dataset_sha256"] != data["content_sha256"]:
        raise ValueError("Independent trajectory dataset binding mismatch")
    for name, digest in results["hashes"].items():
        if canonical_file_sha(BASE/name) != digest:
            raise ValueError("Independent trajectory source mismatch: "+name)
    rows, count = data["cases"], 0
    events = sorted({str(r["session"]) for r in rows})
    for name, result in results["recipes"].items():
        models = {m["outer_event"]: m["model"] for m in result["models"]}
        if sorted(models) != events or len(models) != len(result["models"]):
            raise ValueError("Independent trajectory fold denominator mismatch")
        if [p["case_index"] for p in result["predictions"]] != list(range(len(rows))):
            raise ValueError("Independent trajectory forecast denominator mismatch")
        replay = []
        for index, row in enumerate(rows):
            event = str(row["session"])
            model = models[event]
            if model["training_events"] != [e for e in events if e != event]:
                raise ValueError("Independent trajectory training event leakage")
            support = {c: len({str(r["session"]) for r in rows if str(r["session"]) != event and r["compounds"][1] == c})
                       for c in ("SOFT", "MEDIUM", "HARD")}
            compare(model["support"], support, name+"/support")
            prediction = forecast(row, model)
            compare(result["predictions"][index], {"case_index": index, **prediction}, name+f"/prediction/{index}")
            replay.append({**row, **prediction})
            count += 1
        compare(result["readiness"], panel(replay, sorted(data["sources"])), name+"/readiness")
    primary = results["recipes"].get("full_boost")
    qualified = primary is not None and primary["readiness"]["development_qualified"]
    compare(results["development_qualified"], qualified, "development_qualified")
    return seal({"schema_version": "apex-compound-trajectory-scalar-audit-v11", "dataset_sha256": data["content_sha256"],
                 "result_sha256": results["content_sha256"], "forecasts_audited": count, "audit_passed": True,
                 "audit_source_sha256_lf": canonical_file_sha(Path(__file__)),
                 "development_qualified": qualified, "scope": "INDEPENDENT_FEATURES_CHECKPOINT_INFERENCE_AND_EVENT_GATES_NOT_FIT"})


def audit_native(data: dict, native_root: Path) -> dict:
    """Check every appended observation against the sealed provider payload."""
    check_seal(data)
    base = read_json(BASE/"docs/verification/compound-v10-development-data.json")
    check_seal(base)
    if data["parent_sha256"] != base["content_sha256"] or data["sources"] != base["sources"]:
        raise ValueError("Trajectory parent/source mismatch")
    if len(data["cases"]) != len(base["cases"]):
        raise ValueError("Trajectory changed the cohort")
    for original, row in zip(base["cases"], data["cases"], strict=True):
        if {k: v for k, v in row.items() if k not in ("current_history", "reference_history")} != original:
            raise ValueError("Trajectory changed an original case")
    mapping = {**OPENED, **{e: (*identity, "r041-v9-confirmation-20261104") for e, identity in V9.items()}}
    contributions = 0
    for event, source in data["sources"].items():
        if source["provider"] == "OPENF1":
            round_number, _, folder = mapping[int(event)]
            assert_development_event(2025, round_number)
            root = native_root/folder
            manifest = read_json(root/"manifest.json")
            check_seal(manifest)
            if manifest["content_sha256"] != source["archive_sha256"]:
                raise ValueError("Trajectory native archive mismatch")
            tables = {}
            for endpoint in ("laps", "stints"):
                name = f"{event}-{endpoint}.json"
                if file_sha256(root/name) != manifest["files"][name]:
                    raise ValueError("Trajectory native file mismatch")
                tables[endpoint] = read_json(root/name)
            laps = {(r["driver_number"], r["lap_number"]): r for r in tables["laps"]}
            stints = {(r["driver_number"], r["stint_number"]): r for r in tables["stints"]}
            def native(driver: int, stint: int, age: float, stints=stints, laps=laps) -> tuple:
                meta = stints[driver, stint]
                lap = age-meta["tyre_age_at_start"]+meta["lap_start"]-1
                raw = laps[driver, lap]
                duration = raw["lap_duration"]
                return duration-max(0., 105.-1.4*(lap-1))*.03, utc(raw["date_start"])+duration, meta["compound"]
        else:
            _, year, round_text = event.split("_")
            year, round_number = int(year), int(round_text[1:])
            assert_development_event(year, round_number, event_id=event)
            name = (f"fastf1-2024-r{round_number}-race-20261011" if year == 2024 else
                    f"r026-fastf1-2023-r{round_number}-race-20261013")
            root = native_root/name
            manifest = verify_fastf1_archive(root)
            if manifest["content_sha256"] != source["archive_sha256"]:
                raise ValueError("Trajectory native archive mismatch")
            lookup = {}
            for raw in pd.read_parquet(root/"tables/laps.parquet").to_dict("records"):
                if any(pd.isna(raw[k]) for k in ("DriverNumber", "Stint", "TyreLife")):
                    continue
                key = int(raw["DriverNumber"]), int(raw["Stint"]), raw["TyreLife"]
                if key in lookup:
                    raise ValueError("Trajectory duplicate native age")
                lookup[key] = raw
            def native(driver: int, stint: int, age: float, lookup=lookup) -> tuple:
                raw = lookup[driver, stint, age]
                duration = raw["LapTime"].total_seconds()
                return duration-(105.-1.4*(raw["LapNumber"]-1))*.03, utc(raw["LapStartDate"])+duration, raw["Compound"]
        for row in (r for r in data["cases"] if str(r["session"]) == event):
            for key, pos in (("reference_history", 0), ("current_history", 1)):
                samples = row[key]
                for i, sample in enumerate(samples):
                    pace, end, compound = native(row["driver"], row["stints"][pos], sample["age"])
                    if compound != row["compounds"][pos] or end > row["forecast_at_s"] or not isfinite(pace):
                        raise ValueError("Trajectory invalid native association")
                    compare(sample["pace_s"], pace, "native pace")
                    # Exact UTC seconds: relative tolerances would permit minutes.
                    if abs(sample["end_s"]-end) > 1e-6:
                        raise ValueError("Trajectory native timestamp mismatch")
                    if i and sample["age"] != samples[i-1]["age"]+1:
                        raise ValueError("Trajectory gap in native history")
                    contributions += 1
    return seal({"schema_version": "apex-compound-trajectory-native-audit-v11", "dataset_sha256": data["content_sha256"],
                 "cases_audited": len(data["cases"]), "sources_audited": len(data["sources"]),
                 "audit_source_sha256_lf": canonical_file_sha(Path(__file__)),
                 "native_lap_associations": contributions, "audit_passed": True,
                 "scope": "ALL_APPENDED_AGE_PACE_COMPOUND_AND_UTC_ASSOCIATIONS; NOT_INDEPENDENT_HISTORY_ELIGIBILITY_DENOMINATOR"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--native-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (args.results is None) == (args.native_root is None):
        parser.error("Choose either --results or --native-root")
    data = read_json(args.dataset)
    if args.results:
        results = (json.loads(gzip.decompress(args.results.read_bytes())) if args.results.suffix == ".gz"
                   else read_json(args.results))
        report = audit(data, results)
    else:
        report = audit_native(data, args.native_root)
    write_manifest(args.output, report)
