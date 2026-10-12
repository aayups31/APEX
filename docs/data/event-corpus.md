# Immutable development event corpus v1

R019's `apex-development-event-corpus-v1` binds multiple events to complete
FastF1/OpenF1 archives, a Jolpica calendar and provider-separated observed tables.
Registration and verification are offline. They use the existing archive and
canonical-bundle verifiers; they do not load FastF1's parser pickles, merge
providers, impute missing values, fit models or select a benchmark.

Prepare JSON membership using `CorpusSession` fields: `fastf1`, `openf1`,
`jolpica`, `observed`, `rationale`, `role`. Paths are relative POSIX directories
under an explicit evidence root. Role must be DEVELOPMENT. At least two distinct
events are required; duplicates, provider aliases, wrong source lineage, traversal
and outputs inside referenced archives fail before writing the manifest.

```powershell
.venv/Scripts/python.exe -m apexsim.cli freeze-event-corpus .cache research/fixtures/development-corpus-membership-v1.json .cache/development-corpus-new.json "Frozen development acquisition evidence"
.venv/Scripts/python.exe -m apexsim.cli verify-event-corpus .cache/development-corpus-new.json .cache
```

Every input archive/observed run must already be complete. Output is a new JSON
file, written exclusively after all checks and a repeated source registration.
To relocate, move the evidence root with its referenced directory layout and
pass that new root to verification; the manifest does not store its absolute path.
The checked root is supplied by the caller, not inferred from arbitrary metadata.

Each entry records event/date/circuit/session identity, provider-native keys,
archive and source-manifest hashes, manifest-file hashes, native/canonical schema
versions, acquisition queries/UTC times/terms references, source library versions,
file counts/bytes, canonical row/null counts, issue counts and conversion lineage.
The corpus also binds the canonical schema fingerprint and registration code hash.
All source files remain protected by the original archive manifests.

The initial membership is British and Italian 2024 qualifying, explicitly
DEVELOPMENT. Those inspected events cannot become an untouched benchmark later.
`training_ready=false` and `benchmark_frozen=false` are enforced, not optional
labels. Source-backed mapping issues and absent fields remain visible. R020 must
freeze separate event reservations before modelling access; this collection is
not a substitute for that gate or for a validated causal feature builder.

Large source data remains ignored. Git stores code, membership/protocol and
compact verification evidence. Hashes establish integrity, not cache authenticity,
broadcast completeness, source licences or predictive accuracy.

R020 adds a default [permanent benchmark guard](permanent-benchmark.md). Protected
query, archive-identity or link metadata is refused before native payload reads;
the development corpus cannot admit a reserved weekend under a different name.
