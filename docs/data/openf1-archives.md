# OpenF1 session archives and offline reconstruction

P1-04 adds reproducible acquisition for an exact historical `session_key`. Source
values remain in their native representation until the separate P1-06 alignment
and P1-07 truth-label/placeholder gates. This is acquisition evidence at R0.

## Commands

From the repository root, using the existing environment:

```powershell
.venv/Scripts/python.exe -m apexsim.cli download-openf1 --session-key 9554 --output .cache/openf1-9554
.venv/Scripts/python.exe -m apexsim.cli verify-openf1 .cache/openf1-9554
.venv/Scripts/python.exe -m apexsim.cli replay-openf1 .cache/openf1-9554 --output .cache/openf1-9554-replay
```

Session 9554 is 2024 British GP qualifying, matching the event/session used in the
FastF1 acquisition gate. All output directories must be new. Downloads require
network access; verification and replay work from local files. The normal test
suite uses synthetic responses and never queries a live provider.

## Endpoint and query contract

The v1 profile freezes the 18 endpoint families documented on 2026-09-16:

- Identity: `sessions`, `meetings`, `drivers`.
- Timing and conditions: `laps`, `stints`, `weather`, `race_control`, `pit`,
  `position`, `intervals`.
- Additional source evidence: `overtakes`, `session_result`, `starting_grid`,
  `team_radio`, `championship_drivers`, `championship_teams`.
- High-volume streams: `car_data`, `location`, queried separately for every driver
  in the source's driver inventory.

The query plan uses a positive integer session key, its resolved meeting key and
sorted driver numbers. It rejects `latest`, live/future sessions and pre-2023
sessions. Meetings use `meeting_key`; all other endpoints use `session_key`.
Telemetry adds `driver_number`. There are `16 + 2 * driver_count` requests.
No time-range truncation, lap filtering, resampling, interpolation, deduplication
or conversion to canonical units occurs. Team-radio URLs are preserved as strings;
the linked audio is not fetched. Outcome/standings fields are evaluation information,
not automatically valid causal model inputs.

The exact session, meeting and driver identities are validated against responses.
At least sessions, meetings, drivers, laps, weather, car data and location must be
nonempty; every driver with lap records must have both telemetry streams. Other
empty responses are recorded explicitly. Empty data does **not** establish that no
real-world pit stop, overtake or other event occurred. Availability and collection
success are separate concepts, and broadcast completeness is not established here.

OpenF1 currently returns HTTP 404 with exactly `{"detail":"No results found."}`
for some empty queries. That response is archived intact and interpreted as zero
rows. A successful empty array also means zero rows. Other HTTP errors, error
objects, invalid JSON, duplicate object keys and non-finite numbers fail acquisition.

## HTTP behaviour

`DownloadPolicy` declares seconds, byte limits and retry counts. The defaults are
2.1 seconds between request starts, four attempts per request, 10-second connection
and 60-second read timeouts, a 64 MiB decompressed response limit and a maximum
60-second retry wait. Requests are sequential and include an APEX user agent.
This stays below the published free-tier limits of 3 requests/second and 30/minute;
other clients sharing the same quota can still cause throttling.

Only timeouts/connection errors, 429 and 5xx are retried. `Retry-After` seconds or HTTP
dates are honoured within the configured bound; a longer request fails rather than
retrying early. Backoff and status/error histories are recorded for successful
requests. Redirects are not followed. Read timeouts apply to socket inactivity, not
a total session wall-time limit. There is no automatic resume of partial archives.

## Archive contract

```text
archive/
  raw/0000.json                 # response body after HTTP decompression, otherwise unchanged
  raw/0000.request.json         # endpoint, query, UTC retrieval time, status, safe headers, attempts
  ...
  tables/<endpoint>.jsonl       # deterministic native-value records, one file per endpoint
  snapshot.json                # identity, driver inventory, table hashes/rows/missingness
  manifest.json                # hashed completion marker, published last
```

`apex-openf1-archive-v1` embeds the existing `apex-source-manifest-v1`, including
licence/terms reference, adapter version, request queries and decoded response hashes.
Its file inventory uses relative paths, byte counts and SHA-256 hashes. It records
Python, APEX and Requests versions and the acquisition policy. Relocation preserves
the archive identity. Hashes detect alteration; they do not authenticate an author.

`apex-openf1-snapshot-v1` records rows, field names, explicit null counts, absent-field
counts, per-driver rows, empty endpoints and JSONL hashes. JSONL avoids coercing mixed
values, nested arrays or source timestamp strings through a dataframe. The original
body bytes preserve the exact JSON numeric spelling; parsed floating-point values in
JSONL use Python's standard JSON number representation. Native units remain unchanged.
Source-supplied values may themselves be reconstructed or approximate, so these files
are not labelled uniformly measured ground truth.

Verification checks the manifest seal, exact file and query inventories, embedded
source lineage, HTTP sidecars, raw payload hashes/counts, identity/driver coverage,
and the equivalence of saved tables to reconstruction from raw responses. It rejects
missing, altered or extra files and paths outside the archive. A failed download
retains partial diagnostic responses without publishing a completion manifest.

## Offline gate

Replay verifies the archive, then launches a fresh Python process. A permanent Python
audit hook denies DNS and socket connect/send calls. The worker rebuilds all tables
from JSON response bodies into a new directory outside the archive. The parent
compares every table hash and the full snapshot, checks zero network attempts, and
re-verifies the original archive. `apex-openf1-replay-v1` reports pass/fail, row counts,
empty endpoints, table mismatches and archive identity. Worker failures/timeouts leave
a log and cannot produce a passing replay report.

The guard covers Python networking, not an OS-wide sandbox. Only JSON is loaded;
there are no pickles or provider cache executables. A change of Python version need
not fail up front: exact reconstruction is the compatibility test. Large sessions
are held in memory during reconstruction and can require substantially more memory
than their compressed HTTP payloads.

## Scope and references

These native tables are separate from the five canonical public Parquet tables and
the retired `ingest-openf1` feature CSV. Use [observed tables](observed-tables.md)
for supported nullable canonical fields; public dense training remains gated.
One-session replay is not a multi-event benchmark or calibration result. The endpoint
profile is versioned; future endpoints require an explicit contract update.

Bulk source data remains under ignored `.cache/`; Git stores only code, synthetic
fixtures and compact verification evidence. OpenF1 describes educational/research
and non-commercial use and links CC BY-NC-SA 4.0. This archive does not grant rights
to redistribute upstream data or use it commercially.

Primary references, checked 2026-09-16:

- [OpenF1 API reference](https://openf1.org/docs/)
- [OpenF1 access limits, use guidance and licence link](https://openf1.org/)
- [Provider implementation](https://github.com/br-g/openf1)
