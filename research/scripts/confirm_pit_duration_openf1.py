"""Acquire and reconcile the registered R047 confirmation through OpenF1."""

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from math import isfinite
from pathlib import Path

import requests
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from confirm_compound_crossover import timestamp
from confirm_pit_duration_r047 import FOLDER, RACES
from fit_pit_duration_race_shift import SCALES, evaluate

SESSIONS = {
    1: (9693, 1254),
    4: (10014, 1257),
    6: (10033, 1259),
    16: (9912, 1268),
    18: (9896, 1270),
}
ENDPOINTS = ("sessions", "pit", "laps", "race_control")


def acquire(root):
    root.mkdir(parents=True, exist_ok=False)
    files = {}
    with requests.Session() as client:
        for number, (session, _) in SESSIONS.items():
            assert_development_event(2025, number)
            for endpoint in ENDPOINTS:
                response = client.get(
                    f"https://api.openf1.org/v1/{endpoint}",
                    params={"session_key": session},
                    timeout=30,
                )
                response.raise_for_status()
                path = root / f"{session}-{endpoint}.json"
                with path.open("xb") as handle:
                    handle.write(response.content)
                files[path.name] = file_sha256(path)
    write_manifest(root / "manifest.json", seal({"files": files, "provider": "OPENF1"}))


def status_events(rows):
    """Keep global state changes. Pit exit lights do not clear a safety car."""
    states = []
    for r in rows:
        flag, message = r.get("flag"), (r.get("message") or "").upper()
        if r.get("category") == "SafetyCar" and "DEPLOYED" in message:
            states.append((timestamp(r["date"]), False))
        if r.get("scope") == "Track" and "PIT EXIT" not in message:
            if flag in ("RED", "YELLOW", "DOUBLE YELLOW", "CHEQUERED"):
                states.append((timestamp(r["date"]), False))
            if flag in ("GREEN", "CLEAR"):
                states.append((timestamp(r["date"]), True))
    return sorted(states)


def extract(tables):
    transitions = status_events(tables["race_control"])
    clocks = [t for t, _ in transitions]

    def green(start, end):
        i = bisect_right(clocks, start)
        return (i == 0 or transitions[i - 1][1]) and all(
            state for _, state in transitions[i : bisect_right(clocks, end)]
        )

    drivers = defaultdict(dict)
    pit_laps = defaultdict(set)
    for row in tables["pit"]:
        pit_laps[row["driver_number"]].add(row["lap_number"])
    for row in tables["laps"]:
        driver, lap = row["driver_number"], row["lap_number"]
        if lap in drivers[driver]:
            raise ValueError("Duplicate OpenF1 driver lap")
        duration = row["lap_duration"]
        if (
            not row["date_start"]
            or not isinstance(duration, (int, float))
            or not isfinite(duration)
            or duration <= 0
        ):
            continue
        start = timestamp(row["date_start"])
        end = start + duration
        splits = [row.get(f"duration_sector_{i}") for i in (1, 2, 3)]
        clean = (
            all(isinstance(t, (int, float)) and isfinite(t) and t > 0 for t in splits)
            and abs(sum(splits) - duration) <= 0.1
        )
        drivers[driver][lap] = (
            start,
            end,
            row["is_pit_out_lap"],
            clean
            and green(start, end)
            and row["is_pit_out_lap"] is False
            and lap not in pit_laps[driver],
        )
    stops, excluded = [], Counter()
    for row in tables["pit"]:
        driver, reported = row["driver_number"], row["lap_number"]
        path = drivers[driver]
        outlaps = [
            n
            for n in (reported, reported + 1)
            if n in path and path[n][2] is True and n - 1 in path
        ]
        if len(outlaps) != 1:
            excluded["no_unique_adjacent_timed_outlap"] += 1
            continue
        (out,) = outlaps
        inlap = out - 1
        entry, exit_lap = path[inlap], path[out]
        stamp = timestamp(row["date"])
        duration = row.get("lane_duration", row.get("pit_duration"))
        if not (
            entry[0] <= stamp <= exit_lap[1]
            and green(entry[0], exit_lap[1])
            and isinstance(duration, (int, float))
            and isfinite(duration)
            and duration > 0
        ):
            excluded["clock_green_or_duration"] += 1
            continue
        prefix = range(inlap - 3, inlap)
        if not all(n in path and path[n][3] for n in prefix):
            excluded["missing_clean_subject_prefix"] += 1
            continue
        neighbors = [
            peer
            for peer, peer_path in drivers.items()
            if peer != driver
            and all(
                n in peer_path and peer_path[n][3] for n in range(inlap - 3, out + 1)
            )
            and abs(peer_path[inlap - 1][1] - path[inlap - 1][1]) <= 120
        ]
        if len(neighbors) < 3:
            excluded["insufficient_clean_peers"] += 1
            continue
        stops.append(
            {
                "driver": driver,
                "inlap": inlap,
                "lane_s": duration,
                "peer_count": len(neighbors),
            }
        )
    if len({(s["driver"], s["inlap"]) for s in stops}) != len(stops):
        raise ValueError("Duplicate qualified OpenF1 pit stop")
    return stops, dict(excluded)


def run(root):
    manifest = read_json(root / "manifest.json")
    fitted = read_json(FOLDER / "pit-duration-r047-v1.json")
    decision = read_json(FOLDER / "pit-duration-r047-v2.json")
    for doc in (manifest, fitted, decision):
        check_seal(doc)
    if (
        decision["parent_sha256"] != fitted["content_sha256"]
        or decision["scale_multipliers"] != list(SCALES)
        or not decision["passed"]
    ):
        raise ValueError("Unexpected frozen R047 model")
    events = {}
    for number, (session, meeting) in SESSIONS.items():
        assert_development_event(2025, number)
        tables = {}
        for endpoint in ENDPOINTS:
            name = f"{session}-{endpoint}.json"
            path = root / name
            if file_sha256(path) != manifest["files"][name]:
                raise ValueError("OpenF1 archive integrity check failed")
            rows = read_json(path)
            if not rows or any(
                r["session_key"] != session or r["meeting_key"] != meeting for r in rows
            ):
                raise ValueError("Incorrect OpenF1 confirmation identity")
            tables[endpoint] = rows
        (identity,) = tables["sessions"]
        if identity["year"] != 2025 or identity["session_name"] != "Race":
            raise ValueError("Unexpected OpenF1 confirmation session")
        stops, exclusions = extract(tables)
        events[f"F1_2025_R{number:02}"] = {
            "circuit": RACES[number][0],
            "stops": stops,
            "exclusions": exclusions,
        }
    support = all(len(event["stops"]) >= 5 for event in events.values())
    result = (
        evaluate(fitted["calibration"], events)
        if all(e["stops"] for e in events.values())
        else None
    )
    return seal(
        {
            "schema": "apex-r047-openf1-confirmation",
            "archive_sha256": manifest["content_sha256"],
            "frozen_sha256": decision["content_sha256"],
            "events": events,
            "minimum_support_passed": support,
            "result": result,
            "passed": support and bool(result and result["passed"]),
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--acquire", action="store_true")
    args = parser.parse_args()
    if args.acquire:
        acquire(args.archive)
    write_manifest(args.output, run(args.archive))
