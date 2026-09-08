# Public evidence tables v1

Backlog: P1-01 and P1-08. These contracts prepare public-data work; they do not
constitute calibrated R2 evidence. The runnable fixture is entirely simulated.

## Installation and verification

From the repository root, use Python 3.11 or 3.12:

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -e './apex_engine[dev,data-contracts]'
.venv/Scripts/python.exe -m apexsim.cli public-data-demo --output .cache/public-data-demo
.venv/Scripts/python.exe -m apexsim.cli validate-public-data .cache/public-data-demo/dataset
```

Use a new output directory for every demo. On POSIX, use `.venv/bin/python` for
the same commands. `real-data` additionally installs FastF1. PyArrow stays optional
for simulation/API users; the complete test suite requires `data-contracts`.

## Schema contract

`apex-public-tables-v1` defines five tables. The executable authority is
`apexsim.data.tables.table_schema`; [the frozen schema catalog](public-table-schema-v1.json)
records every Arrow type, field unit, nullability and primary key.

| Table | Primary key | Main evidence |
|---|---|---|
| sessions | session_id | event_id, season, round, event, session type, UTC start, track, source session ID, ruleset |
| laps | session_id, driver_id, lap_number | lap/sector seconds, session-relative start/pit times, accuracy/status, stint, compound, tyre age |
| stints | session_id, driver_id, stint_id | inclusive start/end laps, compound, reported tyre age at start |
| weather | session_id, timestamp_utc | air/track Celsius, rainfall boolean, humidity percent, pressure Pa, wind m/s and degrees |
| race_control | session_id, message_id | UTC time, category, flag, scope, original message, optional driver/lap/sector |

Every table carries `source`, `source_manifest_sha256`, and a non-null
`truth_labels` struct. The struct contains one label for **each other column**,
including identifiers. Supported labels are MEASURED, RECONSTRUCTED, IMPUTED,
PROXY, CALIBRATED, PRIOR, SIMULATED, GAME_DERIVED and UNKNOWN. Null values must
have UNKNOWN labels; non-null values must carry another supported label.

All columns must be supplied, including nullable columns. Missing observations are
explicit `None`, never invented zeroes, temperatures or compounds. An unavailable
entire stream is represented by a correctly typed empty table and a zero row count.
The sessions table cannot be empty. A passing schema report is not a completeness
gate: a bundle with no weather can be schema-valid but inadequate for calibration.

Numbers are finite, integer/boolean fields do not accept lossy coercion, lap and
sector durations are positive, and humidity/sector indices have explicit bounds.
Timestamps are aware UTC at microsecond precision; naive, non-UTC and finer-precision
inputs fail. Source adapters must convert explicitly before entering this boundary.
Pressure uses Pa, not hPa. Rainfall is an observed wet/dry indicator, not a rate.
Pit and start times are seconds relative to the source's declared session start.
Compound values are SOFT, MEDIUM, HARD, INTERMEDIATE, WET or null; older compound
taxonomies require an explicit mapping/version, never an implicit default.

Primary keys are unique. Child tables must reference existing sessions. Known
lap stint IDs must resolve to the same driver's stint and its inclusive lap range;
known compounds must agree. Stints cannot overlap; an unknown end is allowed only
for the final recorded stint of a driver. Same-time race-control messages remain
distinct through `message_id`; adapters preserve a stable source ID or reconstruct
one from source order. Deduplication and temporal alignment belong to P1-06.

## Portable immutable bundles

`make_table(name, records)` validates before Arrow conversion. `write_table` and
`read_table` enforce the physical schema and its metadata. `write_dataset` additionally
checks all cross-table relationships and verifies supplied source manifests and their
raw files before writing:

```text
dataset/
  sessions.parquet
  laps.parquet
  stints.parquet
  weather.parquet
  race_control.parquet
  sources/<source-content-sha256>.json
  manifest.json
```

`manifest.json` is the completion marker, written last. It includes per-table file
hashes, row counts, source snapshot hashes, null-count reports and a content hash.
Readers reject incomplete datasets, unsupported versions, mismatched lineage,
changed snapshots, changed Parquet files or changed reports. Completed paths cannot
be overwritten. Interrupted directories remain unavailable; select a new path.

Bundles use relative, fixed filenames and survive relocation. Raw-file references
inside source snapshots are historical audit information: raw files are verified
at bundle creation but are not required to read a relocated canonical bundle.
`load_source_manifest(..., verify_files=True)` separately audits an available raw cache.
Hashes detect accidental alteration; they are not cryptographic signatures or proof
that source observations are correct.

## Frozen splits

Prepare explicit assignments, for example:

```json
{"train": ["SYNTH_0_Q", "SYNTH_0_R"], "val": ["SYNTH_1_Q", "SYNTH_1_R"], "test": ["SYNTH_2_Q", "SYNTH_2_R"]}
```

```powershell
.venv/Scripts/python.exe -m apexsim.cli freeze-splits .cache/public-data-demo/dataset assignments.json .cache/experiment-splits.json "Frozen experiment purpose"
```

`apex-session-splits-v1` records the exact dataset and sessions-file hashes, explicit
purpose, sorted partitions, event grouping, train-only normalization policy and its
own content hash. It requires all sessions exactly once, three nonempty partitions,
disjoint event IDs and disjoint known season/round identities. Duplicate source
session identities are rejected, preventing aliases from bypassing the split.
There is no automatic benchmark selection or seed-based reshuffling.

Training can opt into these exact frozen partitions:

```yaml
data:
  public_dataset_path: .cache/public-data-demo/dataset
  split_manifest_path: .cache/public-data-demo/splits.json
```

Both paths must be provided together. Telemetry must contain exactly the declared
session IDs. The pipeline verifies evidence before fitting, copies the split manifest
into the run, records input hashes, and fits its existing standardizer only on train
rows. Legacy synthetic/CSV experiments keep their existing split path when neither
option is set; they do not acquire a frozen-public-benchmark claim.

Session IDs must be harmonized across providers by the later ingestion/metadata
work. If round is unavailable, cross-provider event identity relies on the supplied
event_id. These checks enforce declared grouping, not an independent identity oracle.
Repeated manual tuning against test data cannot be detected by this manifest.

## Remaining work

The new tables do not replace the legacy feature CSV and do not perform source
acquisition, alignment or interpolation. P1-03/P1-04 must preserve and replay raw
FastF1/OpenF1 data; P1-05 resolves metadata; P1-06 reports temporal joins; P1-07 removes
the legacy adapter placeholders. Freeze a real multi-event evaluation corpus only
after those gates. Research equation-fidelity tasks R012-R014 also remain open.

Implementation references: [Arrow Parquet I/O](https://arrow.apache.org/docs/python/parquet.html),
[Arrow schemas](https://arrow.apache.org/docs/python/generated/pyarrow.Schema.html).
