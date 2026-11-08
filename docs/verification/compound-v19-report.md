# R041 driving-state review

R041 remains IN_PROGRESS. The latest experiment has a source-access limitation
and fails prediction acceptance. Foundation R1, production R0 and the R042
dependency apply.

## Changes and results

The adapter now associates observed throttle, brake, speed and DRS with the
current prefix and two completed reference windows. It integrates only adjacent
valid native samples at most one second apart. All three laps need at least
90% joint time coverage. Invalid intervals, endpoint gaps and missing sources
remain visible. The 23 new model inputs supplement the v17 practice inputs.
The complete evaluation race is excluded from calibration.

| Registered procedure | Passing supported races | Macro both-label MAE |
|---|---:|---:|
| V17 practice control | 11/24 | 0.423670 s |
| V19 partial driving-state diagnostic | 10/24 | 0.433515 s |

All 91 FastF1 comparisons have coverage on all nine known laps. Driving inputs
remain unavailable for 301 OpenF1 comparisons. All 392 cases and 28 sources
remain in the evaluation. V19 gains Abu Dhabi 2025 and loses Bahrain and
Australia 2024 relative to the control. Adding the available driving
observations does not establish improved transfer.

The missing-input indicators also identify the provider/season distribution.
The full-data hypothesis remains untested. These results cannot support
prospective acquisition or R041 completion.

## Source access

OpenF1 returned HTTP 401 with a global live-session restriction, including
historical data. The exact body and sealed request receipt are preserved in
the acquisition cache. A separate FastF1 archive attempt failed to load its
source tables, and its historical SessionInfo request also returned HTTP 401.
The [access receipt](compound-v19-access-review.json) binds the recorded evidence.

No authenticated credentials or paid access were available to these requests.
The offline diagnostic uses the nine existing verified FastF1 archives.
It records acquisition_ready=false. Even a prediction pass would require
completion of the planned acquisition before development qualification.

## Earlier-work audit

The independent review confirms that v12 intentionally requires the original
scalar reference baseline as well as each label's own reference baseline.
Race exclusion, training-only scaling and unique-window weighting are
consistent. A hindsight existence diagnostic demonstrates that the two-second
forecast bound permits all race gates to pass. This diagnostic uses observed
outcomes and supplies no model validation.

The previous CI receipt was missing from project metadata. It is now sealed at
[v18 final CI](compound-v18-final-ci.json), with 849 passing tests on both
Python versions and all workflow steps successful.

## Verification and reproduction

Twelve new regressions cover time integration, gaps, future observations,
clock ordering, units, provider identity, missing inputs and raw HTTP snapshot
integrity. The independent v19 auditor verifies 9,016 driving feature values,
392 checkpoint forecasts and all 48 supported event-label gates. Its scope is
stored summaries, feature arithmetic, inference and gate reconstruction.
The separate offline inventory establishes native FastF1 coverage.

From the repository root, choose fresh output paths.

```text
python research/scripts/compound_driving_data.py --offline-partial --snapshots .cache/r041-v19-car-snapshots --output <fresh-driving-data>
python research/scripts/diagnose_compound_driving.py --output <fresh-result>
python research/scripts/audit_compound_driving.py --output <fresh-audit>
```

The model and audit use the committed driving-data path. Compare a new
extraction to that file before evaluating its forecasts. An exact same-machine
model refit and native extraction replay are recorded in the final review.
CI executes the independent audit, full test matrix, distribution builds and
the existing simulator verification.

## Next required action

Retry the registered historical acquisition after access becomes available,
using a fresh snapshot directory because the saved rejection is immutable.
The adapter preserves original HTTP bytes and verifies them on reload.
Complete coverage auditing before rescoring the registered candidate. If
prediction acceptance still fails, record the failure and diagnose whether
driving behaviour transfers across races before proposing another model.
R041 requires a development pass and a separately frozen prospective
confirmation. R042 remains downstream.
