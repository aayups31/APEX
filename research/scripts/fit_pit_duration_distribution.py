"""R047 empirical green pit-lane duration distributions."""

import argparse
from collections import defaultdict
from math import isfinite
from pathlib import Path
from statistics import mean, median, quantiles

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from calibrate_pit_expanded import PARENT
from calibrate_pit_timing import BASE, canonical_file_sha

CALIBRATION = PARENT.with_name("pit-timing-r045-v3.json")
PROTOCOL = BASE / "research/protocols/PIT_DURATION_DISTRIBUTIONS_R047.md"


def crps(samples, observed):
    """Mean absolute prediction error minus half mean pairwise spread."""
    n = len(samples)
    spread_half = sum((2 * i - n + 1) * v for i, v in enumerate(samples)) / n**2
    return mean(abs(v - observed) for v in samples) - spread_half


def distribution_scores(samples, observations):
    lower, *_, upper = quantiles(samples, n=10, method="inclusive")
    hits = sum(lower <= v <= upper for v in observations)
    return {
        "sample_count": len(samples),
        "interval_s": [lower, upper],
        "interval_width_s": upper - lower,
        "interval_hits": hits,
        "coverage": hits / len(observations),
        "crps_s": mean(crps(samples, v) for v in observations),
    }


def evaluate(prior, expanded):
    training = {**prior["training"], **expanded["training_additions"]}
    if training.keys() & prior["evaluation"].keys():
        raise ValueError("Pit duration training overlaps held-out races")
    by_circuit = defaultdict(list)
    for event in training.values():
        by_circuit[event["circuit"]].extend(r["lane_s"] for r in event["stops"])
    pooled = sorted(v for group in by_circuit.values() for v in group)
    if len(pooled) < 2 or not all(isfinite(v) and v > 0 for v in pooled):
        raise ValueError("Expected positive finite pit-lane training durations")
    centers = {
        name: median(group) for name, group in by_circuit.items() if len(group) >= 5
    }
    ratios = sorted(
        v / centers[name]
        for name, values in by_circuit.items()
        if name in centers
        for v in values
    )
    folds = {}
    for name, event in prior["evaluation"].items():
        actual = [r["lane_s"] for r in event["stops"]]
        if not actual or not all(isfinite(v) and v > 0 for v in actual):
            raise ValueError("Expected positive finite held-out pit-lane durations")
        circuit = event["circuit"]
        samples = (
            [v * centers[circuit] for v in ratios] if circuit in centers else pooled
        )
        folds[name] = {
            "circuit": circuit,
            "stops": len(actual),
            "fallback": circuit not in centers,
            "candidate": distribution_scores(samples, actual),
            "pooled": distribution_scores(pooled, actual),
        }
    macro = {
        arm: mean(f[arm]["crps_s"] for f in folds.values())
        for arm in ("candidate", "pooled")
    }
    test_count = sum(f["stops"] for f in folds.values())
    coverage = sum(f["candidate"]["interval_hits"] for f in folds.values()) / test_count
    checks = {
        "lower_macro_crps": macro["candidate"] < macro["pooled"],
        "central_coverage": 0.70 <= coverage <= 0.90,
        "per_race_coverage": all(
            f["candidate"]["coverage"] >= 0.50 for f in folds.values()
        ),
    }
    return {
        "calibration": {
            "pooled_seconds": pooled,
            "relative_samples": ratios,
            "circuit_median_seconds": centers,
        },
        "held_out_stops": test_count,
        "folds": folds,
        "macro_crps_s": macro,
        "central_coverage": coverage,
        "checks": checks,
        "passed": all(checks.values()),
    }


def run():
    prior, expanded = read_json(PARENT), read_json(CALIBRATION)
    for item in (prior, expanded):
        check_seal(item)
    if (
        expanded["parent_sha256"] != prior["content_sha256"]
        or expanded["passed"] is not True
    ):
        raise ValueError("R047 requires the qualified R045 source inventory")
    return seal(
        {
            "schema": "apex-pit-duration-distributions-r047-v1",
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(PROTOCOL),
            "pit_calibration_sha256": expanded["content_sha256"],
            **evaluate(prior, expanded),
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, run())
