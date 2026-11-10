"""Distance-align known native laps and test added R041 speed-profile inputs."""

import argparse
from bisect import bisect_right
from collections import defaultdict
from itertools import accumulate, pairwise
from math import fsum, isfinite, log1p
from pathlib import Path
from statistics import mean, median

import numpy as np
import pandas as pd
from apexsim.provenance import write_manifest
from apexsim.research.compound_allocation import features, inventory
from apexsim.research.evidence import check_seal, read_json, seal
from apexsim.research.recorded_alignment import native_times
from audit_compound_driving import base_vector, driving_vector
from audit_compound_repair import compare
from compound_driving_data import car_snapshot, sample_matrix
from compound_line_proximity import archive_laps
from confirm_compound_multiseason import canonical_file_sha
from diagnose_compound_driving import driving_features
from diagnose_compound_pit_exit import BASE, FOLDER, evaluate
from prepare_compound_pit_exit_telemetry import covers, interval_groups

PROTOCOL = BASE / "research/protocols/COMPOUND_SPEED_PROFILE_V25.md"
BINS = 64


def native_profile(samples, start, end):
    """Return integrated metres and speed at the fixed bin centers."""
    inside = samples[(samples[:, 0] >= start) & (samples[:, 0] < end)]
    if len(inside) < 2:
        return None
    times, speed = inside.T
    gaps = np.diff(times)
    if (
        times[0] - start > 1.0
        or end - times[-1] > 1.0
        or gaps.min() <= 0
        or gaps.max() > 2.0
        or gaps[gaps <= 1.0].sum() < 0.95 * (end - start)
        or not np.isfinite(speed).all()
        or speed.min() < 0
        or speed.max() > 120
    ):
        return None
    if times[0] > start:
        times, speed = np.r_[start, times], np.r_[speed[0], speed]
    times, speed = np.r_[times, end], np.r_[speed, speed[-1]]
    steps = np.diff(times) * (speed[:-1] + speed[1:]) / 2.0
    distance = np.r_[0.0, steps.cumsum()]
    if steps.min() <= 0 or distance[-1] < 1000:
        return None
    centers = (np.arange(BINS) + 0.5) / BINS * distance[-1]
    return float(distance[-1]), np.interp(centers, distance, speed).tolist()


def scalar_profile(samples, start, end):
    """Independently integrate and interpolate the ordered native rows."""
    a, b = np.searchsorted(samples[:, 0], (start, end), side="left")
    rows = [(float(t), float(v)) for t, v in samples[a:b]]
    if (
        len(rows) < 2
        or rows[0][0] > start + 1.0
        or rows[-1][0] < end - 1.0
        or any(not isfinite(v) or v < 0 or v > 120 for _, v in rows)
    ):
        return None
    gaps = [right[0] - left[0] for left, right in pairwise(rows)]
    if (
        any(not 0 < gap <= 2.0 for gap in gaps)
        or fsum(g for g in gaps if g <= 1) < (end - start) * 0.95
    ):
        return None
    if rows[0][0] != start:
        rows.insert(0, (start, rows[0][1]))
    rows.append((end, rows[-1][1]))
    distances = list(
        accumulate(
            ((t2 - t1) * (v1 + v2) * 0.5 for (t1, v1), (t2, v2) in pairwise(rows)),
            initial=0.0,
        )
    )
    total = distances[-1]
    if total < 1000 or any(x >= y for x, y in pairwise(distances)):
        return None
    speeds = []
    for i in range(BINS):
        position = total * ((i + 0.5) / BINS)
        j = bisect_right(distances, position) - 1
        fraction = (position - distances[j]) / (distances[j + 1] - distances[j])
        speeds.append(rows[j][1] + fraction * (rows[j + 1][1] - rows[j][1]))
    return total, speeds


def speed_groups(groups):
    profiles = [lap for group in groups for lap in group]
    if any(lap is None for lap in profiles):
        return None
    distance = [lap[0] for lap in profiles]
    if max(distance) > 1.03 * min(distance):
        return None
    reference = np.median([p[1] for p in groups[1]], axis=0)
    order = np.argsort(reference, kind="stable")
    masks = [order[:16], order[-16:]]
    return [
        [
            [float(np.mean(np.asarray(v)[indices])) for indices in masks]
            for _, v in group
        ]
        for group in groups
    ]


