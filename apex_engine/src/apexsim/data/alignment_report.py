"""P1-06 source linkage and temporal diagnostics over frozen provider archives."""
from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from apexsim import __version__
from apexsim.data.alignment import AlignmentPolicy, stream_quality, temporal_join, utc_times
from apexsim.data.fastf1_archive import SESSION_NAMES, verify_fastf1_archive
from apexsim.data.jolpica import verify_jolpica_archive
from apexsim.data.openf1_archive import verify_openf1_archive
from apexsim.provenance import file_sha256, payload_sha256, write_manifest

REPORT_VERSION = "apex-temporal-alignment-v1"
LINK_VERSION = "apex-session-link-v1"
SCHEDULE_KEYS = {"FP1": "FirstPractice", "FP2": "SecondPractice", "FP3": "ThirdPractice",
                 "Q": "Qualifying", "S": "Sprint", "SQ": "SprintQualifying", "SS": "SprintQualifying"}


def validate_link(link: dict, fast: dict, opened: dict, catalog: dict, catalog_root: Path) -> dict:
    """Check an explicit reviewed mapping; never infer identity from similar names."""
    if link.get("schema_version") != LINK_VERSION:
        raise ValueError("Unsupported session-link schema")
    for name in ("season", "round_number", "openf1_session_key", "openf1_meeting_key", "openf1_circuit_key"):
        if type(link.get(name)) is not int or link[name] <= 0:
            raise ValueError(f"Session link requires positive integer {name}")
    if not isinstance(link.get("rationale"), str) or not link["rationale"].strip():
        raise ValueError("Session link requires an explicit mapping rationale")
    code, fi, oi = link["session_code"], fast["identity"], opened["identity"]
    if code not in SESSION_NAMES or fast["query"] != {"year": link["season"], "round_number": link["round_number"], "session": code}:
        raise ValueError("FastF1 query disagrees with explicit session link")
    if fi["event_name"] != link["fastf1_event_name"] or fi["session_name"] != SESSION_NAMES[code]:
        raise ValueError("FastF1 event/session disagrees with link")
    if any(oi[field] != link[key] for field, key in (("year", "season"), ("session_key", "openf1_session_key"),
                                                  ("meeting_key", "openf1_meeting_key"), ("circuit_key", "openf1_circuit_key"))):
        raise ValueError("OpenF1 identity disagrees with link")
    if oi["session_name"] != SESSION_NAMES[code] or catalog["query"]["season"] != link["season"]:
        raise ValueError("Session type or catalog season disagrees with link")
    races = [row for page in catalog["pages"] for row in json.loads((catalog_root / page["path"]).read_bytes())["MRData"]["RaceTable"]["Races"]
             if int(row["round"]) == link["round_number"]]
    if len(races) != 1 or races[0]["Circuit"]["circuitId"] != link["jolpica_circuit_id"]:
        raise ValueError("Jolpica round/circuit disagrees with link")
    schedule = races[0] if code == "R" else races[0].get(SCHEDULE_KEYS[code], {})
    anchor = utc_times([fi["t0_date"]], naive_is_utc=True)[0]
    actual_start = pd.Timestamp(anchor.value + pd.Timedelta(fi["session_start_time_s"], unit="s").value, unit="ns", tz="UTC")
    opened_start = utc_times([oi["date_start"]])[0]
    if not (schedule.get("date") == link["session_date"] == actual_start.date().isoformat() == opened_start.date().isoformat()):
        raise ValueError("Provider session dates disagree with the link")
    return {"event_id": f"F1_{link['season']}_R{link['round_number']:02d}",
            "fastf1_t0_utc": anchor.isoformat(), "fastf1_start_utc": actual_start.isoformat(),
            "openf1_scheduled_start_utc": opened_start.isoformat(),
            "start_difference_ms": float((actual_start - opened_start).total_seconds() * 1000),
            "drivers_fastf1": sorted(fi["drivers"]), "jolpica_scheduled_session": schedule,
            "mapping_kind": "explicit_assertion_checked_against_provider_metadata"}


def _open_table(root: Path, name: str) -> pd.DataFrame:
    with (root / "tables" / f"{name}.jsonl").open(encoding="utf-8") as handle:
        return pd.DataFrame(json.loads(line) for line in handle)


