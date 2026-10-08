# Temporal alignment verification

- Validation date: 2026-09-19 (America/Toronto)
- Branch: `codex/temporal-alignment-report`
- Parent: `2e1d76e0de4856e1f33a8693ab103d74aabd67ec`
- Scope: P1-06, source linkage and temporal alignment diagnostics
- Maturity before/after: R0; no model or simulator promotion
- [Usage and output contract](../data/temporal-alignment.md)
- [Machine-readable acceptance evidence](temporal-alignment-evidence.json)

## A. Current state and baseline

The clean tracked baseline passed 187 tests (117.55 seconds, four existing
dependency/legacy warnings), Ruff and the public-data reference demo. Its output
at `.cache/alignment-baseline-20260919` was inspected: all five public tables and
event-grouped partitions passed validation. Dataset SHA-256 was
`15980dc69431c6169bf3b0c4f81a8c2829640bfd3bf5e82dd9e2378eb5c99935`;
split SHA-256 was
`1a32c2ddf07f35d6bf456f2c42c7d26e069a2a19321a89bf56e597254afeff28`.
The pre-existing untracked `artifacts/` directory was left untouched.

## B. Scope and dependencies

P1-06's FastF1 and OpenF1 acquisition dependencies are DONE; the preceding Jolpica
catalog also supplies an independent calendar identity check. This milestone
reports association rates, tolerances and gaps over preserved sources. Canonical
field conversion and placeholder removal remain P1-07. Research equation-fidelity
and oracle gates R012–R014 remain open and required before maturity promotion.

## C. Sources and contracts

The master build guide, simulator maturity model, live build/research backlogs,
native archive contracts and immutable source manifests govern this change.
The explicit link joins FastF1 2024 round 12 qualifying, OpenF1 session 9554 /
meeting 1240 / circuit 2, and Jolpica 2024 round 12 / `silverstone`, on July 6.
All three archives are verified before and after processing. No fuzzy identity
matching or source-clock correction is performed.

## D. Implementation and execution order

1. Check the explicit mapping, provider dates and equal driver inventories.
2. Normalize provider timestamps with nanosecond resolution and documented UTC
   conventions; preserve missingness and original source row identities.
3. Profile every driver car/location stream and shared weather stream for gaps,
   duplicates, missing timestamps and source-order reversals.
4. Build backward car-to-location/weather associations within each provider;
   build nearest cross-provider diagnostics with future-match counts.
5. Compare driver/lap keys and exact race-control messages without reconciling
   source disagreements, then publish hashed pair files and a completion manifest.
6. Test adversarial cases, run the full suite and inspect the real archived session.

## E. Stopping gate

The report must include rates, declared tolerances and every above-threshold gap
for all drivers; backward joins must contain no future timestamps. Missing or
ambiguous matches must remain explicit. Wrong identity, duplicate lap keys, source
mutation and overwrite attempts must fail. All source files must remain unchanged;
the offline real-data run, artifact hash checks, full regression suite and lint
must pass before P1-06 is DONE. A high join rate is not a training-readiness gate.

## F. Risks and limits

This is one qualifying session, not a multi-circuit telemetry benchmark. Matching
timestamps can reflect shared upstream data and do not establish independent
measurements, equal field meanings or physical accuracy. Backward matches are
causal only by recorded timestamps; actual publication latency is unknown.
Nearest matches are retrospective diagnostics and must not feed causal policies.
Tolerances are declared PRIOR choices, not fitted error bounds. The explicit
mapping remains an assertion checked against provider metadata.

The lap-start differences below require semantic investigation before canonical
training rows are derived. A shared driver/lap key does not guarantee the two
providers define the start of that lap identically. Neither provider is silently
selected as truth. `training_ready` remains false.

## G. Acceptance evidence and next work

The final run is `.cache/alignment-british-2024-q-20260919-v2`. It reads the three
saved archives in a fresh Python process with the existing socket/DNS audit guard
installed before importing the CLI: **zero network attempts**. This is a Python
audit guard, not an OS-wide network sandbox. All source archive hashes were
unchanged, all output file/content hashes were checked, and representative pair
files were read back to confirm counts and timestamp causality.

