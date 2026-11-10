"""Diagnose R041 decisions that are stable across the registered fuel range."""

import argparse
from collections import Counter
from itertools import combinations, pairwise
from pathlib import Path

from apexsim.provenance import write_manifest
from apexsim.research.compound_readiness import LABELS, crossing
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_fuel_sensitivity import COEFFICIENTS, reconstruct
from compound_line_proximity import archive_laps
from confirm_compound_multiseason import canonical_file_sha
from diagnose_compound_pit_exit import BASE, FOLDER


def mass(lap):
    return max(0.0, 105.0 - 1.4 * (lap - 1))


def critical_coefficients(groups):
    """Split the range at pace-order swaps and exact crossover thresholds."""
    low, _, high = COEFFICIENTS
    knots = {low, high}
    for group in groups:
        for (lap_a, time_a, _), (lap_b, time_b, _) in combinations(group, 2):
            diff = mass(lap_a) - mass(lap_b)
            if diff:
                value = (time_a - time_b) / diff
                if low < value < high:
                    knots.add(value)
    order_regions = sorted(knots)
    for a, b in pairwise(order_regions):
        left, right = reconstruct(groups, a), reconstruct(groups, b)
        for axis in ("prefix_s", "target_s"):
            for p, q in zip(left[axis], right[axis], strict=True):
                for threshold in (-0.15, 0.15):
                    if min(p, q) < threshold < max(p, q):
                        knots.add(a + (b - a) * (threshold - p) / (q - p))
    ordered = sorted(knots)
    return sorted({*ordered, *((a + b) / 2 for a, b in pairwise(ordered))})


def stable_labels(groups):
    """Check interiors and one-sided endpoints of every affine region."""
    values = [reconstruct(groups, c) for c in critical_coefficients(groups)]

    # Reconstructed seconds can round by a few ulps at an exact threshold.
    # Snap that arithmetic back to the registered strict margin.
    def snap(value):
        if abs(abs(value) - 0.15) <= 1e-11:
            return 0.15 if value > 0 else -0.15
        return value

    outcomes = [
        {crossing(snap(v["prefix_s"][j]), snap(v["target_s"][j])) for v in values}
        for j in range(2)
    ]
    return [len(options) == 1 for options in outcomes]


def decision_report(entries, forecasts):
    counts = {}
    for tag, stable in (("fuel_stable", True), ("fuel_sensitive", False)):
        selected = [
            (p, record, index)
            for p, record in zip(forecasts, entries, strict=True)
            for index, value in enumerate(record["stable"])
            if value == stable
        ]
        tallies = [Counter(), Counter()]
        races = set()
        for forecast, record, j in selected:
            observed = record["observed"][j]
            called = forecast["crossings"][j]
            tallies[j][f"{int(observed)}->{int(called)}"] += 1
            if observed != called:
                races.add(forecast["event"])
        counts[tag] = {
            "label_confusion": list(map(dict, tallies)),
            "races_with_errors": sorted(races),
        }
    return counts


def audit(data, result, root):
    for item in (data, result):
        check_seal(item)
    if result["dataset_sha256"] != data["content_sha256"]:
        raise ValueError("Residual audit received another cohort")
    records = [None] * len(data["cases"])
    for event, source in data["sources"].items():
        native = archive_laps(root, event, source)
        by_clock = {
            (end, driver): (lap, elapsed) for end, driver, lap, elapsed in native
        }
        by_lap = {(driver, lap): (end, elapsed) for end, driver, lap, elapsed in native}
        if len(by_clock) != len(native) or len(by_lap) != len(native):
            raise ValueError("Residual audit has ambiguous native lap identities")
        for i, row in enumerate(data["cases"]):
            if str(row["session"]) != event:
                continue
            driver = row["driver"]
            groups = [
                [(*by_clock[p["end_s"], driver], p["pace_s"]) for p in group]
                for group in (
                    row["reference_history"][:3],
                    row["current_history"][-3:],
                    row["reference_history"][-3:],
                )
            ]
            prefix_lap = groups[1][-1][0]
            target = []
            for age, pace in zip(
                row["ages"][-3:], row["current_target_s"], strict=True
            ):
                lap = prefix_lap + age - row["ages"][2]
                end, duration = by_lap[driver, lap]
                if end <= row["forecast_at_s"]:
                    raise ValueError("Residual audit target precedes forecast")
                target.append((lap, duration, pace))
            groups.append(target)
            observed = reconstruct(groups, COEFFICIENTS[1])
            for j, (start, end) in enumerate(LABELS):
                if (
                    abs(observed["prefix_s"][j] - row[start]) > 1e-10
                    or abs(observed["target_s"][j] - row[end]) > 1e-10
                ):
                    raise ValueError("Residual audit changed a registered contrast")
            records[i] = {
                "index": i,
                "event": event,
                "stable": stable_labels(groups),
                "observed": observed["observed"],
            }
    if any(record is None for record in records):
        raise ValueError("Incomplete residual audit cohort")
    return seal(
        {
            "schema": "compound-pit-exit-residual-audit-v24",
            "scope": "DIAGNOSTIC_ONLY_REGISTERED_FORECAST_AND_GATE_PRESERVED",
            "dataset_sha256": data["content_sha256"],
            "result_sha256": result["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "fuel_range_s_per_kg": [COEFFICIENTS[0], COEFFICIENTS[-1]],
            "sensitive_cases": sum(not all(record["stable"]) for record in records),
            "cases": records,
            "decisions": {
                name: decision_report(
                    records, sorted(model["predictions"], key=lambda row: row["index"])
                )
                for name, model in result["results"].items()
            },
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = read_json(FOLDER / "compound-v24-cohort.json")
    result = read_json(FOLDER / "compound-v24-development.json")
    write_manifest(args.output, audit(data, result, args.native_root))