def _lap_comparison(fast: pd.DataFrame, opened: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    left = fast[["DriverNumber", "LapNumber"]].rename(columns={"DriverNumber": "driver", "LapNumber": "lap"}).copy()
    right = opened[["driver_number", "lap_number"]].rename(columns={"driver_number": "driver", "lap_number": "lap"}).copy()
    for frame in (left, right):
        for column in ("driver", "lap"):
            number = pd.to_numeric(frame[column], errors="raise")
            if number.isna().any() or (number <= 0).any() or (number % 1 != 0).any():
                raise ValueError("Lap identity requires positive integral driver/lap keys")
            frame[column] = number.astype("int64")
        if frame.duplicated(["driver", "lap"]).any():
            raise ValueError("Ambiguous duplicate driver/lap identity")
    left["fastf1_start_utc"] = utc_times(fast.LapStartDate, naive_is_utc=True)
    right["openf1_start_utc"] = utc_times(opened.date_start)
    left["fastf1_duration_s"] = fast.LapTime.dt.total_seconds().to_numpy()
    right["openf1_duration_s"] = opened.lap_duration.to_numpy()
    pairs = left.merge(right, on=["driver", "lap"], how="outer", indicator=True, validate="one_to_one")
    pairs["start_openf1_minus_fastf1_ms"] = (pairs.openf1_start_utc - pairs.fastf1_start_utc).dt.total_seconds() * 1000
    pairs["duration_openf1_minus_fastf1_ms"] = (pairs.openf1_duration_s - pairs.fastf1_duration_s) * 1000
    report = {"fastf1_rows": len(left), "openf1_rows": len(right), "matched_keys": int((pairs._merge == "both").sum()),
              "fastf1_only_keys": int((pairs._merge == "left_only").sum()),
              "openf1_only_keys": int((pairs._merge == "right_only").sum())}
    for column in ("start_openf1_minus_fastf1_ms", "duration_openf1_minus_fastf1_ms"):
        values = pairs[column].dropna()
        report[column] = {"comparable_rows": len(values), "missing_pairs": int(pairs[column].isna().sum()),
                          "median": float(values.median()) if len(values) else None,
                          "absolute_max": float(values.abs().max()) if len(values) else None}
    return pairs, report


def _messages(frame: pd.DataFrame, *, fastf1: bool) -> list[dict]:
    date_column, text_column, category_column = ("Time", "Message", "Category") if fastf1 else ("date", "message", "category")
    if frame.empty:
        return []
    times = utc_times(frame[date_column], naive_is_utc=fastf1)
    return [{"row": i, "timestamp_utc": None if pd.isna(t) else t.isoformat(),
             "message": str(frame.iloc[i][text_column]), "category": str(frame.iloc[i][category_column])}
            for i, t in enumerate(times)]


def _message_comparison(left: list[dict], right: list[dict]) -> dict:
    def key(row):
        return row["timestamp_utc"], row["category"], row["message"]

    # Missing times never match; exact text/time matching is a diagnostic, not a flag-state merge.
    left_counts = Counter(key(row) for row in left if row["timestamp_utc"] is not None)
    right_counts = Counter(key(row) for row in right if row["timestamp_utc"] is not None)
    common = left_counts & right_counts

    def unmatched(rows):
        remaining = common.copy()
        result = []
        for row in rows:
            if remaining[key(row)]:
                remaining[key(row)] -= 1
            else:
                result.append(row)
        return result

    return {"match_rule": "exact timestamp/category/message multiset; no fuzzy matching",
            "fastf1_rows": len(left), "openf1_rows": len(right), "matched_records": sum(common.values()),
            "fastf1_only": unmatched(left), "openf1_only": unmatched(right)}


def build_alignment_report(fastf1: str | Path, openf1: str | Path, jolpica: str | Path,
                           link_path: str | Path, output: str | Path,
                           *, policy: AlignmentPolicy | None = None) -> dict:
    """Verify archives, audit all drivers/streams and publish a new immutable diagnostic run.

    This produces association indices and quality evidence, not filled features or
    a canonical training dataset. Nearest cross-provider joins must not feed policies.
    """
    policy = policy or AlignmentPolicy()
    roots = {"fastf1": Path(fastf1), "openf1": Path(openf1), "jolpica": Path(jolpica)}
    destination = Path(output)
    if destination.exists():
        raise FileExistsError(f"Alignment output already exists: {destination}")
    if any(destination.resolve().is_relative_to(root.resolve()) for root in roots.values()):
        raise ValueError("Alignment output must be outside source archives")
    verifiers = {"fastf1": verify_fastf1_archive, "openf1": verify_openf1_archive, "jolpica": verify_jolpica_archive}
    sources = {name: verifiers[name](root) for name, root in roots.items()}
    link = json.loads(Path(link_path).read_text(encoding="utf-8"))
    identity = validate_link(link, sources["fastf1"], sources["openf1"], sources["jolpica"], roots["jolpica"])
    frames = {name: _open_table(roots["openf1"], name) for name in ("car_data", "location", "weather", "laps", "race_control", "drivers")}
    open_drivers = {str(int(n)) for n in frames["drivers"].driver_number}
    fast_drivers = set(identity["drivers_fastf1"])
    identity["drivers_only_fastf1"] = sorted(fast_drivers - open_drivers)
    identity["drivers_only_openf1"] = sorted(open_drivers - fast_drivers)
    if fast_drivers != open_drivers:
        raise ValueError("Provider driver inventories differ; resolve explicit coverage before alignment")
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "pairs").mkdir()
    write_manifest(destination / "session_link.json", link)
    write_manifest(destination / "policy.json", asdict(policy))
    streams, joins = {}, {}

    def register(name, times, gap):
        streams[name] = stream_quality(times, gap)
        return times

    def join(name, left_name, right_name, left, right, tolerance, direction):
        pairs, stats = temporal_join(left, right, tolerance_ms=tolerance, direction=direction)
        pairs.to_parquet(destination / "pairs" / f"{name}.parquet", index=False, compression="zstd")
        joins[name] = {**stats, "left_stream": left_name, "right_stream": right_name,
                       "usage": "causal_association" if direction == "backward" else "diagnostic_only"}

    fast_root = roots["fastf1"] / "tables"
    anchor = pd.Timestamp(identity["fastf1_t0_utc"])
    fast_weather = pd.read_parquet(fast_root / "weather_data.parquet")
    fw = register("fastf1/weather", pd.DatetimeIndex(anchor + fast_weather.Time).as_unit("ns"), policy.weather_gap_ms)
    ow = register("openf1/weather", utc_times(frames["weather"].date), policy.weather_gap_ms)
    join("cross_weather", "fastf1/weather", "openf1/weather", fw, ow, policy.cross_weather_ms, "nearest")
    for driver in sorted(fast_drivers, key=int):
        times = {}
        for provider in ("fastf1", "openf1"):
            for kind, fast_kind in (("car", "car_data"), ("location", "pos_data")):
                if provider == "fastf1":
                    frame = pd.read_parquet(fast_root / fast_kind / f"{driver}.parquet")
                    dates = utc_times(frame.Date, naive_is_utc=True)
                else:
                    frame = frames["car_data" if kind == "car" else "location"]
                    dates = utc_times(frame.loc[frame.driver_number == int(driver), "date"])
                name = f"{provider}/{kind}/{driver}"
                times[provider, kind] = register(name, dates, policy.telemetry_gap_ms)
            weather = fw if provider == "fastf1" else ow
            join(f"{provider}_car_location_{driver}", f"{provider}/car/{driver}", f"{provider}/location/{driver}",
                 times[provider, "car"], times[provider, "location"], policy.car_location_ms, "backward")
            join(f"{provider}_car_weather_{driver}", f"{provider}/car/{driver}", f"{provider}/weather",
                 times[provider, "car"], weather, policy.car_weather_ms, "backward")
        for kind in ("car", "location"):
            join(f"cross_{kind}_{driver}", f"fastf1/{kind}/{driver}", f"openf1/{kind}/{driver}",
                 times["fastf1", kind], times["openf1", kind], policy.cross_telemetry_ms, "nearest")
    lap_pairs, laps = _lap_comparison(pd.read_parquet(fast_root / "laps.parquet"), frames["laps"])
    lap_pairs.to_parquet(destination / "pairs/laps.parquet", index=False, compression="zstd")
    messages = _message_comparison(_messages(pd.read_parquet(fast_root / "race_control_messages.parquet"), fastf1=True),
                                   _messages(frames["race_control"], fastf1=False))
    source_hashes = {name: source["content_sha256"] for name, source in sources.items()}
    for name, root in roots.items():
        if verifiers[name](root)["content_sha256"] != source_hashes[name]:
            raise ValueError("Source archive changed during alignment")
    report = {"schema_version": REPORT_VERSION, "maturity": "R0", "report_complete": True,
              "environment": {"python": sys.version.split()[0], "apexsim": __version__,
                              "pandas": pd.__version__, "numpy": np.__version__},
              "implementation_sha256": {name: file_sha256(Path(__file__).with_name(name))
                                        for name in ("alignment.py", "alignment_report.py")},
              "training_ready": False, "source_archives_sha256": source_hashes, "session_link": link,
              "identity": identity, "policy": asdict(policy), "streams": streams, "joins": joins,
              "laps": laps, "race_control": messages, "source_archives_unchanged": True,
              "limitations": ["Time proximity does not establish semantic agreement or provider independence.",
                              "Causal refers to recorded timestamps; publication/availability latency is unknown.",
                              "Nearest joins are retrospective diagnostics, never causal model inputs.",
                              "No clock offset fitting, interpolation, filling or canonical feature conversion."]}
    report["content_sha256"] = payload_sha256(report)
    write_manifest(destination / "report.json", report)
    manifest = {"schema_version": "apex-alignment-run-v1", "source_archives_sha256": source_hashes,
                "report_sha256": report["content_sha256"],
                "files": {p.relative_to(destination).as_posix(): {"sha256": file_sha256(p), "bytes": p.stat().st_size}
                          for p in sorted(destination.rglob("*")) if p.is_file()}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(destination / "manifest.json", manifest)
    return report
