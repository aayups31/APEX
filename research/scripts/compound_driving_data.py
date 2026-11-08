"""Acquire and summarize native pre-forecast car observations for R041 v19."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import pandas as pd
from apexsim.data.openf1_http import DownloadPolicy, OpenF1Client
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from apexsim.research.longitudinal_data import DRS_STATES
from apexsim.research.recorded_alignment import native_times
from compound_line_proximity import archive_laps
from diagnose_compound_decision import ROOT

FOLDER = ROOT / "docs/verification"


def car_snapshot(
    folder: Path, event: str, driver: int, query: dict, client: OpenF1Client | None
) -> tuple[list, str]:
    """Publish the original HTTP body before a sealed receipt, then verify every reload."""
    receipt = folder / f"{event}-{driver}.receipt.json"
    if not receipt.exists():
        if client is None:
            raise ValueError("Missing offline car snapshot")
        body, meta = client.get("car_data", query)
        # A content-addressed immutable body makes a partial write safe to retry.
        from hashlib import sha256

        digest = sha256(body).hexdigest()
        raw_path = folder / f"{digest}.json"
        with NamedTemporaryFile(dir=folder, delete=False) as temp:
            temp.write(body)
        try:
            os.link(temp.name, raw_path)
        except FileExistsError:
            pass
        finally:
            Path(temp.name).unlink()
        write_manifest(
            receipt,
            seal(
                {
                    "query": query,
                    "response": meta,
                    "raw_file": raw_path.name,
                    "raw_sha256": digest,
                }
            ),
        )
    doc = read_json(receipt)
    check_seal(doc)
    if doc["query"] != query or doc["raw_file"] != f"{doc['raw_sha256']}.json":
        raise ValueError("Car snapshot query or raw path mismatch")
    raw_path = folder / doc["raw_file"]
    if file_sha256(raw_path) != doc["raw_sha256"]:
        raise ValueError("Car snapshot raw body changed")
    if doc["response"]["status_code"] != 200:
        raise ValueError(
            f"Historical car data unavailable: HTTP {doc['response']['status_code']}"
        )
    records = json.loads(raw_path.read_bytes())
    if not isinstance(records, list):
        raise TypeError("Invalid car snapshot response")
    return records, doc["content_sha256"]


def lap_summary(samples: np.ndarray, start: float, end: float) -> dict:
    """Integrate preceding valid sample values over measured intervals up to one second."""
    if not np.isfinite([start, end]).all() or start >= end:
        raise ValueError("Invalid driving-state lap clocks")
    selected = samples[(samples[:, 0] >= start) & (samples[:, 0] < end)]
    if len(selected) < 2:
        return {"coverage": 0.0, "means": [0.0] * 5, "samples": len(selected)}
    times, values = selected[:, 0], selected[:, 1:]
    if np.any(np.diff(times) <= 0):
        raise ValueError("Unordered or duplicate driving-state sample clock")
    speed, throttle, brake, drs = values.T
    valid = (
        np.isfinite(values).all(axis=1)
        & (speed >= 0)
        & (speed <= 120)
        & (throttle >= 0)
        & (throttle <= 1)
        & np.isin(brake, [0, 1])
        & np.isin(drs, list(DRS_STATES))
    )
    spans = np.diff(times)
    retained = valid[:-1] & valid[1:] & (spans <= 1.0)
    weights = spans[retained]
    duration = float(weights.sum())
    observed = np.column_stack(
        (
            speed,
            throttle,
            brake,
            (throttle < 0.05) & (brake == 0),
            np.isin(drs, [10, 12, 14]),
        )
    ).astype(float)
    means = (
        np.average(observed[:-1][retained], axis=0, weights=weights).tolist()
        if duration
        else [0.0] * 5
    )
    return {
        "coverage": duration / (end - start),
        "means": means,
        "samples": len(selected),
    }


def sample_matrix(records: list[dict], event: str, driver: int) -> np.ndarray:
    """Validate identity before converting the API's native controls into SI units."""
    rows = []
    for r in records:
        if (r["session_key"], r["driver_number"]) != (int(event), driver):
            raise ValueError("Car telemetry identity mismatch")
        raw = [r.get(k) for k in ("speed", "throttle", "brake", "drs")]
        values = [
            float(v) if isinstance(v, (int, float)) else float("nan") for v in raw
        ]
        speed, throttle, brake, drs = values
        brake = brake / 100 if brake in (0, 100) else float("nan")
        rows.append(
            [
                datetime.fromisoformat(r["date"]).timestamp(),
                speed / 3.6,
                throttle / 100,
                brake,
                drs,
            ]
        )
    matrix = np.asarray(rows, dtype=float).reshape(-1, 5)
    if len(matrix) and (
        not np.isfinite(matrix[:, 0]).all() or np.any(np.diff(matrix[:, 0]) <= 0)
    ):
        raise ValueError("Invalid native OpenF1 telemetry clock")
    return matrix


