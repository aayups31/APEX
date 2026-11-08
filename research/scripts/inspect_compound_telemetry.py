"""Inventory native observed car channels within the sealed R041 known prefix."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from apexsim.research.recorded_alignment import native_times

ROOT = Path(__file__).resolve().parents[2]


def inventory(native_root: Path) -> dict:
    """Verify archives and report joint throttle/brake/speed sample and time coverage."""
    data = read_json(ROOT / "docs/verification/compound-v11-development-data.json")
    check_seal(data)
    events, cases = {}, []
    for event, source in data["sources"].items():
        if source["provider"] != "FASTF1":
            continue
        _, year, label = event.split("_")
        number = int(label[1:])
        assert_development_event(int(year), number, event_id=event)
        name = (
            f"fastf1-2024-r{number}-race-20261011"
            if year == "2024"
            else f"r026-fastf1-2023-r{number}-race-20261013"
        )
        folder = native_root / name
        manifest = verify_fastf1_archive(folder)
        if manifest["content_sha256"] != source["archive_sha256"]:
            raise ValueError("Telemetry native archive differs from frozen cohort")
        laps = pd.read_parquet(folder / "tables/laps.parquet")
        lookup = {}
        for lap in laps.to_dict("records"):
            if (
                pd.isna(lap["DriverNumber"])
                or pd.isna(lap["Stint"])
                or pd.isna(lap["TyreLife"])
            ):
                continue
            key = int(lap["DriverNumber"]), int(lap["Stint"]), float(lap["TyreLife"])
            if key in lookup:
                raise ValueError("Duplicate native tyre-age association")
            lookup[key] = lap
        cars = {}
        for i, row in enumerate(data["cases"]):
            if str(row["session"]) != event:
                continue
            driver = row["driver"]
            if driver not in cars:
                car = pd.read_parquet(folder / f"tables/car_data/{driver}.parquet")
                native_times(car)
                times = pd.DatetimeIndex(car.Date).as_unit("ns").asi8 / 1e9
                speed = pd.to_numeric(car.Speed, errors="coerce").to_numpy(float)
                throttle = pd.to_numeric(car.Throttle, errors="coerce").to_numpy(float)
                brake_valid = np.array(
                    [isinstance(v, (bool, np.bool_)) for v in car.Brake]
                )
                valid = (
                    (car.Source.to_numpy() == "car")
                    & np.isfinite(speed)
                    & (speed >= 0)
                    & (speed <= 432)
                    & np.isfinite(throttle)
                    & (throttle >= 0)
                    & (throttle <= 100)
                    & brake_valid
                )
                cars[driver] = times, valid
            times, valid = cars[driver]
            windows = {}
            for kind, position, history in (
                ("current_prefix", 1, row["current_history"][-3:]),
                ("reference_prefix", 0, row["reference_history"][:3]),
                ("reference_target", 0, row["reference_history"][-3:]),
            ):
                windows[kind] = []
                for sample in history:
                    native = lookup[driver, row["stints"][position], sample["age"]]
                    start = (
                        pd.Timestamp(native["LapStartDate"])
                        .tz_localize("UTC")
                        .timestamp()
                    )
                    duration = native["LapTime"].total_seconds()
                    end = start + duration
                    if abs(sample["end_s"] - end) > 1e-6 or end > row["forecast_at_s"]:
                        raise ValueError("Future or unmatched telemetry window")
                    selected = np.flatnonzero((times >= start) & (times < end))
                    observed = valid[selected]
                    intervals = np.diff(times[selected])
                    supported = observed[:-1] & observed[1:] & (intervals <= 0.5 + 1e-9)
                    coverage = float(np.sum(intervals[supported]) / duration)
                    windows[kind].append(
                        {
                            "native_lap": int(native["LapNumber"]),
                            "rows": len(selected),
                            "valid_rows": int(observed.sum()),
                            "joint_time_coverage": coverage,
                            "duration_s": duration,
                        }
                    )
            cases.append(
                {"index": i, "event": event, "driver": driver, "windows": windows}
            )
        selected = [c for c in cases if c["event"] == event]
        current = [p for c in selected for p in c["windows"]["current_prefix"]]
        events[event] = {
            "cases": len(selected),
            "archive_sha256": manifest["content_sha256"],
            "prefix_laps": len(current),
            "minimum_prefix_coverage": min(
                (p["joint_time_coverage"] for p in current), default=None
            ),
            "cases_all_prefix_laps_90_percent": sum(
                all(
                    p["joint_time_coverage"] >= 0.9
                    for p in c["windows"]["current_prefix"]
                )
                for c in selected
            ),
        }
    return seal(
        {
            "schema": "compound-offline-telemetry-coverage",
            "dataset_sha256": data["content_sha256"],
            "channels": {
                "speed": "MEASURED_PARSED_SOURCE_KMH",
                "throttle": "MEASURED_PARSED_SOURCE_PERCENT",
                "brake": "MEASURED_BOOLEAN_PRESSURE_UNKNOWN",
            },
            "events": events,
            "cases": cases,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=ROOT / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, inventory(args.native_root))
