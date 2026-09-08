"""Small, entirely simulated evidence bundle exercising P1-01 and P1-08 offline."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from apexsim.data.manifest import SourceManifest
from apexsim.data.splits import freeze_splits, load_splits
from apexsim.data.tables import (
    COLUMNS,
    LINEAGE_COLUMNS,
    TABLE_VERSION,
    columns,
    make_table,
    read_dataset,
    write_dataset,
)
from apexsim.provenance import write_manifest


def fixture_tables(source_digest: str) -> dict:
    """Three synthetic events with two sessions each; missing weather stays UNKNOWN."""
    records = {name: [] for name in COLUMNS}

    def add(name: str, session: str, **values) -> None:
        row = {col.name: None for col in columns(name)}
        row.update(session_id=session, source="synthetic", source_manifest_sha256=source_digest, **values)
        row["truth_labels"] = {
            key: "UNKNOWN" if value is None else "SIMULATED"
            for key, value in row.items() if key not in LINEAGE_COLUMNS
        }
        records[name].append(row)

    for event in range(3):
        for session_type in ("Q", "R"):
            session = f"SYNTH_{event}_{session_type}"
            start = datetime(2024, 1, 1 + event * 7, 14, tzinfo=timezone.utc)
            add("sessions", session, event_id=f"SYNTH_EVENT_{event}", season=2024,
                round=event + 1, event=f"Fixture event {event}", session_type=session_type,
                start_utc=start, track_id=f"synthetic_track_{event}", source_session_id=session,
                ruleset_version="synthetic-fixture-v1")
            add("stints", session, driver_id="fixture-driver", stint_id=1, start_lap=1,
                end_lap=2, compound="MEDIUM", tyre_age_at_start_laps=0.0)
            for lap in (1, 2):
                add("laps", session, driver_id="fixture-driver", lap_number=lap,
                    lap_time_s=90.0, start_time_s=(lap - 1) * 90.0,
                    sector1_time_s=30.0, sector2_time_s=30.0, sector3_time_s=30.0,
                    is_accurate=True, track_status="GREEN", stint_id=1,
                    compound="MEDIUM", tyre_age_laps=float(lap))
            add("weather", session, timestamp_utc=start, air_temp_c=22.0,
                track_temp_c=31.0, rainfall=False, humidity_pct=45.0,
                pressure_pa=101325.0, wind_speed_mps=None, wind_direction_deg=None)
            add("race_control", session, message_id="fixture-message-1", timestamp_utc=start,
                category="Flag", flag="GREEN", scope="Track", message="Synthetic green flag")
    return {name: make_table(name, rows) for name, rows in records.items()}


def run_public_data_demo(output: str | Path) -> dict:
    """Generate, reopen and inspect a hashed dataset and an event-safe split."""
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    source = SourceManifest("synthetic", {"fixture": "public-data-v1"}, "https://example.test/synthetic-only",
                            canonical_schema_version=TABLE_VERSION,
                            notes=["Entirely simulated contract fixture; no public observations."])
    source.add_request("fixture://public-data-v1", {"events": 3}, {"events": 3, "sessions_per_event": 2}, records=6)
    source_path = source.save(root / "fixture-source.json")
    dataset_path = root / "dataset"
    write_dataset(dataset_path, fixture_tables(source.to_dict()["content_sha256"]), [source_path])
    assignments = {partition: [f"SYNTH_{event}_Q", f"SYNTH_{event}_R"]
                   for event, partition in enumerate(("train", "val", "test"))}
    freeze_splits(dataset_path, assignments, root / "splits.json", purpose="Synthetic contract verification only")
    tables, manifest = read_dataset(dataset_path)
    splits = load_splits(root / "splits.json", dataset_path)
    summary = {"truth": "SIMULATED", "maturity": "R0", "passed": manifest["quality"]["passed"],
               "table_rows": {name: table.num_rows for name, table in tables.items()},
               "dataset_sha256": manifest["content_sha256"], "split_sha256": splits["content_sha256"],
               "partitions": splits["partitions"], "weather_missingness": manifest["quality"]["tables"]["weather"]["null_counts"]}
    write_manifest(root / "summary.json", summary)
    return summary
