"""P1-01: typed evidence tables, separate from the legacy model-feature CSV.

No coercion, resampling, imputation or unit conversion occurs at this boundary.
Adapters must supply canonical units, aware UTC timestamps and per-value truth labels.
"""
from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from numbers import Integral, Real
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from apexsim.data.manifest import load_source_manifest
from apexsim.provenance import file_sha256, payload_sha256, write_manifest

TABLE_VERSION = "apex-public-tables-v1"
DATASET_VERSION = "apex-public-dataset-v1"
TRUTH_LABELS = frozenset({
    "MEASURED", "RECONSTRUCTED", "IMPUTED", "PROXY", "CALIBRATED",
    "PRIOR", "SIMULATED", "GAME_DERIVED", "UNKNOWN",
})
LINEAGE_COLUMNS = {"source", "source_manifest_sha256", "truth_labels"}


@dataclass(frozen=True)
class Column:
    """One versioned field; numeric bounds are inclusive contract constraints."""

    name: str
    kind: str = "string"
    unit: str = "1"
    nullable: bool = False
    minimum: float | None = None
    maximum: float | None = None

    def arrow_field(self) -> pa.Field:
        types = {"string": pa.string(), "int": pa.int64(), "float": pa.float64(),
                 "bool": pa.bool_(), "utc": pa.timestamp("us", tz="UTC"),
                 "labels": pa.map_(pa.string(), pa.string())}
        return pa.field(self.name, types[self.kind], nullable=self.nullable,
                        metadata={"unit": self.unit})


COMMON = (
    Column("session_id"), Column("source"), Column("source_manifest_sha256"),
)
COMPOUNDS = {"SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"}
COLUMNS = {
    "sessions": (
        Column("event_id"), Column("season", "int", minimum=1950),
        Column("round", "int", nullable=True, minimum=1), Column("event"),
        Column("session_type"), Column("start_utc", "utc", "UTC", nullable=True),
        Column("track_id"), Column("source_session_id"),
        Column("ruleset_version", nullable=True),
    ),
    "laps": (
        Column("driver_id"), Column("lap_number", "int", "lap", minimum=1),
        Column("lap_time_s", "float", "s", True, minimum=0),
        Column("start_time_s", "float", "s", True, minimum=0),
        Column("sector1_time_s", "float", "s", True, minimum=0),
        Column("sector2_time_s", "float", "s", True, minimum=0),
        Column("sector3_time_s", "float", "s", True, minimum=0),
        Column("is_accurate", "bool", nullable=True),
        Column("track_status", nullable=True),
        Column("stint_id", "int", nullable=True, minimum=1),
        Column("compound", nullable=True),
        Column("tyre_age_laps", "float", "lap", True, minimum=0),
        Column("pit_in_time_s", "float", "s", True, minimum=0),
        Column("pit_out_time_s", "float", "s", True, minimum=0),
    ),
    "stints": (
        Column("driver_id"), Column("stint_id", "int", minimum=1),
        Column("start_lap", "int", "lap", minimum=1),
        Column("end_lap", "int", "lap", True, minimum=1),
        Column("compound", nullable=True),
        Column("tyre_age_at_start_laps", "float", "lap", True, minimum=0),
    ),
    "weather": (
        Column("timestamp_utc", "utc", "UTC"),
        Column("air_temp_c", "float", "degC", True, minimum=-273.15),
        Column("track_temp_c", "float", "degC", True, minimum=-273.15),
        Column("rainfall", "bool", nullable=True),
        Column("humidity_pct", "float", "%", True, minimum=0, maximum=100),
        Column("pressure_pa", "float", "Pa", True, minimum=0),
        Column("wind_speed_mps", "float", "m/s", True, minimum=0),
        Column("wind_direction_deg", "float", "deg", True, minimum=0, maximum=360),
    ),
    "race_control": (
        Column("message_id"), Column("timestamp_utc", "utc", "UTC"),
        Column("category"), Column("flag", nullable=True),
        Column("scope", nullable=True), Column("message"),
        Column("driver_id", nullable=True),
        Column("lap_number", "int", "lap", True, minimum=1),
        Column("sector", "int", nullable=True, minimum=1, maximum=3),
    ),
}
KEYS = {
    "sessions": ("session_id",),
    "laps": ("session_id", "driver_id", "lap_number"),
    "stints": ("session_id", "driver_id", "stint_id"),
    "weather": ("session_id", "timestamp_utc"),
    "race_control": ("session_id", "message_id"),
}


def columns(name: str) -> tuple[Column, ...]:
    if name not in COLUMNS:
        raise ValueError(f"Unknown public table: {name!r}")
    return (*COMMON, *COLUMNS[name], Column("truth_labels", "labels"))


