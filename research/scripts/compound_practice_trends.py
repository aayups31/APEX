"""Measure within-stint pre-race practice pace changes on fixed six-lap blocks."""

import argparse
from collections import defaultdict
from datetime import date, datetime, timezone
from itertools import combinations, groupby
from math import isfinite
from pathlib import Path
from statistics import median

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from compound_practice_archive import snapshot
from confirm_compound_crossover import COMPOUNDS, stint_rows
from confirm_compound_traffic import normalize_race_control
from diagnose_compound_line import FOLDER


def measure(tables):
    metadata = {(s["driver_number"], s["stint_number"]): s for s in tables["stints"]}
    if len(metadata) != len(tables["stints"]):
        raise ValueError("Duplicate practice stint")
    laps = {(r["driver_number"], r["lap_number"]): r for r in tables["laps"]}
    if len(laps) != len(tables["laps"]):
        raise ValueError("Duplicate practice lap")
    retained = stint_rows(
        {**tables, "race_control": normalize_race_control(tables["race_control"])}
    )
    blocks = defaultdict(list)
    for driver, stints in retained.items():
        for stint, compound, values in stints:
            meta = metadata[driver, stint]
            for _, run in groupby(
                enumerate(sorted(values)), lambda pair: pair[1] - pair[0]
            ):
                ages = [a for _, a in run]
                for start in range(0, len(ages) - 5, 6):
                    first = (
                        ages[start] - meta["tyre_age_at_start"] + meta["lap_start"] - 1
                    )
                    times = [
                        laps[driver, lap]["lap_duration"]
                        for lap in range(first, first + 6)
                    ]
                    if max(times) > 1.07 * min(times):
                        continue
                    drift = 9 * median(
                        (times[b] - times[a]) / (b - a)
                        for a, b in combinations(range(6), 2)
                    )
                    blocks[compound].append(
                        {
                            "driver": driver,
                            "stint": stint,
                            "first_lap": first,
                            "duration_s": times,
                            "drift_s": drift,
                        }
                    )
    summary = {}
    for compound in COMPOUNDS:
        by_driver = defaultdict(list)
        for block in blocks[compound]:
            by_driver[block["driver"]].append(block["drift_s"])
        summary[compound] = {
            "drivers": len(by_driver),
            "blocks": blocks[compound],
            "drift_s": median(median(v) for v in by_driver.values())
            if by_driver
            else None,
        }
    return summary


def prepare(folder):
    archive = read_json(FOLDER / "compound-v17-practice-sources.json")
    check_seal(archive)
    events = {}
    for event, meta in archive["events"].items():
        tables = {name: [] for name in ("laps", "weather", "race_control", "stints")}
        session = meta["session"]
        if session:
            key = session["session_key"]
            day = date.fromisoformat(meta["race_date"])
            cutoff = datetime(
                day.year, day.month, day.day, tzinfo=timezone.utc
            ).timestamp()
            for name in tables:
                table, binding = snapshot(
                    folder, f"{key}-{name}.json", name, {"session_key": key}, None
                )
                if binding != meta["tables"][name]:
                    raise ValueError("Practice endpoint snapshot mismatch")
                for row in table:
                    stamp = row.get("date_start") if name == "laps" else row.get("date")
                    if stamp:
                        duration = (
                            (row.get("lap_duration") or 0.0) if name == "laps" else 0.0
                        )
                        end = datetime.fromisoformat(stamp).timestamp() + duration
                        if not isfinite(end) or end >= cutoff:
                            raise ValueError(
                                "Practice observation exceeds pre-race cutoff"
                            )
                tables[name] = table
        events[event] = measure(tables)
    return seal(
        {
            "schema": "compound-practice-trends-v17",
            "archive_sha256": archive["content_sha256"],
            "dataset_sha256": archive["dataset_sha256"],
            "events": events,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, prepare(args.snapshots))
