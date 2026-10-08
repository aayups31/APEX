"""P1-07: source-backed public evidence; no dense features or silent imputation."""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from apexsim import __version__
from apexsim.data.alignment import utc_times
from apexsim.data.alignment_report import validate_link
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.data.jolpica import verify_jolpica_archive
from apexsim.data.manifest import SourceManifest, SourceRequest, load_source_manifest
from apexsim.data.openf1_archive import verify_openf1_archive
from apexsim.data.tables import COLUMNS, COMPOUNDS, TABLE_VERSION, make_table, read_dataset, write_dataset
from apexsim.provenance import file_sha256, payload_sha256, write_manifest

MAPPING_VERSION = "apex-observed-public-fields-v1"
RUN_VERSION = "apex-observed-run-v1"


def present(value: Any) -> Any:
    """Map only source null/NaN/NaT/empty text to an explicit unknown."""
    return None if value is None or pd.isna(value) or (isinstance(value, str) and not value.strip()) else value


def number(value: Any, *, integer: bool = False) -> int | float | None:
    value = present(value)
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("Boolean supplied for numeric source field")
    numeric = float(value)
    if not math.isfinite(numeric) or (integer and numeric % 1):
        raise ValueError("Nonfinite or nonintegral numeric source field")
    return int(numeric) if integer else numeric


def boolean(value: Any) -> bool | None:
    value = present(value)
    if value is None:
        return None
    if value not in (True, False, 0, 1):
        raise ValueError("Source boolean must be boolean or 0/1")
    return bool(value)


def driver_id(value: Any) -> str:
    """Require a real positive driver number; never stringify a missing identity."""
    result = number(value, integer=True)
    if result is None or result <= 0:
        raise ValueError("Source driver identity requires a positive integral number")
    return str(result)


def timestamp(value: Any, *, fast: bool = False) -> pd.Timestamp | None:
    value = present(value)
    if value is None:
        return None
    result = utc_times([value], naive_is_utc=fast)[0]
    if result.nanosecond:
        raise ValueError("Public table timestamps require exact microsecond precision")
    return result


class Mapper:
    """Collect explicit field labels, source-row references and rejected conversions."""

    def __init__(self, provider: str, digest: str, session_id: str, start: pd.Timestamp) -> None:
        self.provider, self.digest, self.session_id, self.start = provider, digest, session_id, start
        self.rows = {name: [] for name in COLUMNS}
        self.lineage = {name: [] for name in COLUMNS}
        self.issues = []

    def issue(self, source: str, row: int, field: str, reason: str) -> None:
        self.issues.append({"native_table": source, "row": row, "field": field, "reason": reason})

    def add(self, table: str, values: dict, refs: dict, reconstructed=()) -> None:
        data = {col.name: None for col in COLUMNS[table]}
        data.update(values)
        data["session_id"] = self.session_id
        labels = {k: "UNKNOWN" if v is None else "RECONSTRUCTED" if k in reconstructed or k == "session_id"
                  else "MEASURED" for k, v in data.items()}
        self.rows[table].append({**data, "source": self.provider, "source_manifest_sha256": self.digest,
                                 "truth_labels": labels})
        self.lineage[table].append(refs)

    def compound(self, value: Any, source: str, row: int) -> str | None:
        value = present(value)
        if value is not None and value not in COMPOUNDS:
            self.issue(source, row, "compound", "unsupported_source_compound; retained in native archive")
            return None
        return value

    def relative(self, date: pd.Timestamp | None, source: str, row: int, field: str) -> float | None:
        if date is None:
            return None
        seconds = (date.value - self.start.value) / 1e9
        if seconds < 0:
            self.issue(source, row, field, "before_declared_session_start; cannot represent in v1")
            return None
        return seconds

    def duration(self, value: Any, source: str, row: int, field: str, *, fast: bool) -> float | None:
        value = present(value)
        seconds = None if value is None else value.total_seconds() if fast else number(value)
        if seconds is not None and seconds <= 0:
            self.issue(source, row, field, "nonpositive_source_duration; retained in native archive")
            return None
        return seconds


def _absolute(anchor: pd.Timestamp, delta: Any) -> pd.Timestamp | None:
    return None if present(delta) is None else timestamp(pd.Timestamp(anchor.value + delta.value, unit="ns", tz="UTC"))


