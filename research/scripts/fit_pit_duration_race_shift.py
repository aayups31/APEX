"""Evaluate fixed between-race shifts for the R047 empirical distribution."""

import argparse
from pathlib import Path
from statistics import mean

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from fit_pit_duration_distribution import BASE, PARENT, distribution_scores

SCALES = (0.90, 1.00, 1.10)


def evaluate(calibration, events):
    """Score a frozen empirical mixture using race-level held-out observations."""
    centers = calibration["circuit_median_seconds"]
    ratios = calibration["relative_samples"]
    pooled = calibration["pooled_seconds"]
    rows = {}
    for name, event in events.items():
        circuit = event["circuit"]
        actual = [stop["lane_s"] for stop in event["stops"]]
        if not actual:
            raise ValueError(f"No eligible stops in {name}")
        samples = (
            sorted(centers[circuit] * x * s for x in ratios for s in SCALES)
            if circuit in centers
            else pooled
        )
        rows[name] = {
            "stops": len(actual),
            "fallback": circuit not in centers,
            "candidate": distribution_scores(samples, actual),
            "pooled": distribution_scores(pooled, actual),
        }
    macro = {
        arm: mean(f[arm]["crps_s"] for f in rows.values())
        for arm in ("candidate", "pooled")
    }
    coverage = sum(f["candidate"]["interval_hits"] for f in rows.values()) / sum(
        f["stops"] for f in rows.values()
    )
    checks = {
        "lower_macro_crps": macro["candidate"] < macro["pooled"],
        "central_coverage": 0.70 <= coverage <= 0.90,
        "per_race_coverage": all(
            f["candidate"]["coverage"] >= 0.50 for f in rows.values()
        ),
    }
    return {
        "folds": rows,
        "macro_crps_s": macro,
        "central_coverage": coverage,
        "checks": checks,
        "passed": all(checks.values()),
    }


def run():
    parent = read_json(PARENT)
    previous = read_json(BASE / "docs/verification/pit-duration-r047-v1.json")
    for doc in (parent, previous):
        check_seal(doc)
    return seal(
        {
            "schema": "apex-pit-duration-race-shift-r047-v2",
            "parent_sha256": previous["content_sha256"],
            "pit_cohort_sha256": parent["content_sha256"],
            "scale_multipliers": list(SCALES),
            **evaluate(previous["calibration"], parent["evaluation"]),
            "fresh_confirmation": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, run())
