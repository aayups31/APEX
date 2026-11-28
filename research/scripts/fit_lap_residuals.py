"""R046 event-held-out next-lap pace and driver residual benchmark."""

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from functools import cache
from itertools import pairwise
from pathlib import Path
from statistics import mean, quantiles

import numpy as np
import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.data.tyre_dataset import FuelPrior, segment_native_laps
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from apexsim.research.lap_residuals import COMPOUNDS, point_pace
from calibrate_pit_expanded import PARENT
from calibrate_pit_timing import BASE, canonical_file_sha
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

PROTOCOL = BASE / "research/protocols/LAP_RESIDUALS_R046.md"


def extract(frame, event):
    segments, _ = segment_native_laps(frame, event, FuelPrior())
    rows = []
    for segment in segments:
        native = segment["rows"]
        for i in range(3, len(native)):
            prefix, target = native[i - 3 : i], native[i]
            clocks = [frame.iloc[r["native_row"]]["Time"] for r in (*prefix, target)]
            if any(pd.isna(t) for t in clocks) or any(
                a >= b for a, b in pairwise(clocks)
            ):
                continue
            past = [r["observed_s"] for r in prefix]
            last = prefix[-1]
            rows.append(
                {
                    "event": event["event_id"],
                    "driver": last["driver"],
                    "target_lap": target["lap"],
                    "forecast_clock_s": clocks[2].total_seconds(),
                    "target_clock_s": clocks[3].total_seconds(),
                    "last_s": past[-1],
                    "target_s": target["observed_s"],
                    "features": [
                        past[1] - past[0],
                        past[2] - past[1],
                        last["tyre_age"],
                        last["lap"],
                        *[float(segment["compound"] == c) for c in COMPOUNDS],
                    ],
                }
            )
    return rows


def fit(rows):
    counts = Counter(r["event"] for r in rows)
    weights = np.asarray([len(rows) / (len(counts) * counts[r["event"]]) for r in rows])
    x = np.asarray([r["features"] for r in rows])
    y = [r["target_s"] - r["last_s"] for r in rows]
    scaler = StandardScaler().fit(x, sample_weight=weights)
    regression = Ridge(alpha=10.0, solver="svd").fit(
        scaler.transform(x), y, sample_weight=weights
    )
    return {
        "center": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "coefficients": regression.coef_.tolist(),
        "intercept": float(regression.intercept_),
    }


def point(model, row):
    return point_pace(model, row["last_s"], row["features"])


def reference_errors(training):
    """Generate calibration errors on whole races absent from their point fit."""
    errors = {"ridge": [], "persistence": []}
    inventory = {}
    for race, rows in sorted(training.items()):
        inventory[race] = sorted(set(training) - {race})
        model = fit([r for event in inventory[race] for r in training[event]])
        for row in rows:
            for arm, p in (
                ("ridge", point(model, row)),
                ("persistence", row["last_s"]),
            ):
                errors[arm].append((race, row["driver"], row["target_s"] - p))
    return errors, inventory


