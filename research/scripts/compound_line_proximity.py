"""Join forecast-time timing-line proximity from the two archived providers."""

import argparse
from bisect import bisect_left
from math import isfinite
from pathlib import Path
from statistics import median

import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_context import utc
from diagnose_compound_decision import ROOT
from prepare_compound_trajectory import OPENED, V9, tables_from_archive


def archive_crossings(root, event, source):
    if source["provider"] == "OPENF1":
        sessions = {
            **OPENED,
            **{k: (*v, "r041-v9-confirmation-20261104") for k, v in V9.items()},
        }
        number, meeting, folder = sessions[int(event)]
        tables, digest = tables_from_archive(
            root / folder, int(event), (number, meeting)
        )
        laps = [
            (r["driver_number"], utc(r["date_start"]), r["lap_duration"])
            for r in tables["laps"]
            if r["date_start"] and r["lap_duration"] is not None
        ]
    elif source["provider"] == "FASTF1":
        _, year, race = event.split("_")
        number = int(race[1:])
        assert_development_event(int(year), number, event_id=event)
        folder = (
            f"fastf1-2024-r{number}-race-20261011"
            if year == "2024"
            else f"r026-fastf1-2023-r{number}-race-20261013"
        )
        archive = root / folder
        manifest = verify_fastf1_archive(archive)
        q = manifest["query"]
        if (q["year"], q["round_number"], q["session"]) != (int(year), number, "R"):
            raise ValueError("FastF1 race mismatch")
        digest = manifest["content_sha256"]
        frame = pd.read_parquet(
            archive / "tables/laps.parquet",
            columns=["DriverNumber", "LapStartDate", "LapTime"],
        )
        laps = [
            (int(driver), utc(start), elapsed.total_seconds())
            for driver, start, elapsed in frame.dropna().itertuples(
                index=False, name=None
            )
        ]
    else:
        raise ValueError("Unknown timing-line provider")
    if digest != source["archive_sha256"]:
        raise ValueError("Timing-line archive differs from frozen cohort")
    return sorted(
        (start + duration, driver)
        for driver, start, duration in laps
        if isfinite(start + duration) and duration > 0
    )


def link(row, crossings, identities):
    groups = (
        row["current_history"][-3:],
        row["reference_history"][:3],
        row["reference_history"][-3:],
    )
    result = []
    for history in groups:
        if len(history) != 3:
            raise ValueError("Incomplete timing-line window")
        group = []
        for lap in history:
            end, driver = lap["end_s"], row["driver"]
            if end > row["forecast_at_s"] or (end, driver) not in identities:
                raise ValueError("Future or unmatched subject clock")
            # Tuple prefix selects strictly earlier times, including in a tie.
            window = crossings[
                bisect_left(crossings, (end - 10.0,)) : bisect_left(crossings, (end,))
            ]
            previous = next(((t, d) for t, d in reversed(window) if d != driver), None)
            group.append(previous)
        result.append(group)
    return result


def proximity_features(row, links):
    histories = (
        row["current_history"][-3:],
        row["reference_history"][:3],
        row["reference_history"][-3:],
    )
    values = []
    for group, history in zip(links, histories, strict=True):
        gaps = []
        for previous, lap in zip(group, history, strict=True):
            end = lap["end_s"]
            if end > row["forecast_at_s"]:
                raise ValueError("Subject clock exceeds forecast time")
            gap = 10.0
            if previous is not None:
                time, driver = previous
                gap = end - time
                if driver == row["driver"] or not 0 < gap <= 10.0:
                    raise ValueError("Invalid prior timing-line contributor")
            gaps.append(gap)
        if len(gaps) != 3:
            raise ValueError("Incomplete timing-line window")
        values.extend(
            [median(gaps), gaps[-1] - gaps[0], sum(g <= 1.5 for g in gaps) / 3]
        )
    return values


def prepare(root):
    data = read_json(ROOT / "docs/verification/compound-v11-development-data.json")
    check_seal(data)
    joins = [None] * len(data["cases"])
    for event, source in data["sources"].items():
        clocks = archive_crossings(root, event, source)
        identities = set(clocks)
        if len(identities) != len(clocks):
            raise ValueError("Duplicate driver timing-line clock")
        for i, row in enumerate(data["cases"]):
            if str(row["session"]) == event:
                joins[i] = link(row, clocks, identities)
    if any(join is None for join in joins):
        raise ValueError("Missing timing-line joins")
    return seal(
        {
            "schema": "compound-timing-line-v15",
            "parent_sha256": data["content_sha256"],
            "joins": joins,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--native-root", type=Path, default=ROOT / ".cache")
    args = parser.parse_args()
    write_manifest(args.output, prepare(args.native_root))
