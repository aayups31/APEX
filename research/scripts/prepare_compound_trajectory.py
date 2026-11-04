"""Append causal native stint trajectories to the unchanged opened v10 cohort."""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.data.jolpica import verify_jolpica_archive
from apexsim.data.tyre_dataset import FuelPrior, segment_native_laps
from apexsim.provenance import write_manifest
from apexsim.research.compound_trajectory import validate_history
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_bounded_confirmation import EVENTS as V9
from audit_compound_context import utc
from compound_bounded_common import environment
from confirm_compound_multiseason import BASE, canonical_file_sha
from confirm_compound_reference import tables_from_archive
from diagnose_compound_adaptation import field_stints
from prepare_compound_bounded import OPENED


def fastf1_field(root: Path) -> tuple[list[dict], str]:
    """Preserve existing quality segments and dry-lap masks, including gaps."""
    query = read_json(root/"manifest.json")["query"]
    year, round_number = query["year"], query["round_number"]
    assert_development_event(year, round_number)
    if query["session"] != "R":
        raise ValueError("Trajectory inputs require a race archive")
    manifest = verify_fastf1_archive(root)
    calendar = BASE/f".cache/jolpica-{year}-20260916"
    verify_jolpica_archive(calendar)
    event, = [e for e in read_json(calendar/"events.json")["events"]
              if (e["season"], e["round_number"]) == (year, round_number)]
    frame = pd.read_parquet(root/"tables/laps.parquet")
    weather = pd.read_parquet(root/"tables/weather_data.parquet")
    segments, _ = segment_native_laps(frame, {**event, "track_id": event["circuit_id"]}, FuelPrior())
    samples = sorted((r["Time"].total_seconds(), r["Rainfall"]) for r in weather.to_dict("records")
                     if pd.notna(r["Time"]))
    values, ends, compounds = defaultdict(dict), defaultdict(dict), {}
    for segment in segments:
        key = int(segment["driver"]), segment["stint"]
        if key in compounds and compounds[key] != segment["compound"]:
            raise ValueError("Conflicting trajectory native compound")
        compounds[key] = segment["compound"]
        for row in segment["rows"]:
            native = frame.iloc[row["native_row"]]
            if pd.isna(native["LapStartDate"]) or pd.isna(native["LapStartTime"]):
                continue
            start, duration = native["LapStartTime"].total_seconds(), row["observed_s"]
            past = [wet for time, wet in samples if time <= start]
            if not past or past[-1] is not False or any(wet is not False for time, wet in samples if start < time < start+duration):
                continue
            age, pace, end = row["tyre_age"], row["corrected_s"], utc(native["LapStartDate"])+duration
            if age in values[key]:
                raise ValueError("Duplicate trajectory native age")
            values[key][age], ends[key][age] = pace, end
    if verify_fastf1_archive(root)["content_sha256"] != manifest["content_sha256"]:
        raise ValueError("Trajectory native archive changed during read")
    return [{"driver": d, "stint": s, "compound": compounds[d, s], "values": v, "ends": ends[d, s]}
            for (d, s), v in values.items()], manifest["content_sha256"]


def attach(row: dict, field: list[dict]) -> dict:
    """Select backward from the fixed cutoff; never bridge an excluded lap."""
    lookup = {(r["driver"], r["stint"]): r for r in field}
    if len(lookup) != len(field):
        raise ValueError("Duplicate trajectory native stint")
    reference, current = (lookup[row["driver"], stint] for stint in row["stints"])
    if [reference["compound"], current["compound"]] != row["compounds"]:
        raise ValueError("Trajectory native compound mismatch")
    history_ages, age = [], row["ages"][2]
    while len(history_ages) < 12 and age in current["values"]:
        if current["ends"][age] > row["forecast_at_s"]:
            raise ValueError("Future lap in backward trajectory")
        history_ages.append(age)
        age -= 1
    def observations(source: dict, ages: list) -> list[dict]:
        return [{"age": a, "pace_s": source["values"][a], "end_s": source["ends"][a]} for a in ages]
    result = {**row, "current_history": observations(current, history_ages[::-1]),
              "reference_history": observations(reference, row["ages"])}
    validate_history(result)
    return result


def prepare(native_root: Path) -> dict:
    """Require original source identities/seals before adding any observations."""
    base = read_json(BASE/"docs/verification/compound-v10-development-data.json")
    check_seal(base)
    mapping = {**OPENED, **{e: (*identity, "r041-v9-confirmation-20261104") for e, identity in V9.items()}}
    fields = {}
    for event, source in base["sources"].items():
        if source["provider"] == "OPENF1":
            round_number, meeting, folder = mapping[int(event)]
            assert_development_event(2025, round_number)
            tables, digest = tables_from_archive(native_root/folder, int(event), (round_number, meeting))
            field = field_stints(tables)
        elif source["provider"] == "FASTF1":
            _, year, round_text = event.split("_")
            year, round_number = int(year), int(round_text[1:])
            assert_development_event(year, round_number, event_id=event)
            folder = (f"fastf1-2024-r{round_number}-race-20261011" if year == 2024 else
                      f"r026-fastf1-2023-r{round_number}-race-20261013")
            field, digest = fastf1_field(native_root/folder)
        else:
            raise ValueError("Unknown trajectory native provider")
        if digest != source["archive_sha256"]:
            raise ValueError("Trajectory archive differs from frozen cohort")
        fields[event] = field
    cases = [attach(r, fields[str(r["session"])]) for r in base["cases"]]
    return seal({"schema_version": "apex-compound-trajectory-data-v11", "parent_sha256": base["content_sha256"],
                 "sources": base["sources"], "cases": cases, "environment": environment(),
                 "source_sha256_lf": canonical_file_sha(Path(__file__)),
                 "scope": "OPENED_DEVELOPMENT_UNCHANGED_FORECAST_CLOCK_AND_LABELS",
                 "history_coverage": {str(n): sum(len(r["current_history"]) == n for r in cases) for n in range(3, 13)}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE/".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, prepare(args.native_root))
