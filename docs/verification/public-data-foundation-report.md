# Public-data foundation verification

- Date: 2026-09-07 (America/Toronto; artifact UTC timestamps fall on September 8)
- Branch: `codex/public-data-foundation`
- Parent milestone: `963388c`, `codex/foundation-platform-v1`
- Scope: P1-01, P1-08
- Maturity before/after: R0; no physics or research model promotion
- [Machine-readable evidence](public-data-foundation-evidence.json)
- [Contract and reproducible commands](../data/public-tables.md)
- [Architecture decision](../architecture/adr-0002-public-evidence-tables.md)

## Recovered context and baseline

The shared history identified the foundation/API/UI milestone at `963388c`. The
Windows workspace started at `68b7221` on main. Fetched origin and created this branch
from the pushed foundation milestone, preserving its work rather than rebuilding it.
The later installation edits shown in the shared history were not on that remote head.

Created an ignored root `.venv` with Python 3.12.12 using uv and installed the project
with dev/real-data dependencies. Baseline Ruff passed and all 40 tests passed in
93.86 seconds. Both race and research reference commands completed; artifacts were
read and inspected under `.cache/p1-baseline`.

The two-lap, seed-123 race had six finishers, 1,872 telemetry rows and no invariant
violations. The research demo produced 22 paper records, an eight-lap adapted
strategy, 420 training/140 test tyre-energy windows and 20 latent-state rows. Its
Ridge proxy RMSE was 0.0554717448; this is synthetic research output, not measured
tyre-energy validation. The reference fit emitted an ill-conditioned-matrix warning.

## Completed

P1-01: Five typed Parquet schemas now validate session, lap, stint, weather and
race-control evidence. Versioned metadata preserves units, primary keys and UTC
precision; explicit nullable fields and per-value truth labels preserve missingness.
Validation rejects lossy types, nonfinite values, duplicates, invalid references,
overlapping stints, unsupported compounds and conflicting lap/stint compounds.

Portable dataset bundles verify source manifests and raw-file hashes on creation,
record source snapshots and Parquet hashes, and publish a completion manifest last.
Readers reject altered files, altered snapshots, incomplete bundles, changed schema
metadata or mismatched lineage. No completed artifact is silently overwritten.

P1-08: Explicit split manifests bind train/val/test assignments to exact dataset
and session-table hashes. All sessions appear exactly once, with no empty partition,
event overlap, known season/round overlap or duplicate source-session aliases. The
pipeline can consume these frozen partitions, checks exact telemetry-session coverage,
copies the split evidence into the run and fits the standardizer only on train data.

CLI commands: `public-data-demo`, `validate-public-data`, and `freeze-splits`.
CI and root Makefile install the data-contracts extra. A frozen machine-readable
schema catalog and regression check guard accidental version-one schema drift.

## Final verification

```powershell
.venv/Scripts/python.exe -m ruff check apex_engine/src apex_engine/tests
cd apex_engine
../.venv/Scripts/python.exe -m pytest -q
cd ..
.venv/Scripts/python.exe -m py_compile apex_engine/dags/apexsim_dag.py
.venv/Scripts/python.exe -m apexsim.cli public-data-demo --output .cache/p1-final-evidence
git diff --check
```

- Full local suite: **84 passed**, four upstream/legacy deprecation warnings,
  87.99 seconds on Windows/Python 3.12.12. No new warning category versus baseline.
- Ruff, Airflow wrapper compilation and diff whitespace checks passed.
- Existing deterministic race, API and model-pipeline regression tests passed.
- New tests include Parquet round trips, missingness, unit/schema drift, UTC precision,
  invalid keys and values, incomplete bundles, source/file/manifest tampering,
  relocation, overwrite refusal, event aliases, wrong datasets, partition coverage
  and a train-only-scaler test with extreme holdout values.
- Inspected reopened final bundle: six sessions, twelve laps, six stints, six weather
  observations and six race-control messages. Both wind fields remain null/UNKNOWN
  in all six rows. Two sessions belong to each partition, grouped by entire event.
- Dataset content hash:
  `c47eff1fd9f64321568085f375796f023ba437df7fa9ca618592f20a4aa4932d`.
- Split content hash:
  `2ebc4f45aa936cada2ab1cadf9a66b8d57740599a2be9847c6858068b98ef7fc`.

The reference source manifest records retrieval time, so a new fixture invocation
gets a new dataset identity. Re-freezing identical assignments against the **same**
dataset produces byte-identical split manifests.

The existing platform was also exercised through the browser at localhost:8000:
submitted three laps with seed 42, observed COMPLETED/VALIDATED, inspected all six
standings rows, rendered track and speed trace, and opened the populated provenance
dialog. Run ID: `race-20260908T014646Z-a6095533`. This is a desktop visual smoke test,
not a complete responsive or accessibility audit. Its 14.77-second displayed runtime
was measured during concurrent tests and is not a performance benchmark.

## Remaining limits and next work

Eight of 66 build-backlog rows are now DONE (P0-01 through P0-05, P1-01, P1-02,
P1-08). No real historical corpus was downloaded or frozen by this slice.

1. P1-03: capture the FastF1 raw cache and prove a session rebuilds offline.
2. P1-04: persist all required OpenF1 raw endpoint responses, queries, hashes and
   row counts; prove offline replay and connect observations to these table schemas.
3. P1-05: add paginated Jolpica event metadata and harmonize provider identities.
4. P1-06: produce temporal alignment reports with join coverage, tolerances and gaps.
5. P1-07: replace legacy adapter placeholder fields with observed, reconstructed
   or explicitly unknown values. Then freeze a real evaluation corpus using P1-08.
6. Close remaining P1 gates before P2 track reconstruction and P3 physics calibration.
   R012-R014 equation-fidelity and exact-oracle research prerequisites remain open.

The old dense model-feature CSV remains a separate interface and retains its legacy
behavior without the optional frozen-split configuration. Table-schema validity does
not establish source completeness, correct event identity, calibration or predictive
accuracy. Hashes detect alteration, not forgery. Raw snapshots remain a separate
future acquisition/replay gate; the platform is still the R0 local preview service.

To run the platform on this Windows checkout:

```powershell
.venv/Scripts/python.exe -m apexsim.cli api --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000`. Use Ctrl+C to stop the server.