def evaluate(training, held_out):
    if set(training) & set(held_out):
        raise ValueError("Overlapping residual calibration races")
    model = fit([r for rows in training.values() for r in rows])
    errors, crossfit = reference_errors(training)

    @cache
    def distribution(arm, driver):
        pooled = [e for _, _, e in errors[arm]]
        own = [(event, e) for event, d, e in errors[arm] if d == driver]
        supported = len(own) >= 30 and len({event for event, _ in own}) >= 2
        # Repetition constructs exactly equal weights for both empirical components.
        samples = (
            sorted(pooled * len(own) + [e for _, e in own] * len(pooled))
            if supported
            else sorted(pooled)
        )
        lower, *_, upper = quantiles(samples, n=10, method="inclusive")
        return empirical_index(samples), lower, upper, supported

    folds, details = {}, {}
    for race, rows in sorted(held_out.items()):
        forecasts = []
        for row in rows:
            if (
                not row["forecast_clock_s"] < row["target_clock_s"]
                or row["event"] != race
            ):
                raise ValueError("Unordered or wrong-race residual target")
            result = {**row, "arms": {}}
            for arm, p in (
                ("ridge", point(model, row)),
                ("persistence", row["last_s"]),
            ):
                samples, lo, hi, supported = distribution(arm, row["driver"])
                error = row["target_s"] - p
                # Absolute-error term evaluated by vectorized empirical arithmetic.
                loss = empirical_score(samples, error)
                result["arms"][arm] = {
                    "point_s": p,
                    "error_s": error,
                    "interval_s": [p + lo, p + hi],
                    "covered": lo <= error <= hi,
                    "driver_specific": supported,
                    "crps_s": loss,
                }
            forecasts.append(result)
        details[race] = forecasts
        summary = {}
        for arm in errors:
            metrics = [r["arms"][arm] for r in forecasts]
            drivers = defaultdict(list)
            for r in forecasts:
                drivers[r["driver"]].append(r["arms"][arm]["covered"])
            summary[arm] = {
                "mae_s": mean(abs(m["error_s"]) for m in metrics),
                "crps_s": mean(m["crps_s"] for m in metrics),
                "coverage": mean(m["covered"] for m in metrics),
                "hits": sum(m["covered"] for m in metrics),
                "driver_specific_cases": sum(m["driver_specific"] for m in metrics),
                "driver_coverage": {
                    d: {"cases": len(v), "coverage": mean(v)}
                    for d, v in sorted(drivers.items())
                },
            }
        folds[race] = {"cases": len(rows), **summary}
    macro = {
        arm: {k: mean(f[arm][k] for f in folds.values()) for k in ("mae_s", "crps_s")}
        for arm in errors
    }
    coverage = sum(f["ridge"]["hits"] for f in folds.values()) / sum(
        f["cases"] for f in folds.values()
    )
    checks = {
        "lower_point_mae": macro["ridge"]["mae_s"] < macro["persistence"]["mae_s"],
        "lower_crps": macro["ridge"]["crps_s"] < macro["persistence"]["crps_s"],
        "interval_coverage": 0.70 <= coverage <= 0.90,
        "race_support_and_coverage": all(
            f["cases"] >= 50 and f["ridge"]["coverage"] >= 0.60 for f in folds.values()
        ),
    }
    return {
        "point_model": model,
        "calibration_races": crossfit,
        "calibration_errors": [list(item) for item in errors["ridge"]],
        "macro": macro,
        "coverage": coverage,
        "folds": folds,
        "forecasts": details,
        "checks": checks,
        "passed": all(checks.values()),
    }


def empirical_index(samples):
    """Index a sorted empirical sample for fast forecast replay."""
    n = len(samples)
    prefix = np.r_[0.0, np.cumsum(samples)]
    spread = np.dot(2 * np.arange(n) - n + 1, samples) / n**2
    return samples, prefix, float(spread)


def empirical_score(index, error):
    samples, prefix, spread = index
    n = len(samples)
    k = bisect_right(samples, error)
    return float(((2 * k - n) * error + prefix[-1] - 2 * prefix[k]) / n - spread)


def run(root):
    parent = read_json(PARENT)
    check_seal(parent)
    splits = []
    for split in ("training", "evaluation"):
        rows = {}
        for event, info in parent[split].items():
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
            if manifest["content_sha256"] != info["source_sha256"]:
                raise ValueError("Residual archive differs from the frozen source")
            meta = {
                "season": year,
                "round_number": number,
                "event_id": event,
                "track_id": info["circuit"],
                "race_date": "",
            }
            rows[event] = extract(
                pd.read_parquet(archive / "tables/laps.parquet"), meta
            )
        splits.append(rows)
    return seal(
        {
            "schema": "apex-r046-clean-green-lap-residuals-v1",
            "parent_sha256": parent["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(PROTOCOL),
            "training_rows": {e: len(rows) for e, rows in splits[0].items()},
            **evaluate(*splits),
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
