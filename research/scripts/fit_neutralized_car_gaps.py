"""R049 event-held-out matched per-car timing-gap replay."""

import argparse
from bisect import bisect_right
from collections import defaultdict
from itertools import product
from pathlib import Path
from statistics import mean, median

import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from apexsim.research.neutralized_gaps import scale_gaps
from confirm_compound_crossover import timestamp
from confirm_compound_multiseason import canonical_file_sha
from fit_neutralization_span import activity
from prepare_compound_pit_exit import BASE, FOLDER, MAPPING, tables_from_archive

MODES = ("4", "6")


def episodes(status):
    for i, (start, mode) in enumerate(status):
        if mode not in MODES or (i and status[i - 1][1] in (*MODES, "7")):
            continue
        for end, code in status[i + 1 :]:
            if code == "1":
                if end > start:
                    yield start, end, mode
                break
            if code in ("0", "5") or code in MODES and code != mode:
                break


def snapshots(rows, status):
    observations = []
    for start, release, mode in episodes(status):
        phases = [defaultdict(dict) for _ in range(3)]
        for lap, driver, begin, end, green in rows:
            if not begin < end:
                continue
            if green and start - 240 <= end < start:
                phases[0][lap][driver] = end
            if start <= end < release:
                phases[1][lap][driver] = end
            if green and begin >= release and end <= release + 240:
                phases[2][lap][driver] = end
        possibilities = []
        for (n, a), (m, b), (p, c) in product(*(phase.items() for phase in phases)):
            common = a.keys() & b.keys() & c.keys()
            if len(common) >= 5 and n < m < p:
                possibilities.append((len(common), n, m, -p, common, (a, b, c)))
        identity = {"mode": mode, "start_s": start, "release_s": release}
        if not possibilities:
            observations.append({**identity, "supported": False})
            continue
        _, n, m, minus_p, common, clocks = max(possibilities, key=lambda x: x[:4])
        drivers = sorted(common, key=lambda d: (clocks[0][d], d))
        earliest = [min(clock[d] for d in drivers) for clock in clocks]
        gaps = [
            [clock[d] - first for d in drivers]
            for clock, first in zip(clocks, earliest, strict=True)
        ]
        observations.append(
            {
                **identity,
                "supported": True,
                "lap_numbers": [n, m, -minus_p],
                "drivers": drivers,
                "gaps_s": gaps,
                "observed_order_changed": [v != sorted(v) for v in gaps[1:]],
            }
        )
    return observations


def openf1_rows(tables):
    status = activity(tables["race_control"])
    times = [t for t, _ in status]
    pits = {
        (r["driver_number"], r["lap_number"])
        for r in tables["laps"]
        if r["is_pit_out_lap"] is True
    }
    rows = []
    for row in tables["laps"]:
        d, n, elapsed = row["driver_number"], row["lap_number"], row["lap_duration"]
        if (
            not row["date_start"]
            or elapsed is None
            or elapsed <= 0
            or row["is_pit_out_lap"] is not False
            or (d, n + 1) in pits
        ):
            continue
        start = timestamp(row["date_start"])
        end = start + elapsed
        a, b = bisect_right(times, start), bisect_right(times, end)
        green = (a == 0 or status[a - 1][1] == "1") and all(
            code == "1" for _, code in status[a:b]
        )
        rows.append((n, str(d), start, end, green))
    return rows, status


def fastf1_rows(root, event, sha):
    _, year, rd = event.split("_")
    number = int(rd[1:])
    assert_development_event(int(year), number, event_id=event)
    folder = (
        f"r026-fastf1-2023-r{number}-race-20261013"
        if year == "2023"
        else f"fastf1-2024-r{number}-race-20261011"
    )
    archive = root / folder
    if verify_fastf1_archive(archive)["content_sha256"] != sha:
        raise ValueError("R049 FastF1 source changed")
    table = archive / "tables"
    columns = [
        "LapNumber",
        "DriverNumber",
        "LapStartTime",
        "Time",
        "TrackStatus",
        "PitInTime",
        "PitOutTime",
    ]
    frame = pd.read_parquet(table / "laps.parquet", columns=columns)
    frame = frame[frame.PitInTime.isna() & frame.PitOutTime.isna()].dropna(
        subset=columns[:4]
    )
    rows = [
        (int(n), str(d), a.total_seconds(), b.total_seconds(), f == "1")
        for n, d, a, b, f in frame[columns[:5]].itertuples(index=False, name=None)
    ]
    status = pd.read_parquet(table / "track_status.parquet", columns=["Time", "Status"])
    return rows, sorted(
        (t.total_seconds(), str(s))
        for t, s in status.itertuples(index=False, name=None)
    )