def map_fastf1(mapper: Mapper, frames: dict[str, pd.DataFrame], anchor: pd.Timestamp) -> None:
    """Map FastF1 native fields; all source-relative pit/lap times share one origin."""
    groups = defaultdict(list)
    for i, row in enumerate(frames["laps"].to_dict("records")):
        driver, lap = driver_id(row["DriverNumber"]), number(row["LapNumber"], integer=True)
        stint = number(row.get("Stint"), integer=True)
        values = {"driver_id": driver, "lap_number": lap, "stint_id": stint,
                  "compound": mapper.compound(row.get("Compound"), "laps", i),
                  "tyre_age_laps": number(row.get("TyreLife")),
                  "is_accurate": boolean(row.get("IsAccurate")), "track_status": present(row.get("TrackStatus")),
                  "start_time_s": mapper.relative(timestamp(row.get("LapStartDate"), fast=True), "laps", i, "start_time_s")}
        for target, source in (("lap_time_s", "LapTime"), ("sector1_time_s", "Sector1Time"),
                               ("sector2_time_s", "Sector2Time"), ("sector3_time_s", "Sector3Time")):
            values[target] = mapper.duration(row.get(source), "laps", i, target, fast=True)
        for target, source in (("pit_in_time_s", "PitInTime"), ("pit_out_time_s", "PitOutTime")):
            values[target] = mapper.relative(_absolute(anchor, row.get(source)), "laps", i, target)
        mapper.add("laps", values, {"laps": [i]}, reconstructed=tuple(k for k in values if k.endswith("_s")))
        if stint is not None:
            groups[driver, stint].append((i, values))
    for (driver, stint), rows in sorted(groups.items()):
        compounds = {r["compound"] for _, r in rows if r["compound"] is not None}
        if len(compounds) > 1:
            raise ValueError("FastF1 compound conflict within one driver/stint")
        # A missing compound on some laps does not invent that lap's compound.
        mapper.add("stints", {"driver_id": driver, "stint_id": stint,
                              "start_lap": min(r["lap_number"] for _, r in rows),
                              "end_lap": max(r["lap_number"] for _, r in rows),
                              "compound": next(iter(compounds)) if compounds else None,
                              "tyre_age_at_start_laps": None}, {"laps": [i for i, _ in rows]},
                   reconstructed=("start_lap", "end_lap", "compound"))
    _weather(mapper, frames["weather_data"].to_dict("records"), fast=True, anchor=anchor)
    _messages(mapper, frames["race_control_messages"].to_dict("records"), fast=True)


def map_openf1(mapper: Mapper, frames: dict[str, list[dict]]) -> None:
    """Keep conflicting stint boundaries explicit; never infer pit entry/exit from dates."""
    stints, excluded = [], {}
    for i, row in enumerate(frames["stints"]):
        values = {"driver_id": driver_id(row["driver_number"]),
                  "stint_id": number(row["stint_number"], integer=True),
                  "start_lap": number(row["lap_start"], integer=True), "end_lap": number(row.get("lap_end"), integer=True),
                  "compound": mapper.compound(row.get("compound"), "stints", i),
                  "tyre_age_at_start_laps": number(row.get("tyre_age_at_start"))}
        if values["start_lap"] is None or values["end_lap"] is None or values["end_lap"] < values["start_lap"]:
            excluded[i] = "unbounded_or_invalid_source_stint; quarantined"
        stints.append(values)
    keys = [(s["driver_id"], s["stint_id"]) for s in stints]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate OpenF1 driver/stint key")
    valid = [i for i in range(len(stints)) if i not in excluded]
    for n, i in enumerate(valid):
        for j in valid[n + 1:]:
            a, b = stints[i], stints[j]
            if a["driver_id"] == b["driver_id"] and max(a["start_lap"], b["start_lap"]) <= min(a["end_lap"], b["end_lap"]):
                excluded[i] = excluded[j] = "incompatible_inclusive_range; quarantined with native row preserved"
    for i, values in enumerate(stints):
        if i in excluded:
            mapper.issue("stints", i, "lap_range", excluded[i])
        else:
            mapper.add("stints", values, {"stints": [i]})
    for i, row in enumerate(frames["laps"]):
        driver, lap = driver_id(row["driver_number"]), number(row["lap_number"], integer=True)
        candidates = [j for j, s in enumerate(stints) if s["driver_id"] == driver and s["start_lap"] is not None
                      and s["end_lap"] is not None and s["start_lap"] <= lap <= s["end_lap"]]
        selected = candidates[0] if len(candidates) == 1 else None
        if len(candidates) != 1:
            mapper.issue("laps", i, "compound", "ambiguous_stint_range" if candidates else "no_stint_range")
        values = {"driver_id": driver, "lap_number": lap,
                  "stint_id": stints[selected]["stint_id"] if selected is not None and selected not in excluded else None,
                  "compound": stints[selected]["compound"] if selected is not None else None,
                  "start_time_s": mapper.relative(timestamp(row.get("date_start")), "laps", i, "start_time_s")}
        for target, source in (("lap_time_s", "lap_duration"), ("sector1_time_s", "duration_sector_1"),
                               ("sector2_time_s", "duration_sector_2"), ("sector3_time_s", "duration_sector_3")):
            values[target] = mapper.duration(row.get(source), "laps", i, target, fast=False)
        mapper.add("laps", values, {"laps": [i], "stint_candidates": candidates},
                   reconstructed=("start_time_s", "compound", "stint_id"))
    _weather(mapper, frames["weather"], fast=False)
    _messages(mapper, frames["race_control"], fast=False)


