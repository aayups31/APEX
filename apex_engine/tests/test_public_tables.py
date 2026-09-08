import copy
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.data.manifest import SourceManifest
from apexsim.data.tables import (
    COLUMNS,
    TABLE_VERSION,
    make_table,
    read_dataset,
    read_table,
    table_schema,
    validate_table,
    validate_tables,
    write_dataset,
    write_table,
)
from apexsim.examples.public_data_demo import fixture_tables, run_public_data_demo


@pytest.fixture
def tables():
    return fixture_tables("a" * 64)


@pytest.mark.parametrize("name", list(COLUMNS))
def test_parquet_round_trip_preserves_types_units_truth_and_missingness(tmp_path, tables, name):
    table = tables[name]
    path = write_table(name, table, tmp_path / f"{name}.parquet")
    restored = read_table(name, path)
    assert restored.equals(table, check_metadata=True)
    assert restored.schema.metadata[b"apex.schema_version"] == TABLE_VERSION.encode()
    if name == "weather":
        assert restored.schema.field("pressure_pa").metadata[b"unit"] == b"Pa"
        assert restored["wind_speed_mps"].null_count == 6
        assert dict(restored.to_pylist()[0]["truth_labels"])["wind_speed_mps"] == "UNKNOWN"
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        write_table(name, table, path)
    assert path.read_bytes() == before


@pytest.mark.parametrize(("name", "field", "value", "message"), [
    ("laps", "lap_number", 1.5, "integer without coercion"),
    ("laps", "lap_number", True, "integer without coercion"),
    ("laps", "lap_time_s", float("nan"), "finite numeric"),
    ("laps", "lap_time_s", float("inf"), "finite numeric"),
    ("laps", "lap_time_s", -3.0, "below minimum"),
    ("laps", "lap_time_s", 0.0, "must be positive"),
    ("laps", "compound", "SUPER_GRIP", "unsupported compound"),
    ("sessions", "session_id", "", "nonempty string"),
    ("sessions", "session_id", None, "null is forbidden"),
    ("weather", "rainfall", 1, "boolean without coercion"),
    ("weather", "humidity_pct", 101.0, "above maximum"),
    ("weather", "timestamp_utc", datetime(2024, 1, 1), "timezone-aware UTC"),
    ("weather", "timestamp_utc", "2024-01-01T00:00:00Z", "timezone-aware UTC"),
    ("weather", "timestamp_utc", pd.Timestamp("2024-01-01T00:00:00.000000001Z"), "sub-microsecond precision"),
    ("weather", "source_manifest_sha256", "invalid", "invalid source_manifest"),
])
def test_bad_values_fail_before_arrow_coercion(tables, name, field, value, message):
    rows = tables[name].to_pylist()
    rows[0][field] = value
    with pytest.raises(ValueError, match=message):
        make_table(name, rows)


def test_labels_must_be_complete_and_match_missing_values(tables):
    row = tables["weather"].to_pylist()[0]
    labels = dict(row["truth_labels"])
    for changed, message in [
        ({**labels, "wind_speed_mps": "MEASURED"}, "null values require UNKNOWN"),
        ({**labels, "air_temp_c": "UNKNOWN"}, "null values require UNKNOWN"),
        ({**labels, "air_temp_c": "GROUND_TRUTH"}, "invalid truth label"),
        ({"air_temp_c": "MEASURED"}, "cover every data field"),
        ([*labels.items(), ("air_temp_c", "SIMULATED")], "exactly once"),
    ]:
        with pytest.raises(ValueError, match=message):
            make_table("weather", [{**row, "truth_labels": changed}])


def test_schema_drift_extra_columns_duplicates_and_nullability_fail(tmp_path, tables):
    table = tables["laps"]
    row = table.to_pylist()[0]
    with pytest.raises(ValueError, match="duplicate primary key"):
        make_table("laps", [row, row])
    with pytest.raises(ValueError, match="extra columns"):
        make_table("laps", [{**row, "mystery": 2}])
    with pytest.raises(ValueError, match="missing columns"):
        make_table("laps", [{key: value for key, value in row.items() if key != "is_accurate"}])
    for schema in [table.schema.remove_metadata(), table.schema.with_metadata({"apex.schema_version": "v99"})]:
        with pytest.raises(ValueError, match="schema, units or version mismatch"):
            validate_table("laps", table.cast(schema))
    rows = table.to_pylist()
    rows[0]["session_id"] = None
    malformed = pa.Table.from_pylist(rows, schema=table_schema("laps"))
    with pytest.raises(ValueError, match="null is forbidden"):
        validate_table("laps", malformed)
    path = tmp_path / "wrong.parquet"
    pq.write_table(table.replace_schema_metadata({}), path)
    with pytest.raises(ValueError, match="schema, units or version mismatch"):
        read_table("laps", path)