def prepare(
    root: Path,
    snapshots: Path,
    client: OpenF1Client | None,
    *,
    offline_partial: bool = False,
) -> dict:
    """Retain all sealed cases and record missing driving-state observations."""
    data = read_json(FOLDER / "compound-v11-development-data.json")
    check_seal(data)
    snapshots.mkdir(parents=True, exist_ok=True)
    rows = data["cases"]
    output, sources = [None] * len(rows), {}
    for event, source in data["sources"].items():
        native = archive_laps(root, event, source)
        lookup = {
            (end, driver): (lap, duration) for end, driver, lap, duration in native
        }
        if len(native) != len(lookup):
            raise ValueError("Ambiguous driving-state native lap join")
        needed = defaultdict(list)
        for i, r in enumerate(rows):
            if str(r["session"]) != event:
                continue
            groups = [
                r["current_history"][-3:],
                r["reference_history"][:3],
                r["reference_history"][-3:],
            ]
            intervals = [
                [
                    (lap["end_s"] - lookup[lap["end_s"], r["driver"]][1], lap["end_s"])
                    for lap in g
                ]
                for g in groups
            ]
            if any(end > r["forecast_at_s"] for group in intervals for _, end in group):
                raise ValueError("Future lap in driving-state inputs")
            needed[r["driver"]].append((i, intervals))
        sources[event] = {"archive_sha256": source["archive_sha256"], "drivers": {}}
        for driver, cases in needed.items():
            bounds = [
                t
                for _, groups in cases
                for group in groups
                for interval in group
                for t in interval
            ]
            start, end = min(bounds), max(bounds)
            if source["provider"] == "OPENF1":
                query = {
                    "session_key": int(event),
                    "driver_number": driver,
                    "date>=": datetime.fromtimestamp(start, timezone.utc).isoformat(),
                    "date<": datetime.fromtimestamp(end, timezone.utc).isoformat(),
                }
                if offline_partial:
                    samples = np.empty((0, 5))
                    binding = "UNAVAILABLE_HTTP_401_GLOBAL_RESTRICTION"
                else:
                    records, binding = car_snapshot(
                        snapshots, event, driver, query, client
                    )
                    samples = sample_matrix(records, event, driver)
                if len(samples) and (samples[0, 0] < start or samples[-1, 0] >= end):
                    raise ValueError("Telemetry API ignored time bounds")
            else:
                _, year, race = event.split("_")
                number = int(race[1:])
                name = (
                    f"fastf1-2024-r{number}-race-20261011"
                    if year == "2024"
                    else f"r026-fastf1-2023-r{number}-race-20261013"
                )
                table = root / name / f"tables/car_data/{driver}.parquet"
                frame = pd.read_parquet(table)
                native_times(frame)
                stamp = pd.DatetimeIndex(frame.Date).as_unit("ns").asi8 / 1e9
                brake = np.array(
                    [
                        float(v) if isinstance(v, (bool, np.bool_)) else np.nan
                        for v in frame.Brake
                    ]
                )
                samples = np.column_stack(
                    (
                        stamp,
                        frame.Speed.to_numpy(float) / 3.6,
                        frame.Throttle.to_numpy(float) / 100,
                        brake,
                        frame.DRS.to_numpy(float),
                    )
                )
                samples[frame.Source.to_numpy() != "car", 1:] = np.nan
                binding = source["archive_sha256"]
            sources[event]["drivers"][str(driver)] = binding
            for i, groups in cases:
                output[i] = [
                    [lap_summary(samples, a, b) for a, b in group] for group in groups
                ]
        print(f"Summarized {event}: {len(needed)} drivers", flush=True)
    if any(item is None for item in output):
        raise ValueError("Lost driving-state case")
    return seal(
        {
            "schema": "compound-driving-state-v19",
            "dataset_sha256": data["content_sha256"],
            "acquisition_ready": not offline_partial,
            "sources": sources,
            "lap_summaries": output,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=ROOT / ".cache")
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--offline-partial", action="store_true")
    args = parser.parse_args()
    client = OpenF1Client(DownloadPolicy()) if args.acquire else None
    try:
        write_manifest(
            args.output,
            prepare(
                args.native_root,
                args.snapshots,
                client,
                offline_partial=args.offline_partial,
            ),
        )
    finally:
        if client:
            client.close()
