# OpenF1 acquisition and offline replay verification

- Date: 2026-09-16
- Branch: `codex/openf1-offline-replay`
- Parent: `c0d8103` (FastF1 acquisition/replay; already pushed, not yet merged to main)
- Scope: P1-04, DONE
- Maturity before/after: R0; no model or simulator promotion
- [Archive contract and commands](../data/openf1-archives.md)
- [Machine-readable acceptance evidence](openf1-offline-replay-evidence.json)

## A. Baseline and current state

All 109 existing tests passed in 182.10 seconds, with four existing dependency/legacy
deprecation warnings. Ruff passed. The `public-data-demo` reference command wrote and
reopened five valid tables and event-grouped splits under
`.cache/openf1-baseline-20260916`; its summary reports `passed: true` and R0.

The pre-existing untracked `artifacts/` directory was left alone. The new branch
continues from the verified FastF1 branch, preserving that unmerged milestone.

## B. Scope and dependency decision

This continues the previously selected public-data acquisition sequence with P1-04;
its P1-02 immutable source-manifest dependency is DONE. It complements P1-03 and
unblocks P1-06 alignment. R012-R014 remain the earliest unresolved research gates;
this data infrastructure does not satisfy them or advance maturity beyond R0.

The stopping gate is an exact historical session with all 18 endpoint families,
saved response/query evidence and row counts, plus byte-identical native tables
rebuilt offline. Alignment, canonical feature filling, physics calibration,
world-model training and UI changes are outside this slice.

## C. Source-of-truth inputs

- Master guide sections 4, 9.1, 11, 15, 16 and 19; maturity model; P1-02/P1-04/P1-06.
- Existing source manifests, portable public-table contracts and FastF1 archive gate.
- [OpenF1 API reference](https://openf1.org/docs/) and
  [published limits/use guidance](https://openf1.org/), inspected 2026-09-16.
- Native historical source responses and synthetic provider-shaped test records.

## D. Implementation

1. A sequential HTTP client with bounded retries, timeouts, response size and request
   spacing; exact queries and preserved HTTP response bodies.
2. A complete versioned endpoint/driver request plan, immutable completion manifest,
   source lineage, file hashes, row counts, explicit empty/null/missing records and
   deterministic JSONL tables that retain native values.
3. Offline validation and a guarded fresh-process replay, exposed through
   `download-openf1`, `verify-openf1` and `replay-openf1`.
4. Failure tests for identity, coverage, HTTP, malformed payloads, overwrite attempts,
   tampering, lineage, unsafe paths and offline-worker errors.

## E. Evaluation gate

All endpoint families must be represented, including empty responses. Required
identity/core streams must be nonempty and every lap driver must have telemetry.
Each reconstructed table must match its frozen SHA-256 exactly; snapshot metadata
must match, networking attempts must be zero, and the source archive must remain
unchanged. Full regression tests and lint must pass before P1-04 is marked DONE.

## F. Limits

An empty API result is availability evidence, not evidence that a real event did
not occur. Source reconstruction/approximation, later identity mapping and temporal
alignment remain concerns. No train/test data are fitted or benchmark outcomes
used for tuning here. The network guard applies to Python socket operations.
Telemetry queries are partitioned by driver; reconstruction still holds a session
in memory. Failed runs preserve partial evidence and require a new output path.

## G. Acceptance evidence and next work

The real acquisition is session 9554, meeting 1240, 2024 British GP qualifying.
It requested all 20 drivers and all 18 endpoint families with 56 HTTP requests,
each successful on its first attempt (including four explicitly empty 404 results).
The archive covers 131 files and 227,862,794 bytes, excluding the manifest itself.
Acquisition started at 2026-09-17T01:14:02 UTC and the last response arrived at
01:17:17 UTC (the local date was still September 16).

| Native endpoint | Rows |
|---|---:|
| sessions | 1 |
| meetings | 1 |
| drivers | 20 |
| car_data | 385,580 |
| location | 393,300 |
| laps | 368 |
| stints | 102 |
| weather | 85 |
| race_control | 54 |
| pit | 101 |
| position | 1,799 |
| session_result | 20 |
| starting_grid | 20 |
| team_radio | 22 |
| intervals | 0 |
| overtakes | 0 |
| championship_drivers | 0 |
| championship_teams | 0 |
| **Total** | **781,473** |

Inspection confirmed 46 null lap durations and two null lap-start timestamps;
these remain null. The four empty endpoints retain their original 404 response
body, zero-row tables and explicit availability metadata. OpenF1 returned 54
race-control rows versus 46 in the earlier FastF1 archive; agreement between
providers is not assumed, and semantic/temporal reconciliation remains P1-06.

Local full suite: **157 passed**, four pre-existing warnings, 141.19 seconds.
The 48 new cases cover native value/missingness preservation, full endpoint/driver
coverage, relocation, actual offline subprocess replay, real socket/DNS denial,
immutable output paths, malformed JSON, unsafe paths, file/manifest/lineage tampering,
wrong or incomplete identities/streams, HTTP retries/limits and worker failure.
Ruff, the Airflow wrapper compilation and whitespace checks passed.

The live archive passed offline reconstruction: **18 identical endpoint tables,
zero network attempts, zero table mismatches, original archive unchanged**.
The report includes the four empty endpoints; a zero-row file is still verified.

- Archive SHA-256: `f792e17fc1270aeac688b12ed715e397559f76d1c379319831fc36e7f43016f5`
- Replay-report content SHA-256: `7f537c0619757648ba1b620bbf3b398839a2eee91be3b481543ac27065bc4439`
- Runtime environment: Python 3.12.12, APEX 0.4.0, Requests 2.34.2.
- Local archive: `.cache/openf1-9554-20260916`
- Local replay: `.cache/openf1-9554-20260916-replay`

Reproduction commands (choose new output paths when repeating):

```powershell
.venv/Scripts/python.exe -m apexsim.cli download-openf1 --session-key 9554 --output .cache/openf1-9554-20260916
.venv/Scripts/python.exe -m apexsim.cli replay-openf1 .cache/openf1-9554-20260916 --output .cache/openf1-9554-20260916-replay
.venv/Scripts/python.exe -m apexsim.cli verify-openf1 .cache/openf1-9554-20260916
.venv/Scripts/python.exe -m ruff check apex_engine/src apex_engine/tests
cd apex_engine
../.venv/Scripts/python.exe -m pytest -q
```

P1-04 is DONE: **10 of 66 build tasks** are complete, with 56 remaining. Raw source
data remains ignored locally; only implementation and compact evidence are tracked.

Next acquisition task is P1-05 Jolpica metadata, followed by P1-06 temporal alignment
and P1-07 removal of legacy placeholders. Research equation fidelity R012-R014
remains required before maturity promotion.
