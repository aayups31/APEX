# Foundation and local platform verification report

## Verification identity

- Date: 2026-08-28
- Branch: `codex/foundation-platform-v1`
- Verified commit: `bcfefd0ae37a187b1159a6f7030dda8a403562b3`
- GitHub Actions run: [33192144711](https://github.com/aayups31/APEX/actions/runs/33192144711)
- Maturity before: R0 code existed, but its P0 evidence backlog was open
- Maturity after: R0 foundation verified; no R1-or-later promotion claimed

## Scope

This gate closes P0-01 through P0-05 and verifies the first local evidence-platform
slice. It does not validate real-world calibration, historical predictions, stochastic
full-field realism, strategy optimality, or production multi-user operation.

## Clean-environment gate

The root GitHub workflow installed the editable project with development dependencies,
ran Ruff, ran the complete Pytest suite, and compiled the Airflow wrapper independently
on Python 3.11 and Python 3.12. Every step passed in both jobs. The repository contains
34 test functions and 36 collected cases after parameter expansion.

CI jobs:

- [Python 3.11](https://github.com/aayups31/APEX/actions/runs/33192144711/job/98920040294): passed
- [Python 3.12](https://github.com/aayups31/APEX/actions/runs/33192144711/job/98920040143): passed

## Focused local gate

Executed from the repository and engine directories:

```bash
python -m ruff check apex_engine/src apex_engine/tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q \
  tests/test_complete_sim_validation.py \
  tests/test_provenance.py \
  tests/test_platform_api.py
node --check apex_engine/src/apexsim/web/platform.js
git diff --check
```

Result: Ruff passed; 13 focused cases passed; JavaScript syntax passed; the diff check
passed. The local shell uses unsupported Python 3.9, so the complete local collection was
not used as release evidence. A temporary Python 3.12 dependency installation was
abandoned and removed when the host ran out of disk while extracting Torch. The two
clean GitHub environments are the authoritative complete-suite result.

## Determinism and artifact evidence

For fixed seed 123, two independent one-lap six-car runs produce exactly equal in-memory
telemetry, standings, and events, plus byte-identical persisted telemetry, standings,
events, and quality-report artifacts. Completed directories cannot be reused.

Every race run now includes:

- configuration payload and SHA-256;
- Git commit, branch, dirty-state fingerprint, and source SHA-256;
- Python/platform/package environment and SHA-256;
- input and output file sizes and SHA-256 values;
- explicit simulated/proxy truth labels;
- track, telemetry, lap, stint, event, standings, summary, and quality evidence.

## Invariant evidence

The simulator rejects or reports duplicate car-time keys, negative speed/fuel, excess
fuel, invalid energy state, invalid tyre health, backward distance/time/lap movement,
out-of-range or duplicate positions, invalid controls, simultaneous pedal conflicts,
non-finite core values, and conflicting terminal states. Runtime promotion aborts with
the names and counts of the earliest broken contracts.

## Platform gate

A live local run returned successful responses for the interface, health, overview, job
submission, job status, summary, manifest, standings, events, track, and sampled
telemetry routes. The submitted one-lap seed-42 preview completed in 1.35 seconds on the
verification host and its quality report passed all current R0 invariants.

The API contract is versioned at `/api/v1`, publishes typed job/health/overview schemas,
rejects unknown or out-of-range preview inputs, bounds replay payloads, prevents artifact
path escape, and converts interrupted local tasks into explicit failed jobs after a
restart. The packaged UI consumes only these routes and labels current results as
simulated evidence.

Visual browser QA was not claimed because the in-app browser-control connection was not
available in this environment. HTML delivery, static assets, JavaScript syntax, API
integration, and responsive CSS source were verified; visual regression remains an open
product-hardening check.

## Known boundaries and next dependency

- The local background executor is in-process, not a durable distributed worker.
- There is no authentication, multi-user isolation, rate limiting, object storage, or
  deployment configuration yet.
- R0 parameters remain generic priors and latent proxies.
- P9 UI rows remain open; this interface is an evidence consumer, as recorded by ADR 0001.
- The next dependency-ordered work is P1-01 and P1-02: versioned Parquet contracts and
  immutable source-download manifests.
