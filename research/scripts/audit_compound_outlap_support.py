"""Audit pre-forecast pit-exit and outlap coverage on recurring R041 failures."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

import pandas as pd
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_same_phase_support import clean_field
from compound_line_proximity import archive_laps, utc
from prepare_compound_pit_exit import BASE, FOLDER, MAPPING, tables_from_archive

EVENTS = ("9850", "9877", "9912", "9928", "9998", "F1_2023_R15", "F1_2024_R16")


def outlaps(root, event, source):
    """Index provider outlap identity without treating a lap start as pit exit."""
    found = defaultdict(list)
    if source["provider"] == "OPENF1":
        session = int(event)
        number, meeting, folder = MAPPING[session]
        tables, digest = tables_from_archive(root / folder, session, (number, meeting))
        if digest != source["archive_sha256"]:
            raise ValueError("OpenF1 outlap source differs from frozen cohort")
        by_driver = defaultdict(list)
        for lap in tables["laps"]:
            if lap["is_pit_out_lap"] is True:
                by_driver[lap["driver_number"]].append(lap)
        for stint in tables["stints"]:
            if not isinstance(stint["lap_start"], int) or not isinstance(
                stint["lap_end"], int
            ):
                continue
            for lap in by_driver[stint["driver_number"]]:
                if (
                    stint["lap_start"]
                    <= lap["lap_number"]
                    <= min(stint["lap_start"] + 1, stint["lap_end"])
                ):
                    found[stint["driver_number"], stint["stint_number"]].append(
                        lap["lap_number"]
                    )
        return found, {}
    _, year, race = event.split("_")
    number = int(race[1:])
    folder = (
        f"fastf1-2024-r{number}-race-20261011"
        if year == "2024"
        else f"r026-fastf1-2023-r{number}-race-20261013"
    )
    columns = [
        "DriverNumber",
        "Stint",
        "LapNumber",
        "PitOutTime",
        "LapStartTime",
        "LapStartDate",
        "Time",
    ]
    frame = pd.read_parquet(root / folder / "tables/laps.parquet", columns=columns)
    exits = {}
    for driver, stint, lap, pit, start, date, end in frame.dropna(
        subset=columns[:4]
    ).itertuples(index=False, name=None):
        key = int(driver), int(stint)
        found[key].append(int(lap))
        if pd.notna(start) and pd.notna(date) and pd.notna(end) and start <= pit <= end:
            exits[key, int(lap)] = utc(date) + (pit - start).total_seconds()
    return found, exits


def observe(row, outlap_ids, exits, clocks, peers):
    key = row["driver"], row["stints"][1]
    laps = outlap_ids.get(key, [])
    if len(laps) != 1:
        return {"reason": "missing_or_ambiguous_outlap"}
    (lap,) = laps
    subject = clocks.get((key[0], lap))
    cutoff = row["forecast_at_s"]
    real_exit = exits.get((key, lap))
    if real_exit is not None and real_exit > cutoff:
        real_exit = None
    if subject is None or not subject[0] <= cutoff:
        return {"reason": "outlap_not_timed_before_cutoff", "exact_exit_s": real_exit}
    end, duration = subject
    if real_exit is not None and not end - duration <= real_exit <= end:
        real_exit = None
    controls = [
        {"driver": driver, "end_s": stamp, "lap_duration_s": seconds}
        for driver, stamp, seconds in peers[lap]
        if driver != key[0] and stamp <= cutoff and abs(stamp - end) <= 120
    ]
    return {
        "outlap_number": lap,
        "outlap_end_s": end,
        "outlap_duration_s": duration,
        "exact_exit_s": real_exit,
        "peers": controls,
        "outlap_relative_s": duration - median(p["lap_duration_s"] for p in controls)
        if len(controls) >= 3
        else None,
    }


def run(root, events=EVENTS):
    cohort = read_json(FOLDER / "compound-v24-cohort.json")
    check_seal(cohort)
    results = {}
    for event in events:
        source = cohort["sources"][event]
        field = clean_field(root, event, source)
        native = archive_laps(root, event, source)
        native_by_end = {(d, t): (n, v) for t, d, n, v in native}
        clocks = {(d, n): (t, v) for t, d, n, v in native}
        if len(clocks) != len(native) or len(native_by_end) != len(native):
            raise ValueError("Ambiguous provider lap clock")
        peers = defaultdict(list)
        for stint in field:
            d = stint["driver"]
            for end in stint["ends"].values():
                n, v = native_by_end[d, end]
                peers[n].append((d, end, v))
        ids, exits = outlaps(root, event, source)
        records = [
            {"index": i, **observe(row, ids, exits, clocks, peers)}
            for i, row in enumerate(cohort["cases"])
            if str(row["session"]) == event
        ]
        results[event] = {
            "provider": source["provider"],
            "cases": len(records),
            "timed_outlaps": sum("outlap_number" in r for r in records),
            "exact_exit": sum(r.get("exact_exit_s") is not None for r in records),
            "outlap_proxy": sum(
                r.get("outlap_relative_s") is not None for r in records
            ),
            "both": sum(
                r.get("exact_exit_s") is not None
                and r.get("outlap_relative_s") is not None
                for r in records
            ),
            "exclusions": dict(Counter(r["reason"] for r in records if "reason" in r)),
            "records": records,
        }
    return seal(
        {
            "scope": "FORECAST_INPUT_COVERAGE_ONLY",
            "cohort_sha256": cohort["content_sha256"],
            "races": results,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