There are **20 drivers, 82 timestamp streams, 121 temporal joins and 368 matched
driver/lap keys**. The streams contain 1,557,930 timestamp rows across the two
providers; this counts overlapping observations from both sources, not independent
measurements. The output has 122 Parquet pair files and 125 manifest-covered files.

| Association | Left rows | Matched | Join rate | Maximum absolute delta |
|---|---:|---:|---:|---:|
| FastF1 car to OpenF1 car | 385,580 | 385,580 | 100% | 1 ms |
| FastF1 location to OpenF1 location | 393,300 | 393,300 | 100% | 1 ms |
| FastF1 weather to OpenF1 weather | 85 | 85 | 100% | 1 ms |
| FastF1 car to location | 385,580 | 384,800 | 99.7977% | 996 ms |
| OpenF1 car to location | 385,580 | 384,800 | 99.7977% | 995 ms |
| FastF1 car to weather | 385,580 | 382,580 | 99.2220% | 60,073 ms |
| OpenF1 car to weather | 385,580 | 382,580 | 99.2220% | 60,074 ms |

Rates use all left rows and are aggregated across drivers. All backward joins
contain zero future matches. Each provider's car/location joins leave 640 rows
without a preceding location and 140 outside tolerance. Each provider's weather
joins leave 3,000 rows without a preceding weather observation. Those rows are
retained with reasons; no weather or location value is invented.

The 82 streams have zero missing timestamps, duplicate timestamp rows or source
order reversals in this case, and **1,620 above-threshold gap occurrences** across
the streams. These include corresponding gaps reported by both providers and are
not 1,620 distinct race incidents. Each gap's bounds and duration are retained.

All 368 driver/lap keys match. Only 255 lap-duration pairs are comparable; those
agree exactly, while 113 retain missing comparisons. There are 366 comparable lap
starts and two missing comparisons. Their OpenF1-minus-FastF1 median is 73 ms,
with a maximum absolute difference of **606,216 ms (606.216 seconds)**. For example,
driver 27 lap 4 starts at 14:24:40.812 UTC in FastF1 and 14:34:47.028 UTC in OpenF1;
the FastF1 lap duration is missing. No offset correction is used to disguise this.

All 46 FastF1 race-control messages have exact timestamp/category/text matches.
OpenF1 has eight additional `SessionStatus` messages: four starts, three finishes
and one abort. Their original text/timestamps remain in the diagnostic report;
the report does not construct a merged race-control state. The actual FastF1
session start is 87 ms after the OpenF1 scheduled start, another distinction kept
separate from telemetry-clock comparison.

The 25 new tests cover causality, nearest ties, target reuse, duplicate ambiguity,
missing/empty streams, exact tolerance boundaries, nanosecond precision, timezone
rules, gaps, wrong links, mismatched driver inventories, source mutation, duplicate
lap keys, manifest lineage, output refusal and the CLI. Synthetic integration tests
stub archive verification (the archive modules have separate tests); the real
acceptance run uses all three actual verifiers.

Final validation results and hashes are recorded in the companion evidence JSON.
The initial and final real runs also compare pair-file hashes, ensuring the explicit
timedelta-unit compatibility fix does not alter associations or values.

The final full suite passed **212 tests in 148.82 seconds**, with only the four
pre-existing dependency/legacy warnings and no new warnings. Ruff, Airflow wrapper
compilation and whitespace checks passed. P1-06 is DONE: **12 of 66 build tasks
complete, 54 remaining**. This is a task count, not a percentage of total effort.

- Report content SHA-256: `44efb514a1a452be5e1bf64887673f7bb7a4f9b87bf4c2d558f044e3e22b2bf6`
- Run manifest SHA-256: `85762a04a5a447f04ce45d98e5ab7abecc7e76fa76ccc496ca89eee037308c90`
- Manifest-covered output bytes: 46,654,217 (bulk files remain ignored locally)

Next: P1-07 replaces placeholder observed weather/compound/pit fields with supported
source values or explicit unknowns. That work must resolve which source fields and
lap boundary semantics are appropriate before deriving canonical rows. Then extend
the verified telemetry corpus across events and circuits, with frozen event-safe
splits and held-out evaluation. R012–R014 remain required research gates.
