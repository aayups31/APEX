# FastF1 session archives and offline reconstruction

P1-03 freezes a complete session's FastF1 HTTP and parser caches, exports its native
tables, and proves that a fresh process can reproduce those tables without networking.
The initial real-data acceptance case is 2024 round 12 (British GP), qualifying.

## Commands

Run from the repository root with the existing Python 3.12 environment:

```powershell
uv pip install --python .venv/Scripts/python.exe -e './apex_engine[dev,real-data]'
.venv/Scripts/python.exe -m apexsim.cli download-fastf1 --year 2024 --round-number 12 --session Q --output .cache/british-2024-q
.venv/Scripts/python.exe -m apexsim.cli verify-fastf1 .cache/british-2024-q
.venv/Scripts/python.exe -m apexsim.cli replay-fastf1 .cache/british-2024-q --output .cache/british-2024-q-replay
```

Use `.venv/bin/python` on POSIX. Every output directory must be new. Full-session
acquisition can take several minutes; progress and upstream warnings are written to
`worker.log`. A timed-out or failed worker leaves an incomplete directory for inspection,
without a completion manifest. It cannot be silently reused as a completed archive.

An exact year/round/session selects the event without fuzzy name matching. Supported
codes are FP1, FP2, FP3, Q, R, S, SQ and SS when that session exists for the event.
Historical support and complete streams are required; the downloader fails rather
than substituting missing weather, driver telemetry or race-control streams.

## Archive contents

```text
archive/
  cache/                         # isolated FastF1 HTTP + parsed-cache files
  tables/
    laps.parquet
    weather_data.parquet
    race_control_messages.parquet
    track_status.parquet
    session_status.parquet
    results.parquet
    car_data/<driver-number>.parquet
    pos_data/<driver-number>.parquet
  snapshot.json                  # table hashes, row counts, columns, missingness
  worker.log                     # operational log, not an identity input
  manifest.json                  # completion marker, written last
```

Schema versions are `apex-fastf1-archive-v1`, `apex-fastf1-snapshot-v1` and
`apex-fastf1-replay-v1`. The archive manifest records the exact query, resolved
session identity, access time, documentation/terms reference, APEX adapter version,
Python/FastF1/Pandas/NumPy/PyArrow versions, and every persisted cache/table file's
relative path, byte count and SHA-256. It embeds the existing source-manifest format
for logical `get_session` and `Session.load` calls. Low-level HTTP responses remain
inside FastF1's SQLite cache; this module does not claim to enumerate every HTTP call
as a separate manifest request. Parser-cache files contain upstream reconstructed data.

All six shared tables and both car/location streams for each returned driver must be
nonempty. Every driver appearing in lap data must have car and location streams.
This is a structural completeness test, not a claim that every expected sample was
broadcast or every source value is reliable.

Verification reads hashes and Parquet metadata, checks the exact cache/table inventory
and session identity, and rejects changed/missing/unlisted files or unsafe paths.
It does not unpickle cache data or contact the network. Paths are relative, so a bundle
can be relocated without changing its identity.

## Offline gate

Replay verifies the archive before using any cache data and requires the recorded
Python and core dependency versions. It copies the cache to a fresh output directory
outside the archive, then starts a new worker. That worker enables FastF1's cached-only
mode and installs a Python audit hook that rejects DNS/socket connection and send
attempts. An attempted request fails the run even if FastF1 swallows the exception.
This guards the Python HTTP path used by FastF1; it is not an OS-level network sandbox.

Every reconstructed table must have the same serialized Parquet SHA-256, row count,
column list and null counts. Session identity must agree. The report records mismatched
table names, network-attempt count and pass/fail. The original archive is verified
again after replay to ensure its cache has not been altered.

Tests exercise serialization with synthetic provider-shaped frames, relocation,
missingness and nanosecond preservation, tampering, added files, unsafe paths,
version mismatch, partial loads, worker timeouts, wrong sessions and changed replay
values. A child-process test actually attempts DNS and a localhost socket connection
and verifies both are denied. Normal CI does not contact live data services.

## Source semantics and limitations

The Parquet exports preserve **native FastF1 fields, units, timestamps and missingness**.
APEX performs no resampling, filling, calibration or driver filtering here. The
`t0_date` identity field preserves FastF1's naive-UTC representation; session-relative
times are anchored to it, and `session_start_time_s` records the offset to the session
start. Native timestamps retain nanoseconds where present.

These are not yet the five `apex-public-tables-v1` canonical tables or the old dense
model-feature CSV. Canonical unit/time mapping, field-level truth labels, alignment
reports and placeholder removal remain subsequent ingestion gates. Session results
are outcome/evaluation information and must not become causal model inputs.

FastF1 can correct, interpolate or generate values internally. The live reference load
reported a correction to driver 18's tyre-stint information. The archive labels its
tables as parsed source data containing upstream reconstructions, never uniformly
MEASURED ground truth. Preserve and inspect the log for source-specific warnings.

Replay loads FastF1's pickle-based parser cache: use only trusted locally acquired
archives. Hashes detect alteration but do not authenticate arbitrary downloaded
archives or make untrusted pickle safe. Core-version mismatch requires the recorded
environment or a separately documented new acquisition; version checks are not disabled.

Bulk cache, telemetry and native tables stay in ignored `.cache` directories. Only
compact manifests/reports and synthetic fixtures belong in Git. Source rights and
redistribution suitability need separate review before publishing real data.

This gate establishes reproducible acquisition for one historical session. It does
not establish a frozen multi-event benchmark, historical accuracy of the simulator,
general support for all sessions, or R2 maturity.

References: [FastF1 cache implementation](https://github.com/theOehrly/Fast-F1/blob/main/fastf1/req.py),
[FastF1 documentation](https://docs.fastf1.dev/).
