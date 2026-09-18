# Jolpica event catalog

P1-05 adds a versioned season/round/circuit index and freezes the paginated source
calendar behind it. This prepares multi-event selection; it does not collect race
telemetry, fit models or establish cross-provider session matches. Maturity remains R0.

## Commands

Run from the repository root with the existing environment:

```powershell
.venv/Scripts/python.exe -m apexsim.cli download-jolpica --season 2023 --page-size 5 --output .cache/jolpica-2023
.venv/Scripts/python.exe -m apexsim.cli download-jolpica --season 2024 --page-size 5 --output .cache/jolpica-2024
.venv/Scripts/python.exe -m apexsim.cli verify-jolpica .cache/jolpica-2023
.venv/Scripts/python.exe -m apexsim.cli verify-jolpica .cache/jolpica-2024
.venv/Scripts/python.exe -m apexsim.cli list-events .cache/jolpica-2024
```

Outputs must be new directories. The default page size is 100; a size of 5 makes
pagination visible for acceptance checks. `read_jolpica_events(path)` provides the
verified catalog through Python. Lookup keys such as `F1_2024_R12` are reconstructed
from season and round and remain stable within that frozen source calendar.

## Acquisition and source contract

The client calls `https://api.jolpi.ca/ergast/f1/{season}/races/` with explicit
`limit` and `offset`, using an `APEX/<version>` user agent. Seasons must be integer
values from 1950 through 2100; aliases such as `current` are rejected. Page sizes
must be 1–100. The archive caps a single season at 100 event records as a defensive
bound, not a statement about the racing calendar.

The client shares the existing bounded HTTP transport with OpenF1 through two
provider attributes: base URL and diagnostic name. Jolpica requests use 7.3 seconds
between starts, reflecting its published 500/hour sustained limit. The transport
provides four attempts, timeout/connection/429/5xx retries, bounded `Retry-After`
handling, response size bounds and no automatic redirects. Every successful page
has saved query, UTC retrieval time, HTTP status/attempt metadata and user agent.

The page envelope must identify F1, the requested season and the exact offset. The
total cannot change while paginating. Offsets advance by the actual number of
records, including when the server returns a lower limit. Empty intermediate pages,
excess rows, duplicate season/round keys and incorrect identities fail acquisition.
An empty season is recorded as a zero-row response snapshot, not a usable training set.
A page-size or count mismatch cannot silently terminate the download early.

## Archive and offline checks

```text
archive/
  raw/0000.json                 # original response body after HTTP decompression
  raw/0000.request.json         # request, retrieval time, HTTP evidence, user agent
  ...
  events.json                   # derived season/round/circuit index
  manifest.json                 # completion marker written last
```

`apex-jolpica-events-v1` records source lineage, all page queries/counts, raw and
decoded hashes, file sizes, software versions and HTTP policy. Relative paths make
the archive portable. Existing output directories cannot be reused. Failed downloads
retain partial diagnostics without publishing a completed manifest.

`verify-jolpica` checks the exact file inventory and source-manifest seal, validates
every page and its HTTP sidecar, proves pagination completed and reconstructs the
event index from the original bodies. It compares the complete reconstructed index
against `events.json`; all recorded files must match their hashes. It never creates
an HTTP client. Tests additionally execute verification under a Python socket/DNS
audit guard in a fresh interpreter. This is not an OS-wide network sandbox.

## Metadata semantics and limits

`apex-event-catalog-v1` records event ID, season, round, provider circuit ID, race
name/date/time and truth labels. Missing times stay null/UNKNOWN; no midnight default
is inserted. `MEASURED` follows APEX's definition of a value supplied directly by a
declared source. Here those values are reported calendar metadata, not observed car
states or actual on-track session-start times. The event ID is RECONSTRUCTED.

The original pages retain additional source fields such as practice/qualifying/sprint
schedules, circuit coordinates and URLs. No linked content is fetched. OpenF1 meeting
keys and FastF1 round/session identities are not automatically assigned through fuzzy
names; explicit provider mapping and temporal alignment remain P1-06 work.

Matching page totals cannot detect every upstream error or a live calendar revision
that changes content without changing the count. These are frozen retrieval snapshots,
not a claim that a current/future season is complete or immutable. Historical seasons
are the acceptance cases. The catalog alone is not a telemetry corpus or train/test split.

Raw downloads stay under ignored `.cache`; Git stores implementation, synthetic
fixtures and compact evidence. The source manifest links the provider's actual terms
and records CC-BY-NC-SA-4.0. Source-data rights remain distinct from software licensing.

Primary sources inspected 2026-09-16:

- [Jolpica pagination, envelopes and custom user agent](https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md)
- [Race metadata endpoint](https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/races.md)
- [Rate limits](https://github.com/jolpica/jolpica-f1/blob/main/docs/rate_limits.md)
- [Terms of use](https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md)
