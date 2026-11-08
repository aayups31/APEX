"""Compare every available known processed input lap against verified native archives."""

import argparse
from pathlib import Path
from statistics import mean

import numpy as np
import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from apexsim.research.recorded_alignment import native_times
from compound_driving_data import lap_summary
from diagnose_compound_decision import ROOT


def compare(data: dict, native_root: Path) -> dict:
    check_seal(data)
    examples, counts = [], {}
    for event, origin in data["origins"].items():
        if origin["year"] == 2025 or not origin["cases"]:
            continue
        year, number = origin["year"], origin["round"]
        assert_development_event(year, number, event_id=event)
        folder = (
            f"fastf1-2024-r{number}-race-20261011"
            if year == 2024
            else f"r026-fastf1-2023-r{number}-race-20261013"
        )
        archive = native_root / folder
        manifest = verify_fastf1_archive(archive)
        if manifest["content_sha256"] != origin["native_archive_sha256"]:
            raise ValueError("Native comparison archive differs from frozen source")
        links = [
            p
            for p in data["links"]
            if str(p["key"]).startswith(f"{year}-")
            and str(p["url"]).startswith(origin["base_url"])
        ]
        by_driver = {}
        seen = set()
        count = 0
        for p in links:
            identity = p["driver"], p["lap"]
            if identity in seen or "rejection" in p:
                continue
            seen.add(identity)
            driver = p["driver"]
            if driver not in by_driver:
                frame = pd.read_parquet(archive / f"tables/car_data/{driver}.parquet")
                native_times(frame)
                dates = pd.DatetimeIndex(frame.Date).as_unit("ns").asi8 / 1e9
                brake = np.array(
                    [
                        float(v) if isinstance(v, (bool, np.bool_)) else np.nan
                        for v in frame.Brake
                    ]
                )
                samples = np.column_stack(
                    (dates, frame.Speed / 3.6, frame.Throttle / 100, brake, frame.DRS)
                )
                samples[frame.Source.to_numpy() != "car", 1:] = np.nan
                by_driver[driver] = samples
            observed = lap_summary(
                by_driver[driver], p["start_s"] + 1, p["start_s"] + p["duration_s"] - 1
            )
            exported = data["lap_summaries"][p["case"]][p["group"]][p["offset"]]
            examples.append(
                {
                    "event": event,
                    "driver": driver,
                    "lap": p["lap"],
                    "native": observed,
                    "processed": exported,
                    "clock_error_s": p["clock_error_s"],
                    "duration_error_s": p["duration_error_s"],
                    "mean_difference": np.subtract(
                        exported["means"], observed["means"]
                    ).tolist(),
                }
            )
            count += 1
        counts[event] = count
    paired = [
        p
        for p in examples
        if p["native"]["coverage"] >= 0.9 and p["processed"]["coverage"] >= 0.9
    ]
    return seal(
        {
            "schema": "processed-native-comparison-v20",
            "processed_sha256": data["content_sha256"],
            "unique_laps_by_event": counts,
            "unique_laps": len(examples),
            "jointly_supported_laps": len(paired),
            "mean_absolute_channel_difference": [
                mean(abs(p["mean_difference"][j]) for p in paired) for j in range(5)
            ],
            "max_clock_error_s": max(abs(p["clock_error_s"]) for p in examples),
            "laps": examples,
            "scope": "PAIRED_COMPLETED_LAP_SUMMARIES_NOT_UNSEEN_PROVENANCE_PROOF",
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--native-root", type=Path, default=ROOT / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, compare(read_json(args.data), args.native_root))