def test_cross_table_references_stint_ranges_and_compounds(tables):
    assert validate_tables(tables)["passed"]
    for field, value, message in [
        ("session_id", "absent", "orphan session_id"),
        ("stint_id", 3, "orphan stint_id"),
        ("lap_number", 5, "outside referenced stint"),
        ("compound", "HARD", "compound disagrees"),
    ]:
        rows = tables["laps"].to_pylist()[:1]
        rows[0][field] = value
        with pytest.raises(ValueError, match=message):
            validate_tables({**tables, "laps": make_table("laps", rows)})
    rows = tables["stints"].to_pylist()[:1]
    other = copy.deepcopy(rows[0])
    other.update(stint_id=2, start_lap=2, end_lap=4)
    with pytest.raises(ValueError, match="overlapping"):
        validate_tables({**tables, "stints": make_table("stints", [*rows, other])})


def test_missing_observation_tables_are_explicit_empty_tables(tables):
    dataset = {name: table if name == "sessions" else make_table(name, []) for name, table in tables.items()}
    assert validate_tables(dataset)["tables"]["weather"]["rows"] == 0
    with pytest.raises(ValueError, match="requires exactly"):
        validate_tables({"sessions": tables["sessions"]})


def test_bundle_portable_immutable_and_tamper_evident(tmp_path):
    root = tmp_path / "demo"
    summary = run_public_data_demo(root)
    assert summary["passed"] and summary["table_rows"]["laps"] == 12
    moved = tmp_path / "relocated"
    shutil.copytree(root / "dataset", moved)
    _, manifest = read_dataset(moved)
    assert manifest["content_sha256"] == summary["dataset_sha256"]
    with pytest.raises(FileExistsError):
        run_public_data_demo(root)
    with pytest.raises(FileExistsError):
        write_dataset(moved, {}, [])
    with (moved / "laps.parquet").open("ab") as handle:
        handle.write(b"tampered")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        read_dataset(moved)
    payload = json.loads((root / "dataset" / "manifest.json").read_text())
    payload["tables"]["laps"]["rows"] += 1
    (root / "dataset" / "manifest.json").write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="manifest content hash mismatch"):
        read_dataset(root / "dataset")


def test_source_lineage_must_exist_and_match_before_writing(tmp_path, tables):
    output = tmp_path / "dataset"
    with pytest.raises(ValueError, match="missing or mismatched source"):
        write_dataset(output, tables, [])
    assert not output.exists()
    source = SourceManifest("openf1", {}, "https://example.test/terms")
    source.add_request("fixture://data", {}, [], 0)
    source_path = source.save(tmp_path / "source.json")
    wrong_source = fixture_tables(source.to_dict()["content_sha256"])
    with pytest.raises(ValueError, match="missing or mismatched source"):
        write_dataset(output, wrong_source, [source_path])
    assert not output.exists()


def test_source_snapshot_tampering_and_incomplete_bundles_fail(tmp_path):
    root = tmp_path / "evidence"
    run_public_data_demo(root)
    source_path = next((root / "dataset" / "sources").glob("*.json"))
    source_path.write_text("{}")
    with pytest.raises(ValueError, match="source snapshot hash mismatch"):
        read_dataset(root / "dataset")
    incomplete = tmp_path / "interrupted"
    incomplete.mkdir()
    with pytest.raises(FileNotFoundError):
        read_dataset(incomplete)


def test_cli_generates_and_validates_real_parquet_artifacts(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(app, ["public-data-demo", "--output", str(tmp_path / "cli")])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["validate-public-data", str(tmp_path / "cli" / "dataset")])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["passed"]


def test_utc_precision_is_preserved(tmp_path, tables):
    rows = tables["weather"].to_pylist()
    rows[0]["timestamp_utc"] = datetime(2024, 1, 1, 14, 0, 0, 123456, tzinfo=timezone.utc)
    path = write_table("weather", make_table("weather", rows), tmp_path / "weather.parquet")
    assert read_table("weather", path).to_pylist()[0]["timestamp_utc"] == rows[0]["timestamp_utc"]


def test_version_one_schema_matches_frozen_catalog():
    catalog_path = Path(__file__).resolve().parents[2] / "docs/data/public-table-schema-v1.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert catalog["schema_version"] == TABLE_VERSION
    for name in COLUMNS:
        schema = table_schema(name)
        actual = {
            "metadata": {key.decode(): value.decode() for key, value in schema.metadata.items()},
            "fields": [{"name": field.name, "type": str(field.type), "nullable": field.nullable,
                        "unit": field.metadata[b"unit"].decode()} for field in schema],
        }
        assert actual == catalog["tables"][name], "Schema changes require an explicit version/migration decision"