def parameters(races, mode):
    by_race = []
    for event in races.values():
        ratios = []
        for row in event:
            if not row["supported"] or row["mode"] != mode:
                continue
            before, during, after = map(sum, row["gaps_s"])
            if min(before, during, after) > 0:
                ratios.append((during / before, after / before))
        if ratios:
            by_race.append([median(x[i] for x in ratios) for i in (0, 1)])
    if len(by_race) < 2:
        return None
    return [
        median(x[0] for x in by_race),
        1.0 if mode == "6" else median(x[1] for x in by_race),
    ]


def score(races):
    folds = []
    for event, rows in sorted(races.items()):
        train = {e: r for e, r in races.items() if e != event}
        factors = {mode: parameters(train, mode) for mode in MODES}
        for row in rows:
            mode = row["mode"]
            if not row["supported"] or factors[mode] is None:
                continue
            before, *actual = row["gaps_s"]
            predicted = [scale_gaps(before, f) for f in factors[mode]]
            folds.append(
                {
                    "event": event,
                    "mode": mode,
                    "start_s": row["start_s"],
                    "release_s": row["release_s"],
                    "predicted_s": predicted,
                    "actual_s": actual,
                    "drivers": row["drivers"],
                    "candidate_mae_s": [
                        mean(abs(a - b) for a, b in zip(p, y, strict=True))
                        for p, y in zip(predicted, actual, strict=True)
                    ],
                    "persistence_mae_s": [
                        mean(abs(a - b) for a, b in zip(before, y, strict=True))
                        for y in actual
                    ],
                }
            )
    metrics = {}
    for mode in MODES:
        events = defaultdict(list)
        for row in folds:
            if row["mode"] == mode:
                events[row["event"]].append(row)
        agg = (
            {
                key: [
                    mean(mean(r[key][i] for r in rows) for rows in events.values())
                    for i in (0, 1)
                ]
                for key in ("candidate_mae_s", "persistence_mae_s")
            }
            if events
            else {}
        )
        comparisons = list(
            zip(
                agg.get("candidate_mae_s", []),
                agg.get("persistence_mae_s", []),
                strict=True,
            )
        )
        metrics[mode] = {
            "races": len(events),
            "episodes": sum(map(len, events.values())),
            **agg,
            "passed": len(events) >= 3
            and all(a <= b for a, b in comparisons)
            and any(a < b for a, b in comparisons),
        }
    return {
        "folds": folds,
        "metrics": metrics,
        "passed": all(row["passed"] for row in metrics.values()),
    }


def run(root):
    prior = read_json(FOLDER / "race-model-source-audit.json")
    cohort = read_json(FOLDER / "compound-v24-cohort.json")
    for item in (prior, cohort):
        check_seal(item)
    races = {
        e: snapshots(*fastf1_rows(root, e, row["source_sha256"]))
        for e, row in prior["races"].items()
    }
    sources = {e: row["source_sha256"] for e, row in prior["races"].items()}
    for event, source in cohort["sources"].items():
        if source["provider"] != "OPENF1":
            continue
        session = int(event)
        number, meeting, folder = MAPPING[session]
        tables, sha = tables_from_archive(root / folder, session, (number, meeting))
        if sha != source["archive_sha256"]:
            raise ValueError("R049 OpenF1 source changed")
        races[event] = snapshots(*openf1_rows(tables))
        sources[event] = sha
    return seal(
        {
            "schema": "apex-r049-per-car-gaps-v1",
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(
                BASE / "research/protocols/PER_CAR_RESTART_R049.md"
            ),
            "sources": sources,
            "races": races,
            "fit": {mode: parameters(races, mode) for mode in MODES},
            **score(races),
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