def _weather(mapper: Mapper, rows: list[dict], *, fast: bool, anchor=None) -> None:
    names = {"air_temp_c": ("AirTemp", "air_temperature"), "track_temp_c": ("TrackTemp", "track_temperature"),
             "humidity_pct": ("Humidity", "humidity"), "wind_speed_mps": ("WindSpeed", "wind_speed"),
             "wind_direction_deg": ("WindDirection", "wind_direction"), "pressure_pa": ("Pressure", "pressure")}
    for i, row in enumerate(rows):
        values = {key: number(row.get(source[0 if fast else 1])) for key, source in names.items()}
        # Both providers report hPa/mbar; the frozen public contract uses Pa.
        if values["pressure_pa"] is not None:
            values["pressure_pa"] *= 100.0
        values["rainfall"] = boolean(row.get("Rainfall" if fast else "rainfall"))
        values["timestamp_utc"] = _absolute(anchor, row.get("Time")) if fast else timestamp(row.get("date"))
        mapper.add("weather", values, {"weather_data" if fast else "weather": [i]},
                   reconstructed=("pressure_pa", "timestamp_utc", "rainfall"))


def _messages(mapper: Mapper, rows: list[dict], *, fast: bool) -> None:
    names = {"category": ("Category", "category"), "flag": ("Flag", "flag"), "scope": ("Scope", "scope"),
             "message": ("Message", "message"), "driver_id": ("RacingNumber", "driver_number"),
             "lap_number": ("Lap", "lap_number"), "sector": ("Sector", "sector")}
    for i, row in enumerate(rows):
        values = {key: present(row.get(source[0 if fast else 1])) for key, source in names.items()}
        if values["driver_id"] is not None:
            values["driver_id"] = driver_id(values["driver_id"])
        values["lap_number"] = number(values["lap_number"], integer=True)
        if values["sector"] is not None:
            mapper.issue("race_control_messages" if fast else "race_control", i, "sector",
                         "source_sector_namespace_not_canonical_timing_sector; native value preserved")
        # Native race-control sectors include mini/marshal sectors, not lap timing sectors 1-3.
        values["sector"] = None
        values.update(message_id=f"native-{i:06d}", timestamp_utc=timestamp(row.get("Time" if fast else "date"), fast=fast))
        mapper.add("race_control", values, {"race_control_messages" if fast else "race_control": [i]},
                   reconstructed=("message_id", "timestamp_utc"))


