# Data contracts and provenance

The [public table and frozen split guide](public-tables.md) covers the versioned
Parquet evidence boundary, portable bundles, CLI verification and event-safe splits.

The [FastF1 archive guide](fastf1-archives.md) covers complete-session acquisition,
cache preservation, native source tables and network-disabled reconstruction.

The [OpenF1 archive guide](openf1-archives.md) covers all 18 endpoint families,
original response preservation, explicit empty results and offline reconstruction.

The [Jolpica event catalog](jolpica-events.md) covers paginated season metadata,
stable season/round identifiers and offline verification of the saved calendar.

The [temporal alignment guide](temporal-alignment.md) covers explicit session links,
timestamp associations, coverage gaps and source disagreements over those archives.

The [observed fields guide](observed-tables.md) covers source-backed nullable mapping,
provider-separated evidence, quarantine reasons and complete-run verification.

APEX treats every public-data retrieval as immutable evidence. A source adapter must
create a sidecar using schema `apex-source-manifest-v1` before its output can enter a
calibration or evaluation pipeline.

## Source manifest contract

Each manifest records:

- source and adapter version;
- the complete logical query and access time in UTC;
- every endpoint, endpoint query, returned record count, and decoded-payload SHA-256
  when the payload is available;
- the current source terms or licence URL and licence identifier when known;
- every persisted raw or derived file with role, row count, byte count, and SHA-256;
- the target canonical schema version;
- a SHA-256 over the manifest content itself;
- limitations and source-specific notes.

Manifests are created with exclusive file semantics and cannot overwrite an existing
record. The loader verifies the content hash and, by default, every referenced file hash.
An adapter also refuses to overwrite its existing output or sidecar.

## Adapter behavior

The `download-openf1` command freezes the full versioned endpoint profile
and native values without interpolation or placeholders.
`verify-openf1` and `replay-openf1` check response lineage and exact reconstruction.

The `download-fastf1` command freezes and enumerates an isolated full-session
cache and native source tables, with `replay-fastf1` verifying offline reconstruction.
The `build-observed-tables` command converts verified archives to the five canonical
tables, preserving units, truth labels, missingness and native row references.
`verify-observed-tables` validates the enclosing run and both provider bundles.
The former `ingest-fastf1` and `ingest-openf1` functions and commands fail before
network/filesystem changes with migration instructions. Public dense CSV ingestion
for training is blocked until a validated feature builder exists. Synthetic inputs
remain supported. A real untouched multi-event benchmark is still required.

## Verification

```bash
cd apex_engine
pytest -q tests/test_source_manifest.py
```

Fixtures cover manifest/file tampering, exclusive writes and retirement of both
legacy converters without requests or writes. Mapping and portable-run integrity
checks are in `tests/test_observed_tables.py`.
