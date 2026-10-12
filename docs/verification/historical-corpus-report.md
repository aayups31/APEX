# R019 immutable historical corpus

## A. Current state

2026-10-11, baseline 7fa37e0; scoped research R1, production R0. R001-R018 DONE;
R019 TODO before this slice. Fresh baseline: 418 passed, two existing dependency
warnings, 185.35 s, `.cache/r019-baseline-20261011`. Fresh public-data demo at
`.cache/r019-public-baseline-20261011` passes: six simulated sessions, immutable
table/split hashes, full event grouping and explicit missing wind directions.
Its summary and file outputs were inspected. Pre-existing artifacts remain untouched.

## B. Scope

R019: register a verified two-event DEVELOPMENT collection, binding raw-provider
archives, metadata and canonical observed bundles to immutable identity/schema/
version manifests. R020 untouched benchmark freeze follows separately. No fitting,
outcome claims, research-to-kernel integration or world-model changes.

## C. Inputs

Master guide sections 7,9.1,11.4,15-17; existing source/archive/table/link contracts;
FastF1/OpenF1/Jolpica/observed verifiers and tests; scoped R1 review; new
[frozen protocol](../../research/protocols/HISTORICAL_CORPUS.md). British 2024
qualifying is inspected development evidence. Monza 2024 qualifying is selected
as a second development event, not as a hidden test. Metadata identity retrieval
is saved at `.cache/r019-monza-metadata-20261011.json`.

## D. Implementation

Add a versioned collection manifest and offline verifier over existing archive
APIs. Validate explicit provider/event/session identity, lineage, relative paths,
unique membership and development-only scope. Record hashes, queries, versions,
schemas and mapping quality; publish manifest only after acceptance and source
recheck. Add CLI/tests. Acquire/replay Monza using existing frozen adapters,
convert nullable observed tables and register both events. Preserve old contracts.

## E. Gate

At least two distinct real events, both providers and verified canonical bundles;
recorded versions/schema/hash lineage; immutable/portable collection; zero network
attempts during offline replay; targeted/full tests, lint and matrix CI. No partial
acquisition or simulated-only acceptance can close R019.

## F. Risks

Provider gaps, source/date aliases, unsafe paths, changed archives, missingness,
upstream reconstructions, version-sensitive serialization and benchmark leakage.
Unavailable streams fail their existing acquisition gate; partial artifacts remain
diagnostic and cannot be registered. R020's future benchmark excludes inspected
development events and must be frozen before modelling access.

## G. Order

Baseline; preregistration; registry/tests; acquire second development event while
implementing; offline replay; canonical mapping; real two-event collection;
checkpoint push; full regression/CI; compact evidence and R019 closure push.

Status: DONE (closed 2026-10-11). No maturity promotion from this infrastructure gate.

## H. Implementation checkpoint

Added `apexsim.data.event_corpus`, freeze/verify CLI commands, membership fixture
and Monza session link. New unit/CLI checks: 14 passed in 13.96 s; repository
Ruff passes. An initial sandbox run failed to allocate pytest's default temporary
directory before executing tests; rerunning with a fresh workspace basetemp
resolved that environment issue. Existing source/conversion contracts are unchanged.

New Monza acquisitions completed: FastF1 archive hash
a10ce20c5bb7f80a46d76211b760babbe31e22d7c43497e02b635f1dc5e80e87;
OpenF1 archive hash
26a40e1b9b7a9e7bc7d536f5553f22e58da9db8cf1c965a2dca95f000a711987.
Both offline replays pass, unchanged archives and zero network attempts.
FastF1 reproduces 46 native tables; OpenF1 reproduces 18 endpoint families and
56 source responses. Monza observed-table report completes with hash
93f29d7699735e325eef30ec174043b9eac84678d3801abd639b33f68cc7fe4d.

Both providers retain 276 lap and 79 weather rows. FastF1 yields 92 canonical
stints; OpenF1's 92 incompatible native stint ranges are quarantined, leaving
zero canonical stints and 72 ambiguous lap/stint associations. OpenF1 has 166
mapping issues; FastF1 has two. These are recorded quality limitations, not
invented compounds or implicit training approval. Native rows remain intact.

Real collection publication/verification, full regression and CI remain pending
at this checkpoint; R019 stays IN_PROGRESS and R020 TODO.

## I. Real collection acceptance and closure

Frozen collection `.cache/development-event-corpus-20261011.json` binds two
distinct events and two sessions: F1_2024_R12/Q (Silverstone) and F1_2024_R16/Q
(Monza), with two provider bundles per session. Membership rationale and
DEVELOPMENT-only role are explicit. Corpus content hash:
fe590620134cd63ccfb36b9c0eb79c8e0a0dc8b368582d5ff416e4c889ea922d.
Canonical schema fingerprint:
371da9ddd527d357c503a208331e1bc3c106cdb8d952b026e912063d07384607.
The registration's repeated native/canonical validation passed. A separate
fresh-process socket-audit-guarded verification passed with zero network attempts
and identical collection identity, saved at
`.cache/r019-corpus-verified-20261011.json`. All recorded source/version/schema
and canonical issue/row/null counts were inspected. Source archives remain intact.

Full local regression: 432 passed, two existing dependency warnings, 160.73 s,
`.cache/r019-full-20261011`. Repository Ruff and whitespace checks pass.
Implementation 1cc76493b3f3d3fecdafbb4df17f90be48fc0bed is pushed to main.
[GitHub CI 38192681842](https://github.com/aayups31/APEX/actions/runs/38192681842)
passed every step on Python 3.11/3.12, including the collection unit/CLI tests in
the full suite and all existing artifact commands. Live provider acquisition is
not part of normal CI; real collection/replay evidence is recorded locally.

The [machine evidence](historical-corpus-evidence.json) contains the complete
compact collection manifest, offline audit, Monza identity query, both provider
replay reports, nullable conversion/issue report, implementation hashes and CI
job/step results. Bulk telemetry/native/cache files stay ignored. R019 is DONE:
Machine-evidence content hash:
cc7b6b8fc0e883722fd469f3e1501e7a64c1cd02e019c96f83064535e45b619b.
Inventory at closure:
19/73 research tasks complete, 54 remaining; build inventory stays 13/66 DONE.
Research foundation stays scoped R1; production kernel stays R0; R2 accuracy is
not claimed. `training_ready=false` and `benchmark_frozen=false` remain enforced.

Next: R020 reserves separate whole events as permanently untouched benchmarks
before calibration or model inspection. Both development events are excluded.
The absence of a usable Monza OpenF1 stint table remains a recorded coverage gap
for future model/data selection; no fitting is authorized by this collection.
Rollback: revert the corpus code/CLI and collection documentation commits;
raw archives are immutable and need not be removed or changed. A later revision
must use a new schema or new output manifest, never overwrite this collection.