def build_observed_tables(fastf1: str | Path, openf1: str | Path, jolpica: str | Path,
                          link_path: str | Path, output: str | Path) -> dict:
    """Create immutable provider-separated public tables and a conversion audit offline.

    Source archives are verified twice. No clocks are fitted, no missing values are
    imputed, and no cross-provider field substitution or training promotion occurs.
    """
    roots = {"fastf1": Path(fastf1).resolve(), "openf1": Path(openf1).resolve(), "jolpica": Path(jolpica).resolve()}
    destination = Path(output)
    if destination.exists():
        raise FileExistsError(f"Observed output already exists: {destination}")
    if any(destination.resolve().is_relative_to(root) for root in roots.values()):
        raise ValueError("Observed output must be outside source archives")
    verifiers = {"fastf1": verify_fastf1_archive, "openf1": verify_openf1_archive, "jolpica": verify_jolpica_archive}
    archives = {name: verifiers[name](root) for name, root in roots.items()}
    link = json.loads(Path(link_path).read_text(encoding="utf-8"))
    identity = validate_link(link, archives["fastf1"], archives["openf1"], archives["jolpica"], roots["jolpica"])
    opened_drivers = {driver_id(json.loads(line)["driver_number"])
                      for line in (roots["openf1"] / "tables/drivers.jsonl").read_text(encoding="utf-8").splitlines()}
    if set(identity["drivers_fastf1"]) != opened_drivers:
        raise ValueError("Provider driver inventories differ; resolve coverage before conversion")
    hashes = {name: a["content_sha256"] for name, a in archives.items()}
    code_hash = file_sha256(Path(__file__))
    destination.mkdir(parents=True, exist_ok=False)
    write_manifest(destination / "session_link.json", link)
    providers = {}
    for provider in ("fastf1", "openf1"):
        native_names = ("laps", "weather_data", "race_control_messages") if provider == "fastf1" else ("laps", "stints", "weather", "race_control", "pit", "drivers")
        suffix = "parquet" if provider == "fastf1" else "jsonl"
        paths = {n: roots[provider] / "tables" / f"{n}.{suffix}" for n in native_names}
        native_source = archives[provider]["source_manifest"]
        source = SourceManifest(provider, {"mapping_version": MAPPING_VERSION, "archive_sha256": hashes[provider],
                                          "source_archives_sha256": hashes, "session_link": link, "implementation_sha256": code_hash},
                                native_source["terms_url"], license_id=native_source.get("license_id"),
                                canonical_schema_version=TABLE_VERSION,
                                requests=[SourceRequest(**r) for r in native_source["requests"]],
                                notes=["Derived from frozen provider values, which may include upstream reconstructions.",
                                       "No imputation. Public evidence is not approved dense model input."])
        source.add_file(roots[provider] / "manifest.json", role="verified_archive_manifest")
        for path in paths.values():
            source.add_file(path, role="native_mapping_input")
        source_path = destination / f"{provider}.source.json"
        source.save(source_path)
        start = timestamp(identity["fastf1_start_utc" if provider == "fastf1" else "openf1_scheduled_start_utc"])
        mapper = Mapper(provider, source.to_dict()["content_sha256"], f"{identity['event_id']}_{link['session_code']}_{provider}", start)
        mapper.add("sessions", {"event_id": identity["event_id"], "season": link["season"], "round": link["round_number"],
                                "event": link["fastf1_event_name"], "session_type": link["session_code"], "start_utc": start,
                                "track_id": link["jolpica_circuit_id"], "source_session_id": archives[provider]["identity"].get("api_path")
                                if provider == "fastf1" else str(link["openf1_session_key"])},
                   {"identity": "verified archive metadata and explicit link"},
                   reconstructed=("event_id", "round", "event", "session_type", "track_id", "start_utc"))
        if provider == "fastf1":
            frames = {n: pd.read_parquet(path) for n, path in paths.items()}
            map_fastf1(mapper, frames, timestamp(identity["fastf1_t0_utc"]))
        else:
            frames = {n: [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] for n, path in paths.items()}
            map_openf1(mapper, frames)
        if {r["driver_id"] for r in mapper.rows["laps"]} - opened_drivers:
            raise ValueError("Lap driver identity is outside the linked session inventory")
        tables = {name: make_table(name, rows) for name, rows in mapper.rows.items()}
        bundle = write_dataset(destination / provider, tables, [source_path])
        write_manifest(destination / f"{provider}.lineage.json", mapper.lineage)
        providers[provider] = {"dataset_sha256": bundle["content_sha256"], "source_manifest_sha256": source.to_dict()["content_sha256"],
                               "table_rows": {n: t.num_rows for n, t in tables.items()},
                               "native_table_rows": {n: len(rows) for n, rows in frames.items()},
                               "null_counts": {n: {f: t[f].null_count for f in t.column_names} for n, t in tables.items()},
                               "issues": mapper.issues,
                               "unmapped_pit_records": len(frames["pit"]) if provider == "openf1" else 0}
    for name, root in roots.items():
        if verifiers[name](root)["content_sha256"] != hashes[name]:
            raise ValueError("Source archive changed during observed-table conversion")
    report = {"schema_version": MAPPING_VERSION, "maturity": "R0", "report_complete": True, "training_ready": False,
              "source_archives_sha256": hashes, "source_archives_unchanged": True, "implementation_sha256": code_hash,
              "environment": {"python": sys.version.split()[0], "pandas": pd.__version__, "apexsim": __version__},
              "identity": identity, "providers": providers,
              "limitations": ["Provider lap-start definitions differ; no cross-provider substitution or clock correction.",
                              "OpenF1 pit dates/durations do not establish separate canonical entry/exit timestamps here.",
                              "FastF1 stint-start tyre age and OpenF1 per-lap tyre age remain unknown.",
                              "Overlapping OpenF1 stint rows are quarantined; ambiguous lap compounds remain unknown.",
                              "No telemetry pit-occupancy flag, weather resampling, grip or safety-car proxy is invented.",
                              "Native race-control sector indices are not mapped to canonical timing sectors 1-3.",
                              "Retrospective evidence only; source availability times and calibrated feature semantics remain unverified."]}
    report["content_sha256"] = payload_sha256(report)
    write_manifest(destination / "report.json", report)
    manifest = {"schema_version": RUN_VERSION, "report_sha256": report["content_sha256"],
                "files": {p.relative_to(destination).as_posix(): {"sha256": file_sha256(p), "bytes": p.stat().st_size}
                          for p in sorted(destination.rglob("*")) if p.is_file()}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(destination / "manifest.json", manifest)
    return report


def verify_observed_tables(output: str | Path) -> dict:
    """Verify the entire portable run, including lineage and both provider bundles.

    Native files are not required for readback; the completion report records their
    checked hashes. This verifies recorded integrity and consistency, not authenticity.
    """
    root = Path(output)

    def sealed(path: Path, schema: str) -> dict:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema_version") != schema or value.get("content_sha256") != payload_sha256(
            {k: v for k, v in value.items() if k != "content_sha256"}
        ):
            raise ValueError(f"Observed artifact schema/content hash mismatch: {path.name}")
        return value

    manifest = sealed(root / "manifest.json", RUN_VERSION)
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != root / "manifest.json"}
    if actual != set(manifest["files"]):
        raise ValueError("Observed run file inventory mismatch")
    for name, record in manifest["files"].items():
        if "\\" in name or ":" in name or ".." in Path(name).parts or Path(name).is_absolute():
            raise ValueError("Observed artifact path escapes its root")
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Observed artifact path escapes its root")
        if path.stat().st_size != record["bytes"] or file_sha256(path) != record["sha256"]:
            raise ValueError(f"Observed artifact hash mismatch: {name}")
    report = sealed(root / "report.json", MAPPING_VERSION)
    if (manifest["report_sha256"] != report["content_sha256"] or report["report_complete"] is not True
            or report["training_ready"] is not False or report["maturity"] != "R0"
            or report["source_archives_unchanged"] is not True):
        raise ValueError("Observed report completion mismatch")
    link = json.loads((root / "session_link.json").read_text(encoding="utf-8"))
    for provider in ("fastf1", "openf1"):
        tables, bundle = read_dataset(root / provider)
        stats = report["providers"][provider]
        source = load_source_manifest(root / f"{provider}.source.json", verify_files=False)
        if (bundle["content_sha256"] != stats["dataset_sha256"] or source["content_sha256"] != stats["source_manifest_sha256"]
                or set(bundle["sources"]) != {source["content_sha256"]} or source["query"]["session_link"] != link
                or source["query"]["source_archives_sha256"] != report["source_archives_sha256"]
                or source["query"]["implementation_sha256"] != report["implementation_sha256"]
                or source["query"]["mapping_version"] != MAPPING_VERSION):
            raise ValueError(f"{provider}: observed source/bundle identity mismatch")
        lineage = json.loads((root / f"{provider}.lineage.json").read_text(encoding="utf-8"))
        if set(lineage) != set(COLUMNS):
            raise ValueError(f"{provider}: incomplete lineage table inventory")
        for name, table in tables.items():
            if stats["table_rows"][name] != table.num_rows or len(lineage[name]) != table.num_rows:
                raise ValueError(f"{provider}/{name}: observed row/lineage count mismatch")
            if stats["null_counts"][name] != {f: table[f].null_count for f in table.column_names}:
                raise ValueError(f"{provider}/{name}: observed missingness mismatch")
            for refs in lineage[name]:
                if name == "sessions":
                    if refs != {"identity": "verified archive metadata and explicit link"}:
                        raise ValueError(f"{provider}: invalid session lineage")
                    continue
                expected = {"laps", "stint_candidates"} if provider == "openf1" and name == "laps" else {
                    "laps" if provider == "fastf1" and name == "stints" else
                    "weather_data" if provider == "fastf1" and name == "weather" else
                    "race_control_messages" if provider == "fastf1" and name == "race_control" else name
                }
                if set(refs) != expected:
                    raise ValueError(f"{provider}/{name}: invalid native lineage tables")
                for native, indices in refs.items():
                    native = "stints" if native == "stint_candidates" else native
                    if not isinstance(indices, list) or any(
                        type(i) is not int or not 0 <= i < stats["native_table_rows"][native] for i in indices
                    ):
                        raise ValueError(f"{provider}/{name}: invalid native lineage row index")
    return report