def independent_groups(groups):
    all_laps = [p for group in groups for p in group]
    if any(p is None for p in all_laps):
        return None
    lengths = sorted(p[0] for p in all_laps)
    if lengths[-1] > lengths[0] * 1.03:
        return None
    _, reference = zip(*groups[1], strict=True)
    order = sorted(
        range(BINS), key=lambda j: (median(profile[j] for profile in reference), j)
    )
    return [
        [
            [mean(v[j] for j in indices) for indices in (order[:16], order[48:])]
            for _, v in group
        ]
        for group in groups
    ]


def profile_vector(groups):
    if groups is None:
        return [0.0] * 7
    data = np.asarray(groups)
    if (
        data.shape != (3, 3, 2)
        or not np.isfinite(data).all()
        or data.min() < 0
        or data.max() > 120
    ):
        raise ValueError("Invalid measured speed-profile groups")
    current, prefix, target = np.median(data, axis=1)
    return [*(current - prefix), *(current - target), *(data[0, -1] - data[0, 0]), 1.0]


def scalar_vector(groups):
    if groups is None:
        return [0.0] * 7
    current, ref_prefix, ref_target = [
        [median(values[j] for values in group) for j in range(2)] for group in groups
    ]
    return [
        *(a - b for a, b in zip(current, ref_prefix, strict=True)),
        *(a - b for a, b in zip(current, ref_target, strict=True)),
        *(groups[0][2][j] - groups[0][0][j] for j in range(2)),
        1.0,
    ]


def samples_for(native_root, event, source, driver, binding, start, end):
    if source["provider"] == "FASTF1":
        _, year, race = event.split("_")
        number = int(race[1:])
        folder = (
            f"fastf1-2024-r{number}-race-20261011"
            if year == "2024"
            else f"r026-fastf1-2023-r{number}-race-20261013"
        )
        if binding != source["archive_sha256"]:
            raise ValueError("Unbound FastF1 speed source")
        frame = pd.read_parquet(
            native_root / folder / f"tables/car_data/{driver}.parquet",
            columns=["Date", "Speed", "SessionTime", "Source"],
        )
        native_times(frame)
        car = frame[frame.Source == "car"]
        return np.column_stack(
            (
                pd.DatetimeIndex(car.Date).as_unit("ns").asi8 / 1e9,
                car.Speed.to_numpy(float) / 3.6,
            )
        )
    version = "v23" if binding["reused_v23"] else "v24"
    cache = native_root / f"r041-{version}-native-car"
    receipt = read_json(cache / f"{event}-{driver}.receipt.json")
    check_seal(receipt)
    query = receipt["query"]
    if receipt["content_sha256"] != binding["sha256"] or not covers(
        query, event, driver, start, end
    ):
        raise ValueError("Unbound OpenF1 speed receipt")
    rows, _ = car_snapshot(cache, event, driver, query, None)
    return sample_matrix(rows, event, driver)[:, :2]


def prepare(data, telemetry, native_root):
    for doc in (data, telemetry):
        check_seal(doc)
    if data["content_sha256"] != telemetry["dataset_sha256"]:
        raise ValueError("Speed-profile telemetry cohort mismatch")
    output = [None] * len(data["cases"])
    physical_laps = 0
    for event, source in data["sources"].items():
        native = archive_laps(native_root, event, source)
        durations = {(end, driver): duration for end, driver, _, duration in native}
        if len(durations) != len(native):
            raise ValueError("Ambiguous speed-profile lap clock")
        observations = defaultdict(dict)
        for i, row in enumerate(data["cases"]):
            if str(row["session"]) == event:
                observations[row["driver"]][i] = interval_groups(row, durations)
        bindings = telemetry["sources"][event]
        if bindings["archive_sha256"] != source["archive_sha256"]:
            raise ValueError("Speed-profile source archive mismatch")
        for driver, windows in observations.items():
            spans = sorted(
                {
                    span
                    for groups in windows.values()
                    for group in groups
                    for span in group
                }
            )
            samples = samples_for(
                native_root,
                event,
                source,
                driver,
                bindings["archive_sha256"]
                if source["provider"] == "FASTF1"
                else bindings["drivers"][str(driver)],
                min(a for a, _ in spans),
                max(b for _, b in spans),
            )
            cached = {}
            for a, b in spans:
                primary, independent = (
                    native_profile(samples, a, b),
                    scalar_profile(samples, a, b),
                )
                if primary is None or independent is None:
                    if primary is not independent:
                        raise ValueError("Independent speed-profile support mismatch")
                else:
                    compare(primary[0], independent[0], "lap distance")
                    compare(primary[1], independent[1], "distance-aligned speed")
                cached[a, b] = primary, independent
            physical_laps += len(cached)
            for i, groups in windows.items():
                a = speed_groups([[cached[span][0] for span in g] for g in groups])
                b = independent_groups(
                    [[cached[span][1] for span in g] for g in groups]
                )
                if (a is None) != (b is None):
                    raise ValueError("Independent distance alignment support mismatch")
                if b is not None:
                    compare(a, b, "distance-aligned speed groups")
                output[i] = {"groups_mps": a, "independently_checked": True}
        print(f"Audited native speed profiles for {event}", flush=True)
    if any(row is None for row in output):
        raise ValueError("Incomplete speed profile inventory")
    return seal(
        {
            "schema": "compound-native-speed-profiles-v25",
            "dataset_sha256": data["content_sha256"],
            "telemetry_sha256": telemetry["content_sha256"],
            "protocol_sha256_lf": canonical_file_sha(PROTOCOL),
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "unique_physical_laps": physical_laps,
            "fully_supported_cases": sum(
                row["groups_mps"] is not None for row in output
            ),
            "profiles": output,
        }
    )


