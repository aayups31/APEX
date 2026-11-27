"""Check which crossover decisions are reachable by a shared three-lap offset."""

import argparse
from itertools import pairwise
from pathlib import Path
from statistics import median

from apexsim.provenance import write_manifest
from apexsim.research.compound_readiness import LABELS, crossing
from apexsim.research.evidence import check_seal, read_json, seal
from confirm_compound_multiseason import canonical_file_sha
from diagnose_compound_line import FOLDER

MARGIN = 0.15


def reachable(row, shape):
    """Examine every open interval and boundary of the decision function."""
    prefix = row["current_prefix_s"]
    ref = row["reference_target_s"]
    low = max(p - 2 - v for p, v in zip(prefix, shape, strict=True))
    high = min(p + 2 - v for p, v in zip(prefix, shape, strict=True))
    if low > high:
        raise ValueError("No feasible shift for lap shape")
    contrasts = (
        median(ref) - median(shape),
        median(a - b for a, b in zip(ref, shape, strict=True)),
    )
    tests = []
    points = {low, high}
    for (key, _), value in zip(LABELS, contrasts, strict=True):
        start = row[key]
        direction = int(start > MARGIN) - int(start < -MARGIN)
        boundary = value + direction * MARGIN
        tests.append((direction, boundary))
        if direction and low <= boundary <= high:
            points.add(boundary)
    locations = sorted(points)
    probes = locations + [(a + b) / 2 for a, b in pairwise(locations)]
    return sorted(
        {
            tuple(direction * (shift - threshold) > 0 for direction, threshold in tests)
            for shift in probes
        }
    )


def audit():
    data, control = [
        read_json(FOLDER / f"compound-v24-{name}.json")
        for name in ("cohort", "development")
    ]
    for doc in (data, control):
        check_seal(doc)
    if data["content_sha256"] != control["dataset_sha256"]:
        raise ValueError("Wrong common-shift cohort")
    predictions = sorted(
        control["results"]["nomination_practice_ridge"]["predictions"],
        key=lambda p: p["index"],
    )
    cases = []
    events = {
        event: {
            name: {
                "unreachable_joint": 0,
                "observed_positives": [0, 0],
                "unreachable_positives": [0, 0],
            }
            for name in ("prefix_shape", "ridge_shape")
        }
        for event in data["sources"]
    }
    for i, (row, p) in enumerate(zip(data["cases"], predictions, strict=True)):
        event = str(row["session"])
        if (i, event) != (p["index"], p["event"]):
            raise ValueError("Wrong common-shift forecast identity")
        observed = tuple(crossing(row[start], row[target]) for start, target in LABELS)
        result = {
            "prefix_shape": reachable(row, row["current_prefix_s"]),
            "ridge_shape": reachable(row, p["laps_s"]),
        }
        for name, decisions in result.items():
            counts = events[event][name]
            counts["unreachable_joint"] += observed not in decisions
            for j, positive in enumerate(observed):
                counts["observed_positives"][j] += positive
                counts["unreachable_positives"][j] += positive and not any(
                    d[j] for d in decisions
                )
        cases.append({"index": i, "event": event, "observed": observed, **result})
    return seal(
        {
            "scope": "ORACLE_REACHABILITY_OF_FIXED_LAP_SHAPES_ONLY",
            "dataset_sha256": data["content_sha256"],
            "control_sha256": control["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "cases": cases,
            "events": events,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, audit())
