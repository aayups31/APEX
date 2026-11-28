"""R048 retirement baseline and native source coverage for R049 and R050."""

import argparse
from collections import Counter
from itertools import pairwise
from math import log, log1p
from pathlib import Path

import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from calibrate_pit_expanded import PARENT
from calibrate_pit_timing import BASE


def retirement_exposure(results):
    """Reconstruct all-cause endpoint labels and avoid inventing retirement causes."""
    trials, events = [0, 0], [0, 0]
    excluded = Counter()
    for status, laps in results[["Status", "Laps"]].itertuples(index=False, name=None):
        if (
            status not in ("Retired", "Finished", "Lapped")
            or pd.isna(laps)
            or laps < 0
            or int(laps) != laps
        ):
            excluded[str(status)] += 1
            continue
        retired = status == "Retired"
        exposed = int(laps) + int(retired)
        trials[0] += int(exposed > 0)
        trials[1] += max(0, exposed - 1)
        if retired:
            events[int(exposed > 1)] += 1
    return {"trials": trials, "events": events, "excluded": dict(excluded)}


def hazard_score(training, held_out):
    totals = [sum(row["trials"][i] for row in training.values()) for i in (0, 1)]
    incidents = [sum(row["events"][i] for row in training.values()) for i in (0, 1)]
    common = (sum(incidents) + 0.5) / (sum(totals) + 1)
    split = [(k + 0.5) / (n + 1) for k, n in zip(incidents, totals, strict=True)]
    folds = {}
    for race, row in held_out.items():
        trials, events = row["trials"], row["events"]
        arms = {}
        for name, p in (("constant", [common] * 2), ("first_lap", split)):
            arms[name] = {
                "expected_conditional_on_exposure": sum(
                    n * q for n, q in zip(trials, p, strict=True)
                ),
                "negative_log_likelihood": -sum(
                    k * log(q) + (n - k) * log1p(-q)
                    for n, k, q in zip(trials, events, p, strict=True)
                ),
            }
        folds[race] = {"observed": sum(events), **arms}
    return {
        "constant_hazard": common,
        "split_hazard": split,
        "folds": folds,
        "total_negative_log_likelihood": {
            key: sum(row[key]["negative_log_likelihood"] for row in folds.values())
            for key in ("constant", "first_lap")
        },
    }


def pass_opportunities(laps):
    """Count close running-order reversals across consecutive clean timing lines."""
    clean = laps[
        (laps["TrackStatus"] == "1")
        & laps["IsAccurate"].eq(True)
        & laps["PitInTime"].isna()
        & laps["PitOutTime"].isna()
    ].dropna(subset=["Time", "LapNumber", "DriverNumber"])
    groups = {
        lap: dict(zip(group.DriverNumber, group.Time, strict=True))
        for lap, group in clean.groupby("LapNumber")
    }
    if sum(map(len, groups.values())) != len(clean):
        raise ValueError("Duplicate green driver/lap timing")
    eligible, reversals = 0, 0
    for lap, group in groups.items():
        later = groups.get(lap + 1, {})
        for (leader, ahead), (follower, behind) in pairwise(
            sorted(group.items(), key=lambda x: x[1])
        ):
            if (
                leader not in later
                or follower not in later
                or not 0 < (behind - ahead).total_seconds() <= 2
            ):
                continue
            eligible += 1
            reversals += int(later[follower] < later[leader])
    return {"close_clean_intervals": eligible, "timing_line_reversals": reversals}


