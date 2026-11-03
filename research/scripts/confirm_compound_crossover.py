"""Frozen R041 stint-prefix confirmation against independent OpenF1 races."""
import argparse
from collections import defaultdict
from datetime import datetime
from itertools import combinations, groupby
from pathlib import Path

import numpy as np
import requests
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from scipy.stats import theilslopes

COMPOUNDS = ("SOFT", "MEDIUM", "HARD")
SESSIONS = {9912: (16, 1268), 9839: (24, 1276)}
ENDPOINTS = ("sessions", "laps", "stints", "race_control", "weather")
HORIZON = 9
PROTOCOL = Path(__file__).resolve().parents[1]/"protocols/COMPOUND_CROSSOVER_V2.md"


def hashes():
    return {p.name: file_sha256(p) for p in (Path(__file__), PROTOCOL)}


def calibrate(path):
    data = read_json(path)
    check_seal(data)
    by_compound = defaultdict(list)
    for segment in data["segments"]:
        if segment["round_number"] not in (1, 3, 6):
            continue
        assert_development_event(segment["season"], segment["round_number"], event_id=segment["event_id"])
        if segment["season"] != 2024 or segment["compound"] not in COMPOUNDS:
            raise ValueError("Unexpected calibration segment")
        y = [row["corrected_s"] for row in segment["rows"]]
        x = [row["tyre_age"] for row in segment["rows"]]
        by_compound[segment["compound"]].append(float(theilslopes(y, x).slope))
    return seal({"source_sha256": data["content_sha256"], "implementation": hashes(),
                 "training_rounds": [1, 3, 6],
                 "slopes": {c: max(0., float(np.median(by_compound[c]))) for c in COMPOUNDS},
                 "segments": {c: len(by_compound[c]) for c in COMPOUNDS}})


def acquire(output):
    output.mkdir(parents=True)
    for session, (round_number, _) in SESSIONS.items():
        assert_development_event(2025, round_number)
        for endpoint in ENDPOINTS:
            response = requests.get(f"https://api.openf1.org/v1/{endpoint}",
                                    params={"session_key": session}, timeout=45)
            response.raise_for_status()
            rows = response.json()
            if not isinstance(rows, list) or not rows or any(r.get("session_key") != session for r in rows):
                raise ValueError(f"Invalid {endpoint} response for {session}")
            write_manifest(output/f"{session}-{endpoint}.json", rows)
    write_manifest(output/"manifest.json", seal({"files": {p.name: file_sha256(p) for p in output.iterdir()}}))


def timestamp(value):
    return datetime.fromisoformat(value).timestamp()


def stint_rows(tables):
    """Retain only timed stint interiors with supported clean and dry context."""
    conditions = []
    for row in tables["race_control"]:
        if row.get("scope") != "Track":
            continue
        flag = row.get("flag")
        if flag in ("YELLOW", "DOUBLE YELLOW", "RED", "GREEN", "CLEAR"):
            conditions.append((timestamp(row["date"]), flag in ("YELLOW", "DOUBLE YELLOW", "RED")))
        message = (row.get("message") or "").upper()
        if "DEPLOYED" in message and ("SAFETY CAR" in message or "VSC" in message):
            conditions.append((timestamp(row["date"]), True))
    conditions.sort()
    weather = sorted((timestamp(r["date"]), r.get("rainfall")) for r in tables["weather"])

    def supported(start, end):
        before = [wet for time, wet in weather if time <= start]
        recent = [bad for time, bad in conditions if time <= start]
        return (bool(before) and before[-1] == 0
                and not any(wet != 0 for time, wet in weather if start < time < end)
                and not (recent and recent[-1])
                and not any(bad for time, bad in conditions if start < time < end))

    stints = defaultdict(list)
    laps = defaultdict(list)
    for row in tables["laps"]:
        laps[row["driver_number"]].append(row)
    for stint in tables["stints"]:
        compound = stint["compound"]
        if compound not in COMPOUNDS or stint.get("tyre_age_at_start") is None:
            continue
        first, last = stint["lap_start"], stint["lap_end"]
        if not isinstance(first, int) or not isinstance(last, int):
            continue
        values = {}
        for row in laps[stint["driver_number"]]:
            lap, duration = row["lap_number"], row.get("lap_duration")
            if not first < lap < last or row.get("is_pit_out_lap") is not False or not row.get("date_start"):
                continue
            if duration is None or not np.isfinite(duration) or duration <= 0:
                continue
            start = timestamp(row["date_start"])
            if supported(start, start+duration):
                age = stint["tyre_age_at_start"] + lap-first+1
                values[age] = duration - max(0., 105-1.4*(lap-1))*.03
        stints[stint["driver_number"]].append((stint["stint_number"], compound, values))
    return stints


