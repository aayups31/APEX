# R030 longitudinal power/drag calibration v1

Preregistered2026-10-31 before fitting public acceleration/drag coefficients or
inspecting their validation/test errors. Classification: physics-guided public
**ADAPTATION**, research only. No production or R2/R3 maturity promotion.

## A. Current state and baseline

Baseline ff5832ba48d95b30e4779a57c87ba054bbc91aa5:582 tests pass in470.06s,
two existing dependency deprecations. Accepted R029 public geometry replays with
seal `e22c1c6e0bf35a195120e47e6198c02d38549af4d51d38ef9f400c125d4ba684`;
its inventory seal is
`0caa4285294656c9d223ae4c79348c7f0990ff117c04e6f026947e4d0b7d0162`.
Existing synthetic longitudinal reference runs on525 rows (MAE.225624m/s2),
but its reported error is in-sample. Research foundation R1/kernel R0 remain.

## B. Scope

R030: fit effective specific-power/drag coefficients and test scalar speed
replay on high-speed, full-throttle, low-curvature sections. This is the first
calibrated longitudinal slice; braking forces, partial-throttle transients,
low-speed traction, lateral dynamics, full-lap state/control alignment and
closed-loop driving remain outside it. R031/R033 and later rows retain their gates.
No UI, neural residual or production parameter update. Do not map effective
coefficients to claimed measured engine power, mass, CdA or ERS deployment.

## C. Frozen inputs and source truth

Use all88 laps already frozen in R029 v3, without replacement. Reassign roles for
this separate experiment by **whole event**, never timestamp or within-event:

| Role | Events | R029 source laps |
|---|---|---:|
| Training |2023 Bahrain R01 and Monza R14|48|
| Validation |2024 Bahrain R01|20|
| Test |2024 Monza R16|20|

There is one final test event with two drivers; bootstrap uncertainty conditions
on that event, not a population of races. Both circuits occur in training. All
events/telemetry were previously used in development; this is not an untouched
benchmark. The nine permanent whole-event reservations remain protected before
any native payload read. No new acquisition is needed.

Bind the four original native archive seals from R029:

-2024R01 `19dae940473544324bd0a2562041698fc37c6cf1c85b9f6a7e767210e60cfd50`
-2024R16 `68310c905912847366d4e0aaca28d68985415c7b5a6bac754fc4c6b7c3657c7e`
-2023R01 `5fa8533257e7684df72616e776833a79b78160c0dc1188dbde41ef3158aa96dc`
-2023R14 `bdad18d4461d1d8d6b0e5dec0d9dcdbd0c214441ca3ca392f70ccd8c2ee19181`

Native car Speed converts km/h to m/s, Throttle percent to[0,1], Brake remains
boolean. Require Source=car and finite strictly increasing SessionTime; check
Date differences agree within1e-6s. Do not use the provider's inaccurate relative
Time channel. No future control or speed enters initial state estimation.

FastF1's own source documents DRS10/12/14 as on,0/1 as off,8 as eligible (closed),
with other distinctions uncertain:
<https://github.com/theOehrly/Fast-F1/blob/main/fastf1/_api.py>.
Treat {0,1,8} as closed and {10,12,14} as open, reject other/missing codes.
The recorded indicator is not a surveyed activation-zone map.

Speed/control channels are public parsed-source observations with upstream
reconstruction possible. Target acceleration is RECONSTRUCTED forward speed
difference, not an accelerometer. Geometry is RECONSTRUCTED_REFERENCE_TRACE;
mass, air density and rolling loss are PRIOR. Wind, grade, fuel mass, hybrid
deployment, wheel forces and exact drivetrain state are UNKNOWN.

### Source-only section extraction

For each frozen lap, use native car samples within its timing bounds. Geometry
comes from R029's **already frozen offline registered shape**; its pose used full
position laps and is not claimed to be online causal localization. At car time,
use only the latest saved native position (not reconstructed timing anchors),
lag<=.35s, previous position interval<=.75s, projection distance<=15m and
|reference curvature|<=.001/m. Conditioning on this supplied geometry/section
membership is explicit; no speed error determines inclusion or registration.

Require speed[40,105]m/s, throttle[.98,1], Brake=false, known DRS code. Native car
intervals must be positive and<=.5s. Form uninterrupted runs of constant DRS state;
do not bridge rejected samples, laps, identities or gaps. Split runs into
approximately3s sections (first native endpoint reaching3s), retaining a final
tail only if>=2s. Consecutive sections may share one boundary observation but
no interval. Each start needs five causal native speed samples in the same lap,
span[.4,2]s and gaps<=.5s; ordinary least-squares slope supplies the constant-
acceleration baseline's initial value. Preserve exact source row/time/geometry
parents, accepted/rejected counts and every rejection reason.

Freeze the complete source-preflight manifest and section identities before
coefficient fitting. Do not remove high-error sections or substitute laps.

## D. Equations, fitting and interfaces

Add research modules, sealed dataset/study runners, CLI, hand/equation tests,
independent audit, component card and evidence. Preserve existing sim_core APIs.