def neutralization_windows(laps, status):
    """Find comparable on-track field snapshots around complete SC/VSC phases."""
    ordered = list(
        status.sort_values("Time", kind="stable").itertuples(index=False, name=None)
    )
    groups = list(
        laps.dropna(subset=["LapNumber", "LapStartTime", "Time"]).groupby("LapNumber")
    )
    rows = []
    for i, (start, mode) in enumerate(ordered):
        if mode not in ("4", "6") or (i and ordered[i - 1][1] in ("4", "6", "7")):
            continue
        finish = next((t for t, code in ordered[i + 1 :] if code == "1"), None)
        if finish is None or any(
            code == "5" for t, code in ordered[i + 1 :] if t < finish
        ):
            continue
        windows = []
        for low, high, last, green in (
            (None, start, True, True),
            (start, finish, True, False),
            (finish, None, False, True),
        ):
            candidates = []
            for lap, frame in groups:
                chosen = frame[frame.PitInTime.isna() & frame.PitOutTime.isna()]
                if green:
                    chosen = chosen[chosen.TrackStatus == "1"]
                if low is not None:
                    chosen = chosen[chosen.LapStartTime >= low]
                if high is not None:
                    chosen = chosen[chosen.Time <= high]
                clocks = dict(zip(chosen.DriverNumber, chosen.Time, strict=True))
                if len(clocks) >= 5:
                    candidates.append((lap, clocks))
            windows.append(
                (candidates[-1] if last else candidates[0]) if candidates else None
            )
        if any(window is None for window in windows):
            rows.append({"mode": mode, "supported": False})
            continue
        drivers = set.intersection(*(set(clock) for _, clock in windows))
        if len(drivers) < 5:
            rows.append({"mode": mode, "supported": False})
            continue
        spans = [
            max(clock[d] for d in drivers) - min(clock[d] for d in drivers)
            for _, clock in windows
        ]
        rows.append(
            {
                "mode": mode,
                "supported": True,
                "drivers": len(drivers),
                "lap_numbers": [int(lap) for lap, _ in windows],
                "field_span_s": [span.total_seconds() for span in spans],
            }
        )
    return rows


def inspect(root, event, parent):
    _, year, round_label = event.split("_")
    year, number = int(year), int(round_label[1:])
    assert_development_event(year, number, event_id=event)
    folder = (
        f"r026-fastf1-2023-r{number}-race-20261013"
        if year == 2023
        else f"fastf1-2024-r{number}-race-20261011"
    )
    archive = root / folder
    manifest = verify_fastf1_archive(archive)
    q = manifest["query"]
    if (q["year"], q["round_number"], q["session"]) != (year, number, "R") or (
        manifest["content_sha256"] != parent["source_sha256"]
    ):
        raise ValueError("Race source differs from R045 inventory")
    tables = archive / "tables"
    status = pd.read_parquet(
        tables / "track_status.parquet", columns=["Time", "Status"]
    )
    laps = pd.read_parquet(
        tables / "laps.parquet",
        columns=[
            "DriverNumber",
            "LapNumber",
            "LapStartTime",
            "Time",
            "TrackStatus",
            "IsAccurate",
            "PitInTime",
            "PitOutTime",
        ],
    )
    intervals = [
        (start, end, mode)
        for (start, mode), (end, _) in pairwise(
            status.sort_values("Time", kind="stable").itertuples(index=False, name=None)
        )
        if mode in ("4", "6", "7") and start < end
    ]
    neutralized = Counter()
    for start, end, mode in intervals:
        neutralized[mode] += int(((laps.Time >= start) & (laps.Time < end)).sum())
    files = manifest["files"]
    clean = (
        (laps["TrackStatus"] == "1")
        & laps["IsAccurate"].eq(True)
        & laps["PitInTime"].isna()
        & laps["PitOutTime"].isna()
        & laps.Time.notna()
    )
    return {
        "source_sha256": manifest["content_sha256"],
        "retirement": retirement_exposure(
            pd.read_parquet(tables / "results.parquet", columns=["Status", "Laps"])
        ),
        "race_control": {
            "track_status_codes": status.Status.value_counts().to_dict(),
            "bounded_neutralization_segments": dict(
                Counter(mode for _, _, mode in intervals)
            ),
            "lap_ends_in_neutralization": dict(neutralized),
            "matched_field_windows": neutralization_windows(laps, status),
        },
        "traffic": {
            "clean_green_lap_ends": int(clean.sum()),
            "drivers_with_clean_green_lap_ends": int(
                laps.loc[clean, "DriverNumber"].nunique()
            ),
            "archived_car_tables": sum(
                name.startswith("tables/car_data/") for name in files
            ),
            "archived_position_tables": sum(
                name.startswith("tables/pos_data/") for name in files
            ),
            **pass_opportunities(laps),
        },
    }


def run(root):
    parent = read_json(PARENT)
    check_seal(parent)
    results = {
        event: inspect(root, event, row)
        for event, row in (parent["training"] | parent["evaluation"]).items()
    }
    hazards = hazard_score(
        *[
            {e: results[e]["retirement"] for e in parent[split]}
            for split in ("training", "evaluation")
        ]
    )
    return seal(
        {
            "schema": "apex-race-model-source-audit-v1",
            "source_parent_sha256": parent["content_sha256"],
            "races": results,
            "r048_all_cause_baseline": hazards,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
