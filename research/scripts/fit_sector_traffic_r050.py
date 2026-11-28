"""Calibrate and confirm the R050 sector following-pace associations."""

import argparse
from collections import defaultdict
from itertools import pairwise, product
from math import isfinite
from pathlib import Path
from statistics import mean

import numpy as np
import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import write_manifest
from apexsim.research.evidence import seal
from apexsim.research.longitudinal_data import DRS_STATES
from archive_r050_overtakes import cohort
from calibrate_pit_timing import BASE
from fit_green_traffic_r050 import LAP_FIELDS, lap_timing, load_drs, pace_summary

SECTOR_CLOCKS = ["LapStartTime", *(f"Sector{i}SessionTime" for i in (1, 2, 3))]
SECTOR_DURATIONS = [f"Sector{i}Time" for i in (1, 2, 3)]


def sector_drs(telemetry, start, end):
    seconds, codes = telemetry
    a, b = np.searchsorted(seconds, (start, end), side="left")
    times, values = seconds[a:b], codes[a:b]
    spans = np.diff(times)
    known = np.isin(values, tuple(DRS_STATES))
    valid = (spans > 0) & (spans <= 1) & known[:-1] & known[1:]
    if spans[valid].sum() < 0.90 * (end - start):
        return None
    opened = np.isin(values, [code for code, state in DRS_STATES.items() if state])
    open_s = spans[valid & opened[:-1]].sum()
    if open_s >= 1:
        return True
    return False if not opened.any() else None


def observed_sectors(laps, telemetry):
    _, clean = lap_timing(laps)
    clocks = defaultdict(dict)
    for row in laps.itertuples(index=False):
        tuple_clocks = (getattr(row, k) for k in SECTOR_CLOCKS)
        for checkpoint, clock in enumerate(tuple_clocks):
            if pd.notna(clock):
                clocks[(int(row.LapNumber), checkpoint)][str(row.DriverNumber)] = clock.total_seconds()
    predecessor = {
        k: {follower: leader for leader, follower in pairwise(sorted(arrivals, key=arrivals.__getitem__))}
        for k, arrivals in clocks.items()
    }
    observations = defaultdict(list)
    for lap, field in sorted(clean.items()):
        if lap < 4:
            continue
        for sector, duration_column in enumerate(SECTOR_DURATIONS):
            origin, target = (lap, sector), (lap, sector + 1)
            for driver, leader in predecessor.get(origin, {}).items():
                if (
                    driver not in field
                    or leader not in field
                    or driver not in telemetry
                    or predecessor.get(target, {}).get(driver) != leader
                ):
                    continue
                row = field[driver]
                t0, t1 = clocks[origin][driver], clocks[target][driver]
                gap = t0 - clocks[origin][leader]
                duration = getattr(row, duration_column)
                if (
                    not (0 < gap <= 1 or 2 <= gap <= 4)
                    or pd.isna(duration)
                    or not isfinite(row.Stint)
                    or not isfinite(row.TyreLife)
                    or t1 <= t0
                ):
                    continue
                duration_s = duration.total_seconds()
                if abs(t1 - t0 - duration_s) > 0.15:
                    continue
                opened = sector_drs(telemetry[driver], t0, t1)
                if opened is None or (gap >= 2 and opened):
                    continue
                state = "drs" if opened else ("close" if gap <= 1 else "clear")
                observations[(driver, int(row.Stint), sector)].append(
                    (state, lap, row.TyreLife, duration_s, gap)
                )
    return observations


def match_sectors(groups):
    contrasts = {"following": [], "drs": []}
    for rows in groups.values():
        for term, treated, control in (("following", "close", "clear"), ("drs", "drs", "close")):
            candidates = sorted(
                (abs(a[2] - b[2]), abs(a[4] - b[4]), a[1], b[1], a[3] - b[3], a[2] - b[2])
                for a, b in product(
                    (r for r in rows if r[0] == treated), (r for r in rows if r[0] == control)
                )
                if abs(a[2] - b[2]) <= 5 and (term != "drs" or abs(a[4] - b[4]) <= 0.35)
            )
            used_a, used_b = set(), set()
            for _, _, lap_a, lap_b, effect, age in candidates:
                if lap_a in used_a or lap_b in used_b:
                    continue
                used_a.add(lap_a)
                used_b.add(lap_b)
                contrasts[term].append((effect, age))
    return contrasts


def evaluate(panels):
    reports = {year: pace_summary(panel) for year, panel in panels.items()}
    gates, calibration = {}, {}
    for term, sign in (("following", 1), ("drs", -1)):
        adjustment = reports[2023][term]["median_race_effect_s"]
        calibration[term] = adjustment
        confirmation = [values[term] for values in panels[2022].values() if values[term]]
        absolute_error = {
            "zero_s": mean(mean(abs(diff) for diff, _ in rows) for rows in confirmation)
            if confirmation
            else None,
            "calibrated_s": (
                mean(mean(abs(diff - adjustment) for diff, _ in rows) for rows in confirmation)
                if confirmation and adjustment is not None
                else None
            ),
        }
        reports[2022][term]["race_weighted_absolute_error"] = absolute_error
        signs = {
            year: sum(
                r["median_s"] is not None and r["median_s"] * sign > 0 for r in report[term]["races"].values()
            )
            for year, report in reports.items()
        }
        gates[term] = {
            "support": min(report[term]["pairs"] for report in reports.values()) >= 25,
            "development_sign": adjustment is not None and adjustment * sign > 0,
            "validation_sign": signs[2024] >= 3,
            "confirmation_sign": signs[2022] >= 2,
            "confirmation_score": (
                absolute_error["calibrated_s"] is not None
                and absolute_error["calibrated_s"] < absolute_error["zero_s"]
            ),
        }
    return {
        "calibration_s": calibration,
        "panels": {str(year): report for year, report in reports.items()},
        "gates": gates,
        "qualified": all(all(values.values()) for values in gates.values()),
    }


def run(native_root):
    extra = []
    for number in (3, 5, 17):
        event = f"F1_2022_R{number:02}"
        assert_development_event(2022, number, event_id=event)
        extra.append((event, 2022, native_root / f"r045-fastf1-2022-r{number}", None))
    panels, sources = defaultdict(dict), {}
    for event, year, path, expected in [*cohort(native_root), *extra]:
        archive = verify_fastf1_archive(path)
        source = archive["content_sha256"]
        if (
            archive["identity"]["year"] != year
            or archive["identity"]["round_number"] != int(event[-2:])
            or archive["identity"]["session_name"] != "Race"
            or (expected is not None and source != expected)
        ):
            raise ValueError(f"Sector replay archive mismatch for {event}")
        sources[event] = source
        tables = path / "tables"
        columns = list(dict.fromkeys([*LAP_FIELDS, *SECTOR_CLOCKS, *SECTOR_DURATIONS]))
        laps = pd.read_parquet(tables / "laps.parquet", columns=columns)
        laps = laps.dropna(subset=["DriverNumber", "LapNumber"])
        panels[year][event] = match_sectors(observed_sectors(laps, load_drs(tables)))
    return seal(
        {
            "schema": "apex-r050-sector-traffic-v1",
            "fastf1_archives": sources,
            **evaluate(panels),
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
