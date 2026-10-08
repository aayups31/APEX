# Jolpica event catalog verification

- Acquisition/validation: 2026-09-16; handoff: 2026-09-18 (America/Toronto)
- Branch: `codex/jolpica-event-catalog`
- Parent: `4ba6f90477f5f2d48d7cee7538f92ecdeddf5563`
- Scope: P1-05, DONE; Jolpica event metadata with custom user agent and pagination
- Maturity before/after: R0; no model or simulator promotion
- [Usage and archive contract](../data/jolpica-events.md)
- [Machine-readable acceptance evidence](jolpica-event-catalog-evidence.json)

## A. Current state and baseline

This work continues directly from the same unmodified implementation tested in the
preceding turn: 157 local tests passed, and GitHub Actions run 35170253557 passed on
Python 3.11 and 3.12. That exact commit's test evidence is reused, not presented as
a newly executed baseline suite. The public-data reference demo was rerun under
`.cache/jolpica-baseline-20260916`; all five tables and event-grouped splits passed.
The pre-existing untracked `artifacts/` directory remains untouched.

## B. Scope and dependencies

P1-05's immutable source-manifest dependency P1-02 is DONE. A complete metadata
catalog supports selection of multiple events before alignment and calibration.
R012-R014 research equation-fidelity/oracle gates remain open; acquisition work
does not bypass them. No telemetry is interpreted as calibrated simulator evidence.

## C. Sources and contracts

The master guide's provenance, missingness and immutable-artifact requirements;
the simulator maturity model; the live build/research backlogs; source-manifest v1;
and Jolpica's official endpoint/pagination/user-agent/rate-limit/terms documentation
linked in the archive guide govern the implementation.

## D. Implementation and execution order

1. Reuse bounded HTTP transport with provider-specific URL/diagnostics and Jolpica
   request spacing; identify the client using APEX's versioned user agent.
2. Preserve every response page, request metadata, hashes and source lineage.
3. Validate complete pagination and derive explicit season/round/circuit keys,
   preserving unknown race times rather than inventing them.
4. Expose download, verification and listing commands; test failures and real
   offline reconstruction.
5. Acquire both 2023 and 2024 calendars with page size 5, inspect event coverage,
   run full regression checks and publish compact evidence.

## E. Stopping gate

Both historical seasons must fetch all reported pages and event records, with a
custom user agent recorded on each request. Offline verification must recreate the
exact catalog and reject corruption, missing pages, changing totals, duplicate rounds,
wrong seasons and no-progress responses. The source archive must remain unchanged.
All tests and lint must pass before P1-05 is marked DONE.

## F. Risks and limits

These are calendar metadata snapshots, not full-race telemetry or training datasets.
Calendar times may differ from actual on-track timing. Cross-provider session mapping
requires separate evidence, and source-query completeness does not prove the upstream
calendar is correct. No parameters are fitted and no benchmark is tuned in this task.

## G. Acceptance evidence and next work

Both season calendars passed verification in a fresh Python process with a socket/DNS
audit guard installed: zero network attempts and no changed archive file hashes.
The local outputs are `.cache/jolpica-2023-20260916` and
`.cache/jolpica-2024-20260916`. There are **46 events across 24 distinct circuits**.

| Season | Events | Pages | Offsets | Manifest-covered bytes |
|---|---:|---:|---|---:|
| 2023 | 22 | 5 | 0, 5, 10, 15, 20 | 29,408 |
| 2024 | 24 | 5 | 0, 5, 10, 15, 20 | 31,773 |

Each archive contains 11 manifest-covered files: five raw pages, five HTTP sidecars
and the derived event index. The user agent is recorded on each page. The final
pages contain two and four records respectively, demonstrating correct handling
of incomplete final pages.

- 2023 archive SHA-256: `62f7dad20cf71d1a5b00a5c9476d95f7ca0972d4b16bdbae369f03cc034162c8`
- 2024 archive SHA-256: `66ace4d99431f6021ed128600f7112ca3b48b57049401bc0fa9c41d1f962d232`

Inspection confirmed British GP identifiers `F1_2023_R10` and `F1_2024_R12`, with
reported race dates July 9, 2023 and July 7, 2024. Both refer to provider circuit ID
`silverstone`; the differing rounds illustrate why matching by a fixed round number
across seasons would be wrong. Provider session linkage is not inferred from names.

The 30 new tests passed alongside the 48 OpenF1 cases. Coverage includes pagination,
returned-limit changes, empty seasons, absent race times, wrong source identities,
changing totals, duplicate rounds, HTTP error rejection, user agent/URL/pacing/retry
behaviour, manifest/file/query lineage, relocation and real offline subprocess
verification. The full suite passed: **187 tests**, four existing dependency/legacy
deprecation warnings, 107.27 seconds. Ruff, Airflow wrapper compilation and whitespace
checks passed. P1-05 is DONE: **11 of 66 build tasks complete, 55 remaining**.

Reproduce with the commands in the archive guide, choosing new output directories.
Source terms identify the data licence as CC-BY-NC-SA-4.0; raw provider data stays
ignored locally while code and compact acceptance evidence are version controlled.

Next: P1-06 explicit provider/session linkage and temporal alignment reports,
then P1-07 placeholder removal and a real multi-event telemetry corpus with frozen
splits. R012-R014 research gates remain required before maturity promotion.