The specific longitudinal model is
`dv/dt = p*u/v - d_open*v^2 - d_extra*(1-z)*v^2 - r`,
where p=P_eff/m [m2/s3=W/kg], d [1/m], z is recorded DRS-open, u throttle[0,1].
`r=.015*9.81=.14715m/s2` is the existing rolling-loss PRIOR. It is not identified
without additional coast/engine-braking evidence. Grade/wind/ERS are unresolved
effective confounders. Restriction to high speed/low curvature supports the
power-limited point-mass approximation but does not establish actual no-slip.

Fit separate track/driver cells using **training events only**. Two preregistered
candidate classes: shared drag (p,d; ignore z) and DRS drag (p,d_open,d_extra).
For native intervals, fit speed increments using left-endpoint causal features
`dt*[u/v,-v^2,-(1-z)*v^2]` and target `delta_v+r*dt`. Shared drag omits column3.
This Euler identification approximation is disclosed; replay uses RK4.
Scale columns by training RMS, then bounded least squares, no target clipping:
p in[100,2000], each drag coefficient in[0,.005]. Nonnegative d_extra imposes
closed>=open as a declared structural prior. Report active bounds and do not call
a boundary coefficient independently identified. Require>=100 training intervals
and>=5 distinct laps per fitted cell, normalized design full rank and condition
number<=1e4. An unavailable/rank-deficient class is ineligible, never silently
substituted or fitted on validation/test. Report singular values and residuals.
The SciPy bounded linear solver's contract is documented at
<https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.lsq_linear.html>.

Replay from each observed initial speed with recorded controls held left on each
native interval, RK4 maximum step.05s; no later observed speed resets. This is a
conditional recorded-control section replay, not a future-control forecast.
Reject nonfinite/nonpositive speed or speed>120m/s; no clipping/soft speed limiter.
Select the candidate class with lowest equal-driver/lap validation speed RMSE;
deterministic tie break shared drag. No refitting on validation or test.

Matched baselines: constant speed; constant causal acceleration; uncalibrated
power/drag PRIOR from CarParameters740kW*.92/900kg, CdA1.05m2, rho1.225kg/m3,
DRS reduction.16 and r above; the existing Huber diagnostic regression fitted
per cell on the same training intervals. Use raw legacy coefficients without
its absolute-value/clipped production mapping. All receive the same recorded
section inputs; no target-derived initial acceleration or teacher forcing.

Report speed MAE/RMSE, endpoint error, integrated distance error, by driver/lap,
DRS state, speed band and section duration. Primary aggregation: average interval
speed squared errors within section, sections within lap, laps within driver,
then drivers equally. Also retain frame-weighted errors. Training-only200
lap-cluster bootstrap coefficient fits (seed3030) give descriptive parameter and
prediction intervals; disclose failed/boundary bootstrap fits and empirical
test coverage, not assumed calibrated confidence. Compare selected coefficients
with fixed rolling prior +/-50% as identifiability sensitivity, not reselection.

## E. Acceptance and stopping gate

- All source identities, hashes, units, sequence/gap/geometry/control checks pass.
  Each driver contributes>=5 test laps and>=10 test sections; all four training
  track/driver cells meet the selected class's support/conditioning requirements.
- Primary test RMSE at least5% lower than **each** matched baseline. Paired
  500-resample test-lap bootstrap95% upper bound on selected-minus-best-baseline
  MSE <0 (drivers fixed, seed3030). The best baseline is the best test aggregate
  among the frozen baseline set, not a newly tuned model. Each driver must also
  beat constant speed and the uncalibrated physical prior individually.
- No integration failures; max .05s vs .025s RK4 speed difference<=.002m/s.
- Hand force balance, units, analytic derivatives vs finite differences,
  drag/power direction, DRS prior inequality, exact constant-acceleration limit,
  timestep convergence, noiseless coefficient recovery and rank deficiency tests.
- Event split/target independence, unknown DRS, gaps/causal warmup, source guards,
  immutable/portable artifacts, false resealing and scientific replay tests.
- Independent coefficient/equation/section-score audit; portable replay refits
  training, reproduces validation selection, all predictions/intervals/decisions.
  Numeric tolerance rtol1e-6/atol1e-7. Full suite/lint and Python3.11/3.12 CI pass.

Only passing public evidence closes R030. Source failure or held-out failure is
preserved and reported as INCONCLUSIVE/REJECTED; do not relax gates or alter this
cohort to force DONE. No formal maturity or production promotion follows.

## F. Risks

Partial identifiability: effective parameters mix engine/ERS/mass, road slope,
wind and setup. DRS coding and boolean braking are limited; restrict the scope.
Short straight sections and one test event limit transfer claims. R029's offline
registered positions are supplied geometry, not a validated online localization
system. Speed quantization and finite-difference identification can bias fitted
coefficients. Preserve failed regimes, prior sensitivity and uncertainty coverage.

## G. Execution order

1. Push this preregistration and mark R030 IN_PROGRESS.
2. Implement/test native source extraction and freeze the source preflight.
3. Implement/test constrained equations, fitting, baselines and integration.
4. Freeze fitted training candidates and validation decision; push checkpoint.
5. Evaluate held-out Monza with unchanged models; retain all source-selected cases.
6. Replay/audit, run regression/CI, publish evidence and exact limitations.
7. Close only if gates pass; next normal dependency is R031.
