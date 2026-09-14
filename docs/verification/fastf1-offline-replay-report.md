# FastF1 acquisition and offline replay verification

- Date: 2026-09-14
- Branch: `codex/fastf1-offline-replay`
- Parent: `3d58be0` (merged public-data foundation)
- Backlog: P1-03, DONE
- Maturity before/after: R0; no simulator calibration or model promotion
- [Machine-readable evidence](fastf1-offline-replay-evidence.json)
- [Usage, artifact contract and limitations](../data/fastf1-archives.md)

## Baseline and scope

The previous milestone was merged through PR #1. This branch starts from that
merged main revision. The source tree matched the previously verified milestone.
Baseline: all 84 tests passed in 90.87 seconds; Ruff passed; the public-data fixture
wrote and reopened its five-table bundle with valid event-grouped splits.

The selected slice was P1-03: one complete session must rebuild from its frozen
FastF1 cache without contacting the network. P1-02 source lineage was already closed.
P1-04 multi-endpoint OpenF1 acquisition remains the next dependency.

## Delivered

- `download-fastf1`: exact season/round/session selection, isolated cache, full
  native source-table exports, file hashes, versions and immutable completion manifest.
- `verify-fastf1`: portable archive verification without network or pickle loading.
- `replay-fastf1`: fresh-process reconstruction from a private cache copy using
  cached-only HTTP plus a Python network audit guard, followed by table-hash comparison.
- Strict failures for incomplete streams, missing driver data, wrong sessions,
  unsupported query values, changed versions, file tampering, unsafe paths, unlisted
  cache files, output reuse, worker failure and timeouts.
- Native columns, units, nanosecond timestamps and nulls survive serialization;
  no APEX resampling, feature filling or calibration occurs in this slice.

## Real-session acceptance evidence

Downloaded 2024 round 12, British Grand Prix qualifying, and rebuilt it offline.

| Measurement | Result |
|---|---:|
| Drivers | 20 |
| Exported tables | 46 |
| Lap records | 368 |
| Car-data rows | 385,580 |
| Position rows | 393,300 |
| Weather observations | 85 |
| Race-control messages | 46 |
| Result rows | 20 |
| Session-status rows | 14 |
| Track-status rows | 4 |
| Total exported rows | 779,417 |
| Preserved cache files | 11 |
| Manifest-covered files | 58 |
| Manifest-covered bytes | 74,163,966 |
| Offline network attempts | **0** |
| Mismatched reconstructed tables | **0** |

All 46 reconstructed Parquet files matched their original SHA-256 hashes, row
counts, columns and null-count metadata. Session identity matched, and re-verifying
the original archive after replay confirmed that its frozen cache remained unchanged.

- Archive SHA-256: `cab9254b9499b7adf819f550766204e9170179ac81dd05cc6b6ebc40532a0f56`
- Replay-report SHA-256: `ab5da1556764d7888e788114ea8150783d4389ffb40f341f1d0c5ae4e3cb33bb`
- Environment: Python 3.12.12, FastF1 3.8.3, pandas 2.3.3, NumPy 2.5.3, PyArrow 25.0.1.

FastF1 logged a correction to driver 18's tyre-stint information. These exports
therefore remain labelled as parsed source data with upstream reconstructions;
they are not uniformly measured ground truth. An initial acquisition exposed a
Python-timedelta serialization incompatibility. It failed without publishing a
manifest; the corrected acquisition and its separate offline replay are the evidence
reported here. Partial diagnostic data remains ignored locally.

## Reproducible verification

```powershell
.venv/Scripts/python.exe -m apexsim.cli download-fastf1 --year 2024 --round-number 12 --session Q --output .cache/fastf1-2024-r12-q-v2
.venv/Scripts/python.exe -m apexsim.cli replay-fastf1 .cache/fastf1-2024-r12-q-v2 --output .cache/fastf1-2024-r12-q-offline
.venv/Scripts/python.exe -m apexsim.cli verify-fastf1 .cache/fastf1-2024-r12-q-v2
.venv/Scripts/python.exe -m ruff check apex_engine/src apex_engine/tests
cd apex_engine
../.venv/Scripts/python.exe -m pytest -q
```

Choose new directories when repeating acquisition/replay. Compact reports and
cache hashes are tracked in Git; the actual source cache and telemetry remain in
ignored `.cache` directories.

Final local suite: **109 passed**, four existing dependency/legacy deprecation
warnings, 83.83 seconds. The 25 new cases include native serialization, nanosecond
and null preservation, relocation, overwrite refusal, tampering and path containment,
changed environments, incomplete/wrong sessions, changed replay values, timeout/failure
handling, CLI integration and actual DNS/socket denial in a child process. Normal
CI uses simulated source frames and makes no requests to historical data providers.
Ruff, Airflow-wrapper compilation and whitespace checks passed.

## Limits and next work

P1-03 is complete; **9 of 66 build-backlog rows** are now DONE. This is one-session
acquisition/reconstruction evidence, not a multi-event benchmark or proof of
simulator accuracy. The cache includes FastF1's pickle-based parser artifacts:
offline reconstruction is for trusted locally acquired archives only. Hashes are
integrity checks, not signatures. The network guard protects Python networking,
not arbitrary native subprocesses or an OS-wide network policy.

Next build sequence:

1. **P1-04:** persist OpenF1 endpoint payloads, queries, hashes and row counts;
   verify offline reconstruction and source completeness.
2. **P1-05:** paginated Jolpica metadata and consistent provider/event identities.
3. **P1-06:** map native inputs into the canonical tables and report temporal join
   coverage, tolerances and missing gaps.
4. **P1-07:** remove legacy weather/compound/pit placeholders, preserving field-level
   observed/reconstructed/unknown labels.
5. Freeze a real multi-event split using P1-08; then advance to P2 track reconstruction
   and P3 single-car calibration. Research prerequisites R012-R014 remain open.

The existing simulation engine, neural experiments, API and web platform continue
to pass their regression tests. This slice does not feed unaligned native data
directly into those models or claim progress on their later scientific gates.
