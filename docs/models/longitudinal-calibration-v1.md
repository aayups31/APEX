# R030 high-speed longitudinal calibration v1

Research component; **ADAPTATION**, no production promotion. See the
[protocol](../../research/protocols/LONGITUDINAL_CALIBRATION.md),
[equation map](../../research/equations/LONGITUDINAL_CALIBRATION_V1.md) and
[acceptance report](../verification/longitudinal-calibration-report.md).

This component fits effective specific-power/drag ratios from native public car
data and replays supplied recorded controls over short sections. The accepted
domain is40–105m/s, throttle98–100%, no recorded braking, low reconstructed
curvature, qualified native timestamps/positions, and supported DRS codes.
`LongitudinalSection` enforces the managed replay domain. Calling the algebraic
power/drag law directly outside that domain is unvalidated extrapolation.

Training:2023 Bahrain/Monza. Validation:2024 Bahrain. Final test:2024 Monza,
33 sections across18 source-qualified laps/two drivers. All88 original geometry
laps remain in the source accounting; source-only filters determine section
membership before fitting, with no outcome-based replacement. The input geometry
is R029's frozen **offline registered reference trace**, not an online location
estimate or surveyed road. These are reused development events, not a permanent
benchmark or unseen-circuit claim.

The fitted law is `a=p*u/v-d*v2-r` for the selected shared-drag class, separately
per track/driver. Bounds, scale/rank/condition diagnostics, active constraints and
training-only bootstrap fits are retained. The DRS-specific class is ineligible:
one training cell has no DRS-open samples. No missing effect is imputed. The
selected model therefore does **not** identify a DRS causal drag reduction.

The coefficients describe conditional effective ratios. Actual engine/ERS power,
mass, wind, gradient, drivetrain losses and aerodynamic CdA are not separated.
Rolling loss stays a declared PRIOR. There is no write-back to CarParameters or
the production simulator. Braking, low-speed traction, partial-throttle dynamics,
lateral dynamics, full-lap alignment and closed-loop driving need later gates.

Held-out speed RMSE is1.110m/s versus1.918m/s for the strongest matched baseline
(42.1% reduction), with both drivers improving. This does not establish real-car
intervention validity. Parameter-only95% bootstrap bands cover35.0% of observed
test speed nodes; they are **not calibrated prediction intervals**. Eleven test
starts fall outside the respective training speed ranges and remain reported.

## Public replay on the preserved inputs

Install the existing APEX real-data/development environment. Set CPU thread
variables to1 as in the other public studies. From the checkout, use fresh outputs:

```powershell
python -m apexsim.cli prepare-longitudinal-dataset --geometry .cache/r029-v3-research-20261020 --archives .cache/fastf1-2024-r1-race-20261011 --archives .cache/fastf1-2024-r16-race-20261011 --archives .cache/r026-fastf1-2023-r1-race-20261013 --archives .cache/r026-fastf1-2023-r14-race-20261013 --output .cache/longitudinal-source-new
python -m apexsim.cli verify-longitudinal-dataset .cache/longitudinal-source-new
python -m apexsim.cli fit-longitudinal-calibration --dataset .cache/longitudinal-source-new --output .cache/longitudinal-development-new
python -m apexsim.cli verify-longitudinal-development .cache/longitudinal-development-new
```

Freeze/preserve the training/validation checkpoint before any test evaluation:

```powershell
python -m apexsim.cli evaluate-longitudinal-calibration --development .cache/longitudinal-development-new --output .cache/longitudinal-test-new
python -m apexsim.cli verify-longitudinal-calibration .cache/longitudinal-test-new
python -m apexsim.cli audit-longitudinal-calibration .cache/longitudinal-test-new
```

The dataset contains copied native car/lap Parquet tables, original archive
manifests, sealed geometry, every rejected row and exact section/warmup lineage.
Native provider caches are verified on acquisition/preparation but are not copied
into the portable package. Verification reconstructs section membership from
those sealed tables, refits training, reproduces validation selection and all
held-out predictions/metrics/intervals/gates. Independent audit checks optimality
and uses DOP853 instead of the replay engine's RK4 integrator.

Bulk source/parameter draws and raw arrays remain ignored locally. Compact
source/cohort/model/evaluation evidence and inventory seals are versioned in Git.
Public replay requires the preserved source artifacts; a new arbitrary refit
cannot silently replace the fixed geometry/native sources.

## Fresh-checkout execution fixture

```powershell
python -m apexsim.cli longitudinal-calibration-smoke --output .cache/longitudinal-smoke-new
python -m apexsim.cli audit-longitudinal-calibration .cache/longitudinal-smoke-new
```

Smoke generates visibly SIMULATED independent sections and cannot close public
R030 or claim native full-lap provenance. CI exercises fitting, checkpoint freeze,
held-out execution, scientific replay, source guards and independent audit on
Python3.11/3.12. No confidential data, game telemetry or GPU is required.
