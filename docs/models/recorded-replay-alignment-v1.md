# R033 recorded replay observations v1

Public parsed-source **ADAPTATION**, research only. See the
[protocol](../../research/protocols/RECORDED_REPLAY_ALIGNMENT.md),
[unit/truth map](../../research/equations/RECORDED_REPLAY_ALIGNMENT_V1.md) and
generated `field_contract.json` for the typed observation boundary.

This layer aligns recorded throttle, boolean brake, DRS and observed speed/RPM/
gear with backward same-lap native position. It retains every source row, source
IDs, rejected association, time gap and nullable unknown field. Offline R029
reference geometry is labelled conditioning; it is not measured chassis state.

**Steering angle, body vx/vy, yaw rate, fuel and battery remain UNKNOWN.** The
complete measured bicycle adapter explicitly abstains. Boolean braking supplies
no calibrated pressure or force, and RPM/gear supply no identified torque/ERS.
The observed-channel coverage gate and full bicycle readiness are reported
separately. This task does not certify autonomous or full-car lap replay.

## Public run on preserved inputs

The exact original four archives and accepted R030 source dataset are required.
All88 R029 laps and150 source-selected R030 sections are inherited unchanged.
No provider cache is unpickled and no networking is needed.

```powershell
python -m apexsim.cli prepare-recorded-replay --longitudinal .cache/r030-native-sections-20261031 --archives .cache/fastf1-2024-r1-race-20261011 --archives .cache/fastf1-2024-r16-race-20261011 --archives .cache/r026-fastf1-2023-r1-race-20261013 --archives .cache/r026-fastf1-2023-r14-race-20261013 --output .cache/recorded-replay-new
python -m apexsim.cli verify-recorded-replay .cache/recorded-replay-new
python -m apexsim.cli audit-recorded-replay .cache/recorded-replay-new
```

Use fresh output paths. The portable package contains the unchanged source-bound
R030 dataset, exact original native position tables, source headers, per-lap
aligned Parquet frames, all longitudinal input bundles, field semantics, code/
protocol snapshots, environment and commit metadata, and sealed results/inventory.
Every source event is guarded before binary access. Nine permanent benchmark
events remain excluded; these four events were already used in development.

Verification reconstructs every row association and coverage result from the
sealed native tables, checks input bundles, and compares aligned frames with
atol1e-9. Exact stored-byte integrity is checked separately. Independent audit
uses a backward pointer and direct conversions, not the primary join algorithm.

## Fresh-checkout execution fixture

```powershell
python -m apexsim.cli recorded-replay-smoke --output .cache/replay-smoke-new
python -m apexsim.cli verify-recorded-replay .cache/replay-smoke-new
python -m apexsim.cli audit-recorded-replay .cache/replay-smoke-new
```

Smoke is visibly simulated and cannot close public R033 or replace its native
source provenance. CI tests it on Python3.11/3.12. Public predictive errors remain
R034; braking/cornering calibration and complete state initialization need later
evidence. No production model/state is overwritten. Rollback is to stop consuming
this versioned research package; prior studies remain available.
