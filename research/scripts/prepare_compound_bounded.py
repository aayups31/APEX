"""Rebuild R041 opened development data with source-bound causal context."""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.data.jolpica import verify_jolpica_archive
from apexsim.data.tyre_dataset import FuelPrior, segment_native_laps
from apexsim.provenance import write_manifest
from apexsim.research.compound_bounded import bounded_features, causal_weather
from apexsim.research.evidence import check_seal, read_json, seal
from compound_bounded_common import environment, source_hashes
from compound_multiseason import ARCHIVES, fastf1_cases
from confirm_compound_crossover import timestamp
from confirm_compound_multiseason import BASE, canonical_file_sha
from confirm_compound_reference import build_cases, tables_from_archive
from diagnose_compound_adaptation import context, field_stints
from extend_compound_development import combine

OPENED = {
    9912: (16, 1268, "r041-openf1-confirmation"), 9839: (24, 1276, "r041-openf1-confirmation"),
    10014: (4, 1257, "r041-traffic-holdout"), 9971: (9, 1262, "r041-traffic-holdout"),
    9963: (10, 1263, "r041-reference-holdout"), 9955: (11, 1264, "r041-reference-holdout"),
    9998: (2, 1255, "r041-conditioned-holdout"), 9928: (14, 1266, "r041-conditioned-holdout"),
    9920: (15, 1267, "r041-event-holdout"), 9896: (18, 1270, "r041-event-holdout"),
    9888: (19, 1271, "r041-multiseason-holdout-final"), 9877: (20, 1272, "r041-multiseason-holdout-final"),
    10033: (6, 1259, "r041-v8-confirmation-panel"), 9987: (7, 1260, "r041-v8-confirmation-panel"),
    9850: (23, 1275, "r041-v8-confirmation-panel"),
}


def field_context(row: dict, field: list[dict]) -> list[dict]:
    """Retain contributing timestamps for completed, same-compound age windows."""
    return [{"driver": w["driver"], "stint": w["stint"], "available_at_s": w["available_at_s"],
             "change_s": w["target_s"]-w["prefix_s"]} for w in context(row, field)]


def fastf1_context(root: Path, rows: list[dict]) -> list[dict]:
    """Use the existing dry/green mask and explicitly map session weather to UTC."""
    metadata = read_json(root/"manifest.json")
    query = metadata["query"]
    year, round_number = query["year"], query["round_number"]
    assert_development_event(year, round_number)
    verified = verify_fastf1_archive(root)
    frame = pd.read_parquet(root/"tables/laps.parquet")
    weather = pd.read_parquet(root/"tables/weather_data.parquet")
    calendar = BASE/f".cache/jolpica-{year}-20260916"
    verify_jolpica_archive(calendar)
    event, = [e for e in read_json(calendar/"events.json")["events"]
              if (e["season"], e["round_number"]) == (year, round_number)]
    event = {**event, "track_id": event["circuit_id"]}
    segments, _ = segment_native_laps(frame, event, FuelPrior())
    samples = sorted((r["Time"].total_seconds(), r["Rainfall"]) for r in weather.to_dict("records")
                     if pd.notna(r["Time"]))
    field, native_lookup = defaultdict(dict), {}
    compounds = {}
    for segment in segments:
        driver, stint = int(segment["driver"]), segment["stint"]
        key = (driver, stint)
        compounds[key] = segment["compound"]
        for row in segment["rows"]:
            native = frame.iloc[row["native_row"]]
            if pd.isna(native["LapStartDate"]) or pd.isna(native["LapStartTime"]):
                continue
            start = native["LapStartTime"].total_seconds()
            end = start+row["observed_s"]
            previous = [wet for time, wet in samples if time <= start]
            if (not previous or previous[-1] not in (False, np.False_)
                    or any(wet not in (False, np.False_) for time, wet in samples if start < time < end)):
                continue
            date = pd.Timestamp(native["LapStartDate"])
            date = date.tz_localize("UTC") if date.tzinfo is None else date.tz_convert("UTC")
            end_utc = date.timestamp()+row["observed_s"]
            field[key][row["tyre_age"]] = {"pace_s": row["corrected_s"], "end_s": end_utc}
            native_lookup[(driver, stint, row["tyre_age"])] = (end_utc, end)
    field_rows = [{"driver": d, "stint": s, "compound": compounds[(d, s)],
                   "values": {a: v["pace_s"] for a, v in values.items()},
                   "ends": {a: v["end_s"] for a, v in values.items()}} for (d, s), values in field.items()]
    result = []
    for row in rows:
        end_utc, end_relative = native_lookup[(row["driver"], row["stints"][1], row["ages"][2])]
        if abs(end_utc-row["forecast_at_s"]) > 1e-6:
            raise ValueError("FastF1 context clock differs from frozen forecast clock")
        weather_samples = [{"at_s": end_utc+r["Time"].total_seconds()-end_relative,
                            "track_temperature_c": float(r["TrackTemp"]) if pd.notna(r["TrackTemp"]) else None}
                           for r in weather.to_dict("records") if pd.notna(r["Time"])]
        enriched = {**row, "context": {**causal_weather(weather_samples, row["forecast_at_s"]),
                                      "field_windows": field_context(row, field_rows)}}
        bounded_features(enriched, "context")
        result.append(enriched)
    if verify_fastf1_archive(root)["content_sha256"] != verified["content_sha256"]:
        raise ValueError("FastF1 context source changed during read")
    return result


