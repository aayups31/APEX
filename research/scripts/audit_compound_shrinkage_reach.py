"""Bound achievable crossover recall for any per-case shrinkage of ridge laps."""

import argparse
from itertools import combinations
from pathlib import Path
from statistics import median

from apexsim.provenance import write_manifest
from apexsim.research.compound_readiness import LABELS, crossing
from apexsim.research.evidence import check_seal, read_json, seal
from confirm_compound_multiseason import canonical_file_sha
from diagnose_compound_line import FOLDER


def can_cross(start, intercepts, slopes):
    """Check every piecewise-affine median extremum on the unit interval."""
    locations = {0.0, 1.0}
    for i, j in combinations(range(3), 2):
        difference = slopes[i] - slopes[j]
        if difference:
            alpha = (intercepts[j] - intercepts[i]) / difference
            if 0.0 < alpha < 1.0:
                locations.add(alpha)
    extrema = [
        median(a + t * b for a, b in zip(intercepts, slopes, strict=True))
        for t in locations
    ]
    # Give borderline values to the oracle. This yields a conservative upper bound.
    if start > 0.15:
        return min(extrema) <= -0.15 + 1e-10
    if start < -0.15:
        return max(extrema) >= 0.15 - 1e-10
    return False


def run():
    data = read_json(FOLDER / "compound-v24-cohort.json")
    control = read_json(FOLDER / "compound-v24-development.json")
    for doc in (data, control):
        check_seal(doc)
    if data["content_sha256"] != control["dataset_sha256"]:
        raise ValueError("Wrong shrinkage endpoint cohort")
    counts = {
        e: [{"observed": 0, "reachable": 0} for _ in LABELS] for e in data["sources"]
    }
    predictions = sorted(
        control["results"]["nomination_practice_ridge"]["predictions"],
        key=lambda p: p["index"],
    )
    for i, (row, p) in enumerate(zip(data["cases"], predictions, strict=True)):
        if (i, str(row["session"])) != (p["index"], p["event"]):
            raise ValueError("Ambiguous shrinkage endpoint")
        prefix, reference = row["current_prefix_s"], row["reference_target_s"]
        slopes = [u - v for u, v in zip(prefix, p["laps_s"], strict=True)]
        for j, (initial, target) in enumerate(LABELS):
            if crossing(row[initial], row[target]):
                metric = counts[p["event"]][j]
                metric["observed"] += 1
                ref = reference if j else [median(reference)] * 3
                metric["reachable"] += can_cross(
                    row[initial],
                    [a - b for a, b in zip(ref, prefix, strict=True)],
                    slopes,
                )
    impossible = [
        e
        for e, labels in counts.items()
        if any(2 * m["reachable"] < m["observed"] for m in labels)
    ]
    return seal(
        {
            "scope": "OPTIMISTIC_PER_LABEL_RECALL_BOUND_ONLY",
            "dataset_sha256": data["content_sha256"],
            "control_sha256": control["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "events": counts,
            "impossible_recall_events": impossible,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, run())
