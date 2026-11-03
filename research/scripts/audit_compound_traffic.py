"""Describe recorded traffic exposure in existing R041 crossover blocks."""
import argparse
from bisect import bisect_left
from collections import defaultdict
from pathlib import Path

from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from confirm_compound_crossover import timestamp


def audit(results, archive, intervals):
    evidence = read_json(results)
    manifest = read_json(archive/"manifest.json")
    check_seal(evidence)
    check_seal(manifest)
    if evidence["archive_sha256"] != manifest["content_sha256"]:
        raise ValueError("Results and archive do not match")
    rows, sources = [], {}
    for session in dict.fromkeys(case["session"] for case in evidence["cases"]):
        tables = {}
        for endpoint in ("laps", "stints"):
            name = f"{session}-{endpoint}.json"
            if file_sha256(archive/name) != manifest["files"][name]:
                raise ValueError("Source table hash mismatch")
            tables[endpoint] = read_json(archive/name)
        path = intervals/f"{session}.json"
        sources[str(session)] = file_sha256(path)
        gaps = defaultdict(list)
        for item in read_json(path):
            if item["session_key"] != session:
                raise ValueError("Interval session mismatch")
            gap = item.get("interval")
            if isinstance(gap, (int, float)) and 0 <= gap <= 120:
                gaps[item["driver_number"]].append((timestamp(item["date"]), gap))
        laps = {(r["driver_number"], r["lap_number"]): r for r in tables["laps"]}
        stints = {(r["driver_number"], r["stint_number"]): r for r in tables["stints"]}
        for case in evidence["cases"]:
            if case["session"] != session:
                continue
            driver = case["driver"]
            samples = sorted(gaps[driver])
            times = [time for time, _ in samples]
            exposure = []
            for number in case["stints"]:
                stint = stints[driver, number]
                windows = []
                for ages in (case["ages"][:3], case["ages"][-3:]):
                    counts = []
                    for age in ages:
                        lap_number = stint["lap_start"] + age - stint["tyre_age_at_start"] - 1
                        lap = laps[driver, lap_number]
                        start = timestamp(lap["date_start"])
                        stop = start + lap["lap_duration"]
                        relevant = samples[bisect_left(times, start):bisect_left(times, stop)]
                        counts.append({"lap": lap_number, "samples": len(relevant),
                                       "close_samples": sum(gap < 1.5 for _, gap in relevant)})
                    windows.append(counts)
                exposure.append(windows)
            rows.append({"session": session, "driver": driver, "stints": case["stints"], "ages": case["ages"],
                         "observed_crossover": case["observed_crossover"], "traffic_samples": exposure})
    return seal({"scope": "POSTHOC_DIAGNOSTIC_ONLY", "gap_threshold_s": 1.5, "interval_sha256": sources,
                 "results_sha256": evidence["content_sha256"], "cases": rows})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("results", "archive", "intervals", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, audit(args.results, args.archive, args.intervals))
