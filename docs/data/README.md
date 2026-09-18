# Data contracts and provenance

The [public table and frozen split guide](public-tables.md) covers the versioned
Parquet evidence boundary, portable bundles, CLI verification and event-safe splits.

The [FastF1 archive guide](fastf1-archives.md) covers complete-session acquisition,
cache preservation, native source tables and network-disabled reconstruction.

The [OpenF1 archive guide](openf1-archives.md) covers all 18 endpoint families,
original response preservation, explicit empty results and offline reconstruction.

The [Jolpica event catalog](jolpica-events.md) covers paginated season metadata,
stable season/round identifiers and offline verification of the saved calendar.

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

The legacy `ingest-openf1` command records separate request evidence for `car_data`, `location`, and `weather`, then
hashes its derived canonical CSV. Its published site links the data licence as
CC BY-NC-SA 4.0; the manifest stores the official licence URL.

The separate `download-openf1` command freezes the full versioned endpoint profile
and native values without the legacy feature CSV's interpolation or placeholders.
`verify-openf1` and `replay-openf1` check response lineage and exact reconstruction.

The legacy `ingest-fastf1` command records its logical query and canonical CSV output.
The separate `download-fastf1` command now freezes and enumerates an isolated full-session
cache and native source tables, with `replay-fastf1` verifying offline reconstruction.
Canonical mapping and a real untouched multi-event benchmark remain separate gates.

Default sidecars use `{output-name}.source.json`. Callers can supply an explicit manifest
path, but both the output and manifest paths must be new.

## Verification

```bash
cd apex_engine
pytest -q tests/test_source_manifest.py
```

The fixture covers manifest and file tampering, exclusive writes, a mocked three-endpoint
OpenF1 retrieval, payload hashes, request counts, and overwrite refusal without contacting
the live service.
