"""Recover complete native car streams with supported driver-only API queries."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from apexsim.data.openf1_http import DownloadPolicy, OpenF1Client
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from compound_driving_data import car_snapshot, lap_summary, sample_matrix
from compound_line_proximity import archive_laps
from diagnose_compound_decision import ROOT


def bounded_query(session: int, driver: int, start: float, end: float) -> dict:
    """Use operator keys with the equals delimiter supplied by requests."""
    return {
        "session_key": session,
        "driver_number": driver,
        "date>": datetime.fromtimestamp(start - 1e-6, timezone.utc).isoformat(),
        "date<": datetime.fromtimestamp(end, timezone.utc).isoformat(),
    }


def prepare(root: Path, cache: Path, client: OpenF1Client | None) -> dict:
    folder = ROOT / "docs/verification"
    data = read_json(folder / "compound-v11-development-data.json")
    previous = read_json(folder / "compound-v19-driving-data.json")
    for doc in (data, previous):
        check_seal(doc)
    if previous["dataset_sha256"] != data["content_sha256"]:
        raise ValueError("Wrong native FastF1 summary parent")
    cache.mkdir(parents=True, exist_ok=True)
    summaries = [None] * len(data["cases"])
    sources = {}
    for event, source in data["sources"].items():
        indices = [
            i for i, row in enumerate(data["cases"]) if str(row["session"]) == event
        ]
        # This helper checks benchmark guards, native identity and immutable archive hashes.
        native = archive_laps(root, event, source)
        lookup = {(end, driver): duration for end, driver, _, duration in native}
        if len(lookup) != len(native):
            raise ValueError("Ambiguous native recovery lap clock")
        sources[event] = {"archive_sha256": source["archive_sha256"], "drivers": {}}
        if source["provider"] == "FASTF1":
            for i in indices:
                summaries[i] = previous["lap_summaries"][i]
            continue
        for driver in sorted({data["cases"][i]["driver"] for i in indices}):
            intervals_by_case = {}
            for i in indices:
                row = data["cases"][i]
                if row["driver"] != driver:
                    continue
                groups = (
                    row["current_history"][-3:],
                    row["reference_history"][:3],
                    row["reference_history"][-3:],
                )
                intervals = [
                    [
                        (p["end_s"] - lookup[p["end_s"], driver], p["end_s"])
                        for p in group
                    ]
                    for group in groups
                ]
                if any(
                    end > row["forecast_at_s"]
                    for group in intervals
                    for _, end in group
                ):
                    raise ValueError("Future observation in native recovery")
                intervals_by_case[i] = intervals
            start = min(
                a
                for groups in intervals_by_case.values()
                for group in groups
                for a, _ in group
            )
            end = max(
                b
                for groups in intervals_by_case.values()
                for group in groups
                for _, b in group
            )
            query = bounded_query(int(event), driver, start, end)
            receipt = cache / f"{event}-{driver}.receipt.json"
            broad = {"session_key": int(event), "driver_number": driver}
            if receipt.exists() and read_json(receipt)["query"] == broad:
                query = broad
            rows, binding = car_snapshot(cache, event, driver, query, client)
            samples = sample_matrix(rows, event, driver)
            if (
                query != broad
                and len(samples)
                and (samples[0, 0] < start - 2e-6 or samples[-1, 0] >= end)
            ):
                raise ValueError("Native telemetry response ignored query bounds")
            sources[event]["drivers"][str(driver)] = binding
            for i, intervals in intervals_by_case.items():
                summaries[i] = [
                    [lap_summary(samples, start, end) for start, end in group]
                    for group in intervals
                ]
        print(f"Recovered native {event}", flush=True)
    if any(s is None for s in summaries):
        raise ValueError("Missing native recovery case")
    return seal(
        {
            "schema": "compound-native-recovery-v23",
            "dataset_sha256": data["content_sha256"],
            "fastf1_parent_sha256": previous["content_sha256"],
            "lap_summaries": summaries,
            "sources": sources,
            "acquisition_ready": True,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=ROOT / ".cache")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--acquire", action="store_true")
    args = parser.parse_args()
    client = OpenF1Client(DownloadPolicy()) if args.acquire else None
    try:
        write_manifest(args.output, prepare(args.native_root, args.cache, client))
    finally:
        if client:
            client.close()