def prepare() -> dict:
    """Append the opened v8 panel, requiring exact reconstruction of every case."""
    base = combine(read_json(BASE/"docs/verification/compound-v8-training-additions.json"))
    panel = read_json(BASE/"docs/verification/compound-v8-coverage-results.json")
    check_seal(panel)
    expected = base["cases"]+panel["cases"]
    fields = tuple(base["cases"][0])
    def key(r: dict) -> tuple:
        return str(r["session"]), r["driver"], tuple(r["stints"]), tuple(r["ages"])
    expected_by_key = {key(r): {f: r[f] for f in fields} for r in expected}
    if len(expected_by_key) != len(expected):
        raise ValueError("Opened source corpus contains duplicate comparison cases")
    cases, sources = [], {}
    for session, (round_number, meeting, folder) in OPENED.items():
        tables, digest = tables_from_archive(BASE/".cache"/folder, session, (round_number, meeting))
        rows, support = build_cases(tables, session)
        field = field_stints(tables)
        weather = [{"at_s": timestamp(w["date"]), "track_temperature_c": w.get("track_temperature")}
                   for w in tables["weather"]]
        for row in rows:
            row["context"] = {**causal_weather(weather, row["forecast_at_s"]), "field_windows": field_context(row, field)}
        cases.extend(rows)
        sources[str(session)] = {"provider": "OPENF1", "archive_sha256": digest, "blocks": len(rows), **support}
    for root in ARCHIVES:
        rows, metadata = fastf1_cases(root)
        cases.extend(fastf1_context(root, rows))
        sources[metadata["event_id"]] = {"provider": "FASTF1", **metadata}
    for row in cases:
        if {f: row[f] for f in fields} != expected_by_key.get(key(row)):
            raise ValueError("Native context reconstruction changed an opened case or label")
        bounded_features(row, "context")
    if {key(r) for r in cases} != set(expected_by_key):
        raise ValueError("Native context reconstruction dropped opened cases")
    return seal({"schema_version": "apex-compound-bounded-development-data-v9", "sources": sources,
                 "parents": {"v8_training_sha256": base["content_sha256"], "v8_panel_sha256": panel["content_sha256"]},
                 "source_sha256_lf": canonical_file_sha(Path(__file__)),
                 "implementation_sha256_lf": source_hashes(), "environment": environment(),
                 "scope": "PREVIOUSLY_OPENED_DEVELOPMENT_ONLY_NOT_CONFIRMATION", "cases": cases,
                 "truth": {"pace": "FUEL_PRIOR_CORRECTED_PROXY", "weather": "PROVIDER_PARSED_OBSERVATION",
                           "field_drift": "COMPLETED_OBSERVED_PACE_PROXY", "physical_wear": "UNKNOWN"},
                 "context_coverage": {"weather": sum(r["context"]["track_temperature_c"] is not None for r in cases),
                                      "field": sum(bool(r["context"]["field_windows"]) for r in cases)}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, prepare())