def table_schema(name: str) -> pa.Schema:
    """Return the complete physical schema with version, units and primary key."""
    fields = [col.arrow_field() for col in columns(name) if col.name != "truth_labels"]
    labels = pa.struct([pa.field(col.name, pa.string(), nullable=False)
                        for col in columns(name) if col.name not in LINEAGE_COLUMNS])
    fields.append(pa.field("truth_labels", labels, nullable=False, metadata={"unit": "1"}))
    return pa.schema(fields, metadata={
        "apex.schema_version": TABLE_VERSION, "apex.table": name,
        "apex.primary_key": json.dumps(KEYS[name]),
        "apex.time_origin": "start_time_s and pit times are relative to session start",
    })


def _validate_rows(name: str, rows: list[dict[str, Any]]) -> None:
    specs = columns(name)
    expected = {col.name for col in specs}
    labelled = expected - LINEAGE_COLUMNS
    keys: set[tuple] = set()
    for index, row in enumerate(rows):
        where = f"{name}[{index}]"
        if set(row) != expected:
            raise ValueError(f"{where}: missing columns {sorted(expected - set(row))}; extra columns {sorted(set(row) - expected)}")
        for col in specs:
            value = row[col.name]
            error = f"{where}.{col.name}"
            if value is None:
                if not col.nullable:
                    raise ValueError(f"{error}: null is forbidden")
                continue
            if col.kind == "string" and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{error}: expected nonempty string")
            if col.kind == "int" and (isinstance(value, bool) or not isinstance(value, Integral)):
                raise ValueError(f"{error}: expected integer without coercion")
            if col.kind == "float" and (isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value)):
                raise ValueError(f"{error}: expected finite numeric value")
            if col.kind == "bool" and not isinstance(value, bool):
                raise ValueError(f"{error}: expected boolean without coercion")
            if col.kind == "utc" and (not isinstance(value, datetime) or value.utcoffset() != timedelta(0)):
                raise ValueError(f"{error}: expected timezone-aware UTC datetime")
            if col.kind == "utc" and getattr(value, "nanosecond", 0):
                raise ValueError(f"{error}: sub-microsecond precision is unsupported; convert explicitly")
            if col.minimum is not None and value < col.minimum:
                raise ValueError(f"{error}: below minimum {col.minimum}")
            if col.maximum is not None and value > col.maximum:
                raise ValueError(f"{error}: above maximum {col.maximum}")
        raw_labels = row["truth_labels"]
        try:
            labels = dict(raw_labels)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{where}: invalid truth_labels mapping") from exc
        if len(raw_labels) != len(labels) or set(labels) != labelled:
            raise ValueError(f"{where}: truth_labels must cover every data field exactly once")
        for field, label in labels.items():
            if label not in TRUTH_LABELS:
                raise ValueError(f"{where}.{field}: invalid truth label {label!r}")
            if (row[field] is None) != (label == "UNKNOWN"):
                raise ValueError(f"{where}.{field}: null values require UNKNOWN; known values require a supported truth label")
        if not re.fullmatch(r"[0-9a-f]{64}", row["source_manifest_sha256"]):
            raise ValueError(f"{where}: invalid source_manifest_sha256")
        if row.get("compound") is not None and row["compound"] not in COMPOUNDS:
            raise ValueError(f"{where}: unsupported compound")
        for field in ("lap_time_s", "sector1_time_s", "sector2_time_s", "sector3_time_s", "pressure_pa"):
            if row.get(field) == 0:
                raise ValueError(f"{where}.{field}: must be positive or explicitly unknown")
        if name == "stints" and row["end_lap"] is not None and row["end_lap"] < row["start_lap"]:
            raise ValueError(f"{where}: end_lap precedes start_lap")
        key = tuple(row[field] for field in KEYS[name])
        if key in keys:
            raise ValueError(f"{where}: duplicate primary key {key}")
        keys.add(key)


def make_table(name: str, rows: Sequence[Mapping[str, Any]]) -> pa.Table:
    """Validate explicit Python records before Arrow can silently cast their values."""
    records = [dict(row) for row in rows]
    _validate_rows(name, records)
    for row in records:
        row["truth_labels"] = dict(row["truth_labels"])
    return pa.Table.from_pylist(records, schema=table_schema(name))


def validate_table(name: str, table: pa.Table) -> dict[str, Any]:
    """Reject schema drift and invalid rows; report missingness without filling it."""
    if not table.schema.equals(table_schema(name), check_metadata=True):
        raise ValueError(f"{name}: physical schema, units or version mismatch")
    table.validate(full=True)
    _validate_rows(name, table.to_pylist())
    return {"rows": table.num_rows, "passed": True,
            "null_counts": {field: table[field].null_count for field in table.column_names}}


