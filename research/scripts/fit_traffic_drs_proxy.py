"""Test whether completed-lap DRS adds information about subsequent order changes."""

import argparse
from collections import Counter
from itertools import pairwise
from math import log
from pathlib import Path
from statistics import mean

import numpy as np
import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from calibrate_pit_expanded import PARENT
from calibrate_pit_timing import BASE


def drs_history(seconds, codes, start, end):
    if not start < end:
        return None
    a, b = np.searchsorted(seconds, (start, end), side="left")
    x, y = seconds[a:b], codes[a:b]
    spans = np.diff(x)
    valid = np.isfinite(y)
    usable = (spans > 0) & (spans <= 1) & valid[:-1] & valid[1:]
    if spans[usable].sum() < 0.90 * (end - start):
        return None
    return bool(spans[usable & np.isin(y[:-1], (10, 12, 14))].sum() >= 1.0)


def observations(table, telemetry):
    clean = table[
        (table.TrackStatus == "1")
        & table.IsAccurate.eq(True)
        & table.PitInTime.isna()
        & table.PitOutTime.isna()
    ].dropna(subset=["Time", "LapStartTime", "LapNumber", "DriverNumber"])
    groups = {
        int(lap): {
            str(d): (start.total_seconds(), end.total_seconds())
            for d, start, end in rows[
                ["DriverNumber", "LapStartTime", "Time"]
            ].itertuples(index=False, name=None)
        }
        for lap, rows in clean.groupby("LapNumber")
    }
    if sum(map(len, groups.values())) != len(clean):
        raise ValueError("Duplicate clean traffic lap")
    cases, unsupported = [], 0
    for lap, group in groups.items():
        following = groups.get(lap + 1, {})
        arrivals = sorted(group, key=lambda d: group[d][1])
        for ahead, behind in pairwise(arrivals):
            start, end = group[behind]
            gap = end - group[ahead][1]
            if ahead not in following or behind not in following or not 0 < gap <= 2:
                continue
            drs = (
                drs_history(*telemetry[behind], start, end)
                if behind in telemetry
                else None
            )
            if drs is None:
                unsupported += 1
                continue
            cases.append(
                {
                    "lap": lap,
                    "ahead": ahead,
                    "behind": behind,
                    "gap_s": gap,
                    "drs": drs,
                    "reversal": following[behind][1] < following[ahead][1],
                }
            )
    return cases, unsupported


def predict(training, cases):
    totals, events = Counter(), Counter()
    for r in training:
        band = int(r["gap_s"] > 1)
        for key in ((band,), (band, r["drs"])):
            totals[key] += 1
            events[key] += r["reversal"]
    metrics = {}
    for use_drs in (False, True):
        estimates = []
        for r in cases:
            band = int(r["gap_s"] > 1)
            key = (band, r["drs"]) if use_drs else (band,)
            key = key if totals[key] else (band,)
            p = (events[key] + 0.5) / (totals[key] + 1)
            estimates.append((p, r["reversal"]))
        metrics["gap_and_drs" if use_drs else "gap_only"] = {
            "expected_reversals": sum(p for p, _ in estimates),
            "brier": mean((p - y) ** 2 for p, y in estimates),
            "log_loss": mean(-log(p if y else 1 - p) for p, y in estimates),
        }
    return metrics


def run(root):
    parent = read_json(PARENT)
    check_seal(parent)
    inventory = {}
    for event, expected in (parent["training"] | parent["evaluation"]).items():
        _, year, label = event.split("_")
        year, number = int(year), int(label[1:])
        assert_development_event(year, number, event_id=event)
        folder = (
            f"r026-fastf1-2023-r{number}-race-20261013"
            if year == 2023
            else f"fastf1-2024-r{number}-race-20261011"
        )
        archive = root / folder
        manifest = verify_fastf1_archive(archive)
        if manifest["content_sha256"] != expected["source_sha256"]:
            raise ValueError("Traffic archive differs from frozen inventory")
        data = archive / "tables"
        laps = pd.read_parquet(
            data / "laps.parquet",
            columns=[
                "TrackStatus",
                "IsAccurate",
                "PitInTime",
                "PitOutTime",
                "Time",
                "LapStartTime",
                "LapNumber",
                "DriverNumber",
            ],
        )
        telemetry = {}
        for path in sorted((data / "car_data").glob("*.parquet")):
            samples = pd.read_parquet(path, columns=["SessionTime", "DRS"]).dropna(
                subset=["SessionTime"]
            )
            samples = samples.sort_values("SessionTime", kind="stable")
            telemetry[path.stem] = (
                samples.SessionTime.dt.total_seconds().to_numpy(),
                samples.DRS.astype(float).to_numpy(),
            )
        rows, skipped = observations(laps, telemetry)
        inventory[event] = {
            "source_sha256": expected["source_sha256"],
            "rows": rows,
            "missing_telemetry": skipped,
        }
    training = [r for event in parent["training"] for r in inventory[event]["rows"]]
    folds = {}
    for event in parent["evaluation"]:
        rows = inventory[event]["rows"]
        folds[event] = {
            "cases": len(rows),
            "reversals": sum(r["reversal"] for r in rows),
            **predict(training, rows),
        }
    return seal(
        {
            "schema": "apex-r050-drs-association-v1",
            "training_cases": len(training),
            "races": inventory,
            "folds": folds,
            "qualified_traffic_model": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