def sign_change(start, end):
    return start*end < 0 and min(abs(start), abs(end)) > .15


def evaluate(frozen, archive):
    check_seal(frozen)
    if frozen["implementation"] != hashes():
        raise ValueError("Frozen implementation mismatch")
    manifest = read_json(archive/"manifest.json")
    check_seal(manifest)
    expected = {f"{session}-{endpoint}.json" for session in SESSIONS for endpoint in ENDPOINTS}
    if set(manifest["files"]) != expected:
        raise ValueError("Race archive inventory mismatch")
    cases, metrics = [], []
    for session, (round_number, meeting) in SESSIONS.items():
        assert_development_event(2025, round_number)
        tables = {}
        for endpoint in ENDPOINTS:
            name = f"{session}-{endpoint}.json"
            if file_sha256(archive/name) != manifest["files"][name]:
                raise ValueError("Race archive hash mismatch")
            tables[endpoint] = read_json(archive/name)
        identity = tables["sessions"]
        if (len(identity) != 1 or identity[0]["year"] != 2025
                or identity[0]["session_name"] != "Race" or identity[0]["meeting_key"] != meeting
                or identity[0]["session_key"] != session):
            raise ValueError("Race identity mismatch")
        event_cases, unsupported = [], 0
        for driver, stints in sorted(stint_rows(tables).items()):
            for (i, a, x), (j, b, y) in combinations(stints, 2):
                if a == b:
                    continue
                count = 0
                for _, group in groupby(enumerate(sorted(x.keys() & y.keys())), lambda pair: pair[1]-pair[0]):
                    ages = [age for _, age in group]
                    width = HORIZON+3
                    for offset in range(0, len(ages)-width+1, width):
                        block = ages[offset:offset+width]
                        difference = [x[age]-y[age] for age in block]
                        start, actual = (float(np.median(part)) for part in (difference[:3], difference[-3:]))
                        predicted = start+HORIZON*(frozen["slopes"][a]-frozen["slopes"][b])
                        event_cases.append({"session": session, "driver": driver, "stints": [i, j],
                                            "compounds": [a, b], "ages": block, "prefix_s": start,
                                            "actual_s": actual, "predicted_s": predicted,
                                            "observed_crossover": sign_change(start, actual),
                                            "predicted_crossover": sign_change(start, predicted)})
                        count += 1
                unsupported += count == 0
        observed = sum(c["observed_crossover"] for c in event_cases)
        predicted = sum(c["predicted_crossover"] for c in event_cases)
        matched = sum(c["observed_crossover"] and c["predicted_crossover"] for c in event_cases)
        mae = float(np.mean([abs(c["predicted_s"]-c["actual_s"]) for c in event_cases])) if event_cases else None
        baseline = float(np.mean([abs(c["prefix_s"]-c["actual_s"]) for c in event_cases])) if event_cases else None
        metrics.append({"session": session, "blocks": len(event_cases), "unsupported_pairs": unsupported,
                        "observed": observed, "predicted": predicted, "matched": matched, "mae_s": mae,
                        "persistence_mae_s": baseline, "passed": observed > 0 and predicted > 0
                        and 2*matched >= max(observed, predicted) and mae <= baseline})
        cases.extend(event_cases)
    return seal({"calibration_sha256": frozen["content_sha256"], "archive_sha256": manifest["content_sha256"],
                 "metrics": metrics, "cases": cases, "passed": all(row["passed"] for row in metrics)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("fit", "acquire", "evaluate"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--frozen", type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if args.stage == "acquire":
        acquire(args.output)
    elif args.stage == "fit":
        write_manifest(args.output, calibrate(args.dataset))
    else:
        write_manifest(args.output, evaluate(read_json(args.frozen), args.archive))


if __name__ == "__main__":
    main()