def validate_tables(tables: Mapping[str, pa.Table]) -> dict[str, Any]:
    """Validate the five-table dataset, including session and lap/stint references."""
    if set(tables) != set(COLUMNS):
        raise ValueError("Dataset requires exactly sessions, laps, stints, weather and race_control")
    report = {name: validate_table(name, table) for name, table in tables.items()}
    sessions = {row["session_id"] for row in tables["sessions"].to_pylist()}
    if not sessions:
        raise ValueError("Dataset requires at least one session")
    for name, table in tables.items():
        if set(table["session_id"].to_pylist()) - sessions:
            raise ValueError(f"{name}: orphan session_id")
    stints = {}
    previous = {}
    for row in sorted(tables["stints"].to_pylist(), key=lambda r: (r["session_id"], r["driver_id"], r["start_lap"])):
        group = (row["session_id"], row["driver_id"])
        if group in previous and (previous[group] is None or row["start_lap"] <= previous[group]):
            raise ValueError(f"stints: overlapping or unclosed stint for {group}")
        previous[group] = row["end_lap"]
        stints[(*group, row["stint_id"])] = row
    for lap in tables["laps"].to_pylist():
        if lap["stint_id"] is None:
            continue
        stint = stints.get((lap["session_id"], lap["driver_id"], lap["stint_id"]))
        if stint is None:
            raise ValueError("laps: orphan stint_id")
        if lap["lap_number"] < stint["start_lap"] or (stint["end_lap"] is not None and lap["lap_number"] > stint["end_lap"]):
            raise ValueError("laps: lap_number outside referenced stint")
        if lap["compound"] is not None and stint["compound"] is not None and lap["compound"] != stint["compound"]:
            raise ValueError("laps: compound disagrees with referenced stint")
    return {"schema_version": TABLE_VERSION, "passed": True, "tables": report}


def write_table(name: str, table: pa.Table, path: str | Path) -> Path:
    """Create a Parquet artifact exclusively; completed evidence is never replaced."""
    validate_table(name, table)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        pq.write_table(table, handle, compression="zstd", version="2.6")
    return output


def read_table(name: str, path: str | Path) -> pa.Table:
    table = pq.ParquetFile(path).read()
    validate_table(name, table)
    return table


def _validate_lineage(tables: Mapping[str, pa.Table], sources: Mapping[str, dict]) -> None:
    for name, table in tables.items():
        for source, digest in zip(table["source"].to_pylist(), table["source_manifest_sha256"].to_pylist(), strict=True):
            if digest not in sources or sources[digest]["source"] != source:
                raise ValueError(f"{name}: missing or mismatched source manifest {digest}")


def write_dataset(output: str | Path, tables: Mapping[str, pa.Table], source_manifests: Sequence[str | Path]) -> dict:
    """Freeze a portable bundle after validating raw lineage and all table contracts.

    manifest.json is written last as the completion marker. An interrupted bundle
    remains incomplete and cannot be loaded or reused; callers choose a new directory.
    """
    root = Path(output)
    if root.exists():
        raise FileExistsError(f"Dataset already exists: {root}")
    report = validate_tables(tables)
    sources = {}
    for path in source_manifests:
        manifest = load_source_manifest(path)
        sources[manifest["content_sha256"]] = manifest
    _validate_lineage(tables, sources)
    root.mkdir(parents=True, exist_ok=False)
    source_records = {}
    for digest, manifest in sorted(sources.items()):
        path = write_manifest(root / "sources" / f"{digest}.json", manifest)
        source_records[digest] = file_sha256(path)
    records = {}
    for name in COLUMNS:
        path = write_table(name, tables[name], root / f"{name}.parquet")
        records[name] = {"sha256": file_sha256(path), "rows": tables[name].num_rows}
    manifest = {"schema_version": DATASET_VERSION, "tables": records,
                "sources": source_records, "quality": report}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(root / "manifest.json", manifest)
    return manifest


def read_dataset(path: str | Path) -> tuple[dict[str, pa.Table], dict]:
    """Verify portable snapshots and Parquet hashes before exposing any table.

    Raw files were checked when frozen. Reading does not require the original cache;
    source snapshots retain those external references for later raw-data audits.
    """
    root = Path(path)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    digest = manifest.pop("content_sha256", None)
    if digest != payload_sha256(manifest):
        raise ValueError("Dataset manifest content hash mismatch")
    if manifest.get("schema_version") != DATASET_VERSION or set(manifest.get("tables", {})) != set(COLUMNS):
        raise ValueError("Unsupported or incomplete dataset schema")
    sources = {}
    for source_digest, expected in manifest["sources"].items():
        if not re.fullmatch(r"[0-9a-f]{64}", source_digest):
            raise ValueError("Invalid source manifest identifier")
        source_path = root / "sources" / f"{source_digest}.json"
        if file_sha256(source_path) != expected:
            raise ValueError("Dataset source snapshot hash mismatch")
        source = load_source_manifest(source_path, verify_files=False)
        if source["content_sha256"] != source_digest:
            raise ValueError("Dataset source identity mismatch")
        sources[source_digest] = source
    tables = {}
    for name, record in manifest["tables"].items():
        table_path = root / f"{name}.parquet"
        if file_sha256(table_path) != record["sha256"]:
            raise ValueError(f"{name}: dataset artifact hash mismatch")
        tables[name] = read_table(name, table_path)
        if tables[name].num_rows != record["rows"]:
            raise ValueError(f"{name}: dataset row count mismatch")
    if validate_tables(tables) != manifest["quality"]:
        raise ValueError("Dataset quality report mismatch")
    _validate_lineage(tables, sources)
    manifest["content_sha256"] = digest
    return tables, manifest
