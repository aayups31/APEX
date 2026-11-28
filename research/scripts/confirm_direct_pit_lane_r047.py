"""Verify measured pit-lane durations conditional on green status."""

import argparse
from bisect import bisect_right
from collections import Counter
from math import isfinite
from pathlib import Path

from apexsim.provenance import write_manifest
from apexsim.research.evidence import seal
from confirm_compound_crossover import timestamp
from confirm_pit_duration_openf1 import run as confirm
from confirm_pit_duration_openf1 import status_events


def extract(tables):
    identities = Counter((r["driver_number"], r["lap_number"]) for r in tables["pit"])
    laps = {(r["driver_number"], r["lap_number"]): r for r in tables["laps"]}
    (session,) = tables["sessions"]
    start, finish = (timestamp(session[k]) for k in ("date_start", "date_end"))
    states = status_events(tables["race_control"])
    clocks = [t for t, _ in states]
    kept, excluded = [], Counter()
    for row in tables["pit"]:
        driver, lap = row["driver_number"], row["lap_number"]
        duration = row.get("lane_duration", row.get("pit_duration"))
        if (
            not isinstance(duration, (float, int))
            or not isfinite(duration)
            or duration <= 0
        ):
            excluded["invalid_duration"] += 1
            continue
        if lap < 3:
            excluded["session_opening"] += 1
            continue
        if identities[driver, lap] != 1 or not (
            (driver, lap) in laps
            or laps.get((driver, lap + 1), {}).get("is_pit_out_lap") is True
        ):
            excluded["ambiguous_or_unlinked_stop"] += 1
            continue
        stamp = timestamp(row["date"])
        lo, hi = stamp - duration, stamp + duration
        a, b = bisect_right(clocks, lo), bisect_right(clocks, hi)
        if not (
            start <= lo < hi <= finish
            and (a == 0 or states[a - 1][1])
            and all(state for _, state in states[a:b])
        ):
            excluded["outside_green_window"] += 1
            continue
        kept.append(
            {
                "driver": driver,
                "reported_lap": lap,
                "pit_timestamp_s": stamp,
                "lane_s": duration,
            }
        )
    return kept, dict(excluded)


def run(root):
    evidence = confirm(root, extractor=extract)
    body = {k: v for k, v in evidence.items() if k != "content_sha256"}
    return seal({**body, "schema": "apex-r047-direct-green-lane-confirmation"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.archive))
