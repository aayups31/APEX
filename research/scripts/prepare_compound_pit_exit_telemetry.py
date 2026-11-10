"""Extract native pre-forecast car inputs for the rebuilt R041 cohort."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from apexsim.data.openf1_http import DownloadPolicy, OpenF1Client
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from compound_driving_data import car_snapshot, lap_summary, sample_matrix
from compound_line_proximity import archive_laps
from confirm_compound_crossover import timestamp
from confirm_compound_multiseason import canonical_file_sha
from prepare_compound_native_recovery import bounded_query
from prepare_compound_pit_exit import BASE, FOLDER


def covers(query, event, driver, start, end):
    """Reuse a snapshot only when its identity and full requested range agree."""
    identity = {"session_key": int(event), "driver_number": driver}
    if query == identity:
        return True
    return (
        set(query) == {*identity, "date>", "date<"}
        and all(query[key] == value for key, value in identity.items())
        and datetime.fromisoformat(query["date>"])
        < datetime.fromtimestamp(start, timezone.utc)
        and datetime.fromisoformat(query["date<"])
        >= datetime.fromtimestamp(end, timezone.utc)
    )


def windows(row):
    return (
        row["current_history"][-3:],
        row["reference_history"][:3],
        row["reference_history"][-3:],
    )


def interval_groups(row, durations):
    groups = [
        [(p["end_s"] - durations[p["end_s"], row["driver"]], p["end_s"]) for p in group]
        for group in windows(row)
    ]
    if any(end > row["forecast_at_s"] for group in groups for _, end in group):
        raise ValueError("Future lap in pit-exit telemetry inputs")
    return groups


def prepare(data, native_root, v23_cache, cache, client=None, *, plan=False):
    legacy = read_json(FOLDER / "compound-v11-development-data.json")
    previous = read_json(FOLDER / "compound-v23-native-data.json")
    for item in (data, legacy, previous):
        check_seal(item)
    if not (
        previous["acquisition_ready"]
        and data["parent_sha256"]
        == previous["dataset_sha256"]
        == legacy["content_sha256"]
        and set(data["sources"]) == set(legacy["sources"])
    ):
        raise ValueError("Pit-exit telemetry cohort changed scope")
    old_windows = {}
    for row, group in zip(legacy["cases"], previous["lap_summaries"], strict=True):
        for history, observations in zip(windows(row), group, strict=True):
            for point, summary in zip(history, observations, strict=True):
                key = str(row["session"]), row["driver"], point["end_s"]
                if old_windows.setdefault(key, summary) != summary:
                    raise ValueError("Inconsistent frozen native lap summary")
    summary = [None] * len(data["cases"])
    sources, required = {}, []
    if client:
        cache.mkdir(parents=True, exist_ok=True)
    for event, source in data["sources"].items():
        if source["archive_sha256"] != legacy["sources"][event]["archive_sha256"]:
            raise ValueError("Pit-exit telemetry archive changed")
        indices = [
            i for i, row in enumerate(data["cases"]) if str(row["session"]) == event
        ]
        drivers = {}
        sources[event] = {
            "archive_sha256": source["archive_sha256"],
            "drivers": drivers,
        }
        if source["provider"] == "FASTF1":
            if [data["cases"][i] for i in indices] != [
                row for row in legacy["cases"] if str(row["session"]) == event
            ]:
                raise ValueError("Cannot reuse FastF1 telemetry after a window change")
            sources[event] = previous["sources"][event]
            for i in indices:
                row = data["cases"][i]
                summary[i] = [
                    [old_windows[event, row["driver"], p["end_s"]] for p in group]
                    for group in windows(row)
                ]
            continue
        native = archive_laps(native_root, event, source)
        durations = {(end, driver): duration for end, driver, _, duration in native}
        if len(durations) != len(native):
            raise ValueError("Ambiguous native lap clocks")
        cases = defaultdict(dict)
        for i in indices:
            row = data["cases"][i]
            cases[row["driver"]][i] = interval_groups(row, durations)
        for driver, groups in sorted(cases.items()):
            intervals = [
                span for window in groups.values() for g in window for span in g
            ]
            start = min(a for a, _ in intervals)
            end = max(b for _, b in intervals)
            receipt = v23_cache / f"{event}-{driver}.receipt.json"
            prior = read_json(receipt) if receipt.exists() else None
            if prior:
                check_seal(prior)
                if prior["content_sha256"] != previous["sources"][event]["drivers"].get(
                    str(driver)
                ):
                    raise ValueError("Unexpected prior telemetry receipt")
            reuse = prior is not None and covers(
                prior["query"], event, driver, start, end
            )
            query = (
                prior["query"]
                if reuse
                else bounded_query(int(event), driver, start, end)
            )
            if not reuse:
                required.append(query)
            if plan:
                continue
            rows, binding = car_snapshot(
                v23_cache if reuse else cache,
                event,
                driver,
                query,
                None if reuse else client,
            )
            samples = sample_matrix(rows, event, driver)
            if (
                "date>" in query
                and len(samples)
                and (
                    samples[0, 0] < timestamp(query["date>"]) - 0.001002
                    or samples[-1, 0] > timestamp(query["date<"]) + 0.001002
                )
            ):
                raise ValueError("Pit-exit car response ignored query bounds")
            drivers[str(driver)] = {"sha256": binding, "reused_v23": reuse}
            for i, window in groups.items():
                summary[i] = [
                    [lap_summary(samples, a, b) for a, b in g] for g in window
                ]
                for group, observations in zip(window, summary[i], strict=True):
                    for (_, clock), obs in zip(group, observations, strict=True):
                        prior_summary = old_windows.get((event, driver, clock))
                        if prior_summary is not None and obs != prior_summary:
                            raise ValueError(
                                "Replayed native lap summary disagrees with v23"
                            )
        print(f"Checked telemetry bounds for {event}: {len(cases)} drivers", flush=True)
    if plan:
        return seal(
            {"dataset_sha256": data["content_sha256"], "additional_queries": required}
        )
    if any(item is None for item in summary):
        raise ValueError("Missing pit-exit telemetry case")
    return seal(
        {
            "schema": "compound-pit-exit-telemetry-v24",
            "dataset_sha256": data["content_sha256"],
            "v23_sha256": previous["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "sources": sources,
            "additional_queries": required,
            "lap_summaries": summary,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument(
        "--v23-cache", type=Path, default=BASE / ".cache/r041-v23-native-car"
    )
    parser.add_argument(
        "--cache", type=Path, default=BASE / ".cache/r041-v24-native-car"
    )
    parser.add_argument("--output", type=Path, required=True)
    options = parser.add_mutually_exclusive_group()
    options.add_argument("--plan", action="store_true")
    options.add_argument("--acquire", action="store_true")
    args = parser.parse_args()
    client = OpenF1Client(DownloadPolicy()) if args.acquire else None
    try:
        result = prepare(
            read_json(args.data),
            args.native_root,
            args.v23_cache,
            args.cache,
            client,
            plan=args.plan,
        )
        write_manifest(args.output, result)
    finally:
        if client:
            client.close()
