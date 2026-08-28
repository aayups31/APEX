# Immutable source-manifest verification report

## Verification identity

- Date: 2026-08-28
- Backlog row: P1-02
- Branch: `codex/foundation-platform-v1`
- Verified commit: `0ae8fb327a9db6a9fbd20d2d7d7739ebe4b91758`
- GitHub Actions run: [33193152352](https://github.com/aayups31/APEX/actions/runs/33193152352)
- Package/API/adapter version: 0.4.0

## Acceptance result

P1-02 is complete. Public-data adapter operations now emit immutable source manifests
using schema `apex-source-manifest-v1`. A manifest records the logical query, UTC access
time, terms or licence URL, adapter and target-schema versions, each endpoint query and
record count, decoded-payload hashes where accessible, persisted-file roles and hashes,
limitations, and a hash over its own content.

Existing outputs or sidecars are refused before a network request. Loading a manifest
verifies its content hash and every referenced file hash by default. Modified manifest
content, modified source files, missing files, source-identity mismatches, and absent
public-data manifests fail with named exceptions.

## Adapter and pipeline evidence

The offline OpenF1 integration fixture exercises independent `car_data`, `location`, and
`weather` responses. It verifies three endpoint records and payload hashes, the derived
canonical file hash, the CC BY-NC-SA 4.0 licence URL published by OpenF1, and overwrite
refusal. The fixture also exposed and fixed a duplicate `timestamp_s` reset-index defect
in the prior adapter.

FastF1 outputs receive an exclusive sidecar containing the complete session/driver/sample
query, output hash, official documentation URL, and the explicit limitation that P1-03
must freeze and enumerate FastF1-managed raw cache files.

For any pipeline configured with `source=fastf1` or `source=openf1`, a matching verified
`source_manifest_path` is mandatory. The pipeline copies that manifest into the immutable
run directory and includes its SHA-256 in the run-level input lineage. Synthetic fixtures
remain source-independent and do not pretend to be public data.

## Automated gate

The repository now contains 38 test functions and 40 cases after parameter expansion.
On both Python 3.11 and Python 3.12, the clean GitHub jobs passed installation, Ruff, the
complete Pytest suite, and Airflow-wrapper compilation:

- [Python 3.11](https://github.com/aayups31/APEX/actions/runs/33193152352/job/98923482029)
- [Python 3.12](https://github.com/aayups31/APEX/actions/runs/33193152352/job/98923482164)

Focused local checks also passed six manifest/platform cases, module compilation,
JavaScript syntax, Ruff, and `git diff --check`. Live source services were not contacted
by tests, so the gate is deterministic and does not consume provider capacity.

## Boundaries and next work

- P1-01 remains open: the five versioned Parquet table schemas are not yet implemented.
- P1-03 must freeze FastF1 raw cache files and prove offline session reconstruction.
- P1-04 must persist every OpenF1 raw endpoint response, not only its payload hash, and
  report complete endpoint row counts.
- A source manifest proves lineage and integrity; it does not prove data accuracy,
  licence suitability for a particular use, or real-world model validity.
