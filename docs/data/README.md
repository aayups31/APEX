# Data contracts and provenance

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

OpenF1 records separate request evidence for `car_data`, `location`, and `weather`, then
hashes its derived canonical CSV. Its published site links the data licence as
CC BY-NC-SA 4.0; the manifest stores the official licence URL.

FastF1 records the complete logical session query and canonical output. FastF1 controls
its own raw cache, so freezing and enumerating every cache source file remains explicitly
assigned to P1-03. A FastF1-derived output is not an untouched benchmark until that gate
passes.

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