def study(data, telemetry, profiles):
    nominations, practice, parent = [
        read_json(FOLDER / name)
        for name in (
            "compound-v21-nominations.json",
            "compound-v17-practice-trends.json",
            "compound-v24-development.json",
        )
    ]
    for doc in (data, telemetry, profiles, nominations, practice, parent):
        check_seal(doc)
    if not (
        data["content_sha256"]
        == parent["dataset_sha256"]
        == profiles["dataset_sha256"]
        == telemetry["dataset_sha256"]
        and telemetry["content_sha256"]
        == parent["telemetry_sha256"]
        == profiles["telemetry_sha256"]
        and nominations["content_sha256"] == parent["nominations_sha256"]
        and practice["content_sha256"] == parent["practice_sha256"]
        and profiles["source_sha256_lf"] == canonical_file_sha(Path(__file__))
        and profiles["protocol_sha256_lf"] == canonical_file_sha(PROTOCOL)
    ):
        raise ValueError("Speed-profile experiment parents changed")
    alloc = inventory(nominations["sources"], set(data["sources"]))
    raw = {
        event: (s["issued"], codes)
        for s in nominations["sources"]
        for event, codes in s["events"].items()
    }
    control, check, additions, independent = [], [], [], []
    for row, groups, profile in zip(
        data["cases"], telemetry["lap_summaries"], profiles["profiles"], strict=True
    ):
        vector = features(row, alloc, True)
        for compound in row["compounds"]:
            p = practice["events"][str(row["session"])][compound]
            vector.extend([p["drift_s"] or 0.0, log1p(p["drivers"])])
        control.append(vector + driving_features(groups))
        check.append(base_vector(row, raw, practice["events"]) + driving_vector(groups))
        additions.append(profile_vector(profile["groups_mps"]))
        independent.append(scalar_vector(profile["groups_mps"]))
    matrix, audit_matrix = np.asarray(control), np.asarray(check)
    baseline, baseline_audit = evaluate(data, matrix, audit_matrix)
    compare(baseline, parent["results"]["native_ridge"], "same-cohort native control")
    result, audit = evaluate(
        data,
        np.column_stack((matrix, additions)),
        np.column_stack((audit_matrix, independent)),
    )
    return seal(
        {
            "schema": "compound-native-speed-profile-study-v25",
            "dataset_sha256": data["content_sha256"],
            "profiles_sha256": profiles["content_sha256"],
            "parent_sha256": parent["content_sha256"],
            "result": result,
            "audit": audit,
            "control_audit": baseline_audit,
            "development_qualified": result["qualified"],
            "new_holdout_acquisition_allowed": result["qualified"],
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = read_json(FOLDER / "compound-v24-cohort.json")
    telemetry = read_json(FOLDER / "compound-v24-telemetry.json")
    if args.profiles:
        result = study(data, telemetry, read_json(args.profiles))
        if args.expected:
            expected = read_json(args.expected)
            check_seal(expected)
            for key in (
                "profiles_sha256",
                "result",
                "development_qualified",
                "new_holdout_acquisition_allowed",
            ):
                compare(result[key], expected[key], key)
    else:
        result = prepare(data, telemetry, args.native_root)
    write_manifest(args.output, result)
