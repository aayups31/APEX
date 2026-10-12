# R021/R022 fuel-corrected latent tyre pace and hierarchical prediction

Preregistered 2026-10-11, baseline 1f77156; 450 tests pass, two existing warnings,
127.44 s. Scoped research R1/kernel R0. R020 benchmark policy remains mandatory.
Source: Cappello/Hoegh arXiv:2512.00640v1 (2025-11-29), abstract only;
current Kalman starter and public archive contracts. The Gaussian equations below
are independently specified for this adaptation, not verified paper equations.
This is a declared Gaussian-state adaptation and a new multi-group extension,
not replication of the paper's Austrian/Hamilton/skewed-t case or measured wear.

## Frozen data and exclusions

Acquire full FastF1 race archives for 2024 rounds 1,3,6,16,18 (Bahrain, Australia,
Miami, Monza, Singapore). All are non-benchmark development events, chosen before
their new telemetry inspection. The subset supplies multiple tracks/drivers and
chronological training/validation/evaluation events. No benchmark data is accessed.
Native archive hashes, versions, tables and raw row lineage are retained.

Build a dedicated slim tyre dataset from native lap tables after archive and
benchmark checks. Keep only finite positive lap times; exact GREEN track status
`1`; IsAccurate true; Deleted false; no pit-in or pit-out timestamps; dry S/M/H
compound; integral positive driver/lap/stint and finite nonnegative tyre age.
Unknown flags/fields fail eligibility. Every rejected native row has reasons.
No pace-based/outcome-based outlier trimming. Contiguous accepted laps within one
event/driver/stint/compound form segments; gaps or compound/stint changes reset
the anchor and latent state. Segments require >=6 accepted contiguous laps for
1/3/5-lap forecasts. This retrospective target-quality mask is not an online flag
forecast. No weather/traffic adjustment or cross-provider substitution is invented.

Fuel proxy: initial 105 kg, burn 1.4 kg per race lap, time effect 0.030 s/kg.
All are PRIOR, not measured fuel. Negative proxy fuel is rejected, not clipped.
Corrected pace = observed seconds minus prior fuel effect. Initial fuel and
absolute tyre pace are not separately identified by lap timing; estimates describe
a fuel-corrected latent pace component, not physical tyre wear. Frozen sensitivity
uses time coefficients .020/.030/.040 s/kg, with identical input/filter/splits.
The primary coefficient remains .030; no best sensitivity is selected.

## R021 state model and evaluation

After observing the first eligible lap of a segment, pace state mean is that
fuel-corrected time and variance R (flat-intercept posterior). Subsequent pace
increments have compound drift d and random-walk variance Q per lap; observed
pace has Gaussian variance R. Forecast before updating with the target lap.
Fit d_S/d_M/d_H in [0,.5] s/lap, Q/R in [1e-5,4] s^2 by training-only marginal
Kalman likelihood with three deterministic starts; require successful finite fit
and preserve the selected training likelihood. No innovation clipping. Compare
fuel-corrected persistence and causal last-three-observation linear trend on the
same eligible origins and horizons. Parameters and every prediction are saved.

Rolling whole-event origin folds: train round1->evaluate3; train1+3->evaluate6;
train1+3+6->evaluate16; train1+3+6+16->evaluate18. Held-out prefixes update latent
states only after their observations arrive; they never update parameters.
Report MAE/RMSE, Gaussian NLL, predictive interval coverage/width, per-event,
compound/horizon errors and source coverage. Completion requires real-data rolling
metrics, hand fixtures, causal/no-lookahead checks, finite fitting and baselines;
model superiority is measured, not assumed or required by the backlog gate.

## R022 hierarchy and calibration

Use each training segment's exact Gaussian state-model marginal drift likelihood
as a scalar normal likelihood (mean/variance computed independently of the hierarchy).
Drift = population mean + compound + track + driver effects. Proper Gaussian
priors and inverse-gamma group-variance priors yield conjugate blocked Gibbs updates.
Population prior N(.05,.2^2); effects zero-mean conditional on their group variance;
IG shape3/scale.01 for compound and shape3/scale.0025 for track/driver. Q/R remain
plug-in estimates from the R021 training-only state model (declared conditional
Bayesian/empirical-Bayes noise boundary). No unobserved fuel is inferred as truth.

Train hierarchy on rounds1+3 only, use round6 only for predictive calibration,
then evaluate rounds16+18 without refitting or calibration updates. Two chains,
seeds11/23, warmup1500 and 1500 retained draws each. Draw unknown track/driver/
compound effects from their hierarchical priors, retaining epistemic uncertainty.
Mixture predictive draws incorporate state, observation and drift uncertainty.
Conditional state updates use observed held-out prefixes, never future targets.
Report raw posterior predictive intervals/PIT and separately validation-calibrated
intervals; parameter credible intervals remain unmodified Bayesian output.

Calibration: horizon-specific finite-sample .90 absolute-standardized-error
quantile on Miami, frozen before either test event. Apply that scale to predictive
standard deviations, without test-set tuning. Report pre/post coverage, width and
cluster-bootstrap uncertainty by event/driver/segment (500 resamples, seed2021).
Acceptance: split R-hat <=1.10 for population and supported predictive group drifts;
finite positive posterior variances/draws; aggregate held-out 90% calibrated
coverage in [.80,.98] at each horizon, finite mean interval width <=20 s, >=100
held-out predictions per horizon. Per-event misses remain visible and forbid broad
real-world or production promotion; these small development tests are not the
permanent benchmark. If this frozen gate fails, retain evidence and do not mark
R022 DONE or retune against test outcomes.

## Artifacts, tests and stopping gate

Hand Kalman/normal-posterior checks; synthetic drift recovery and pit/gap resets;
invalid state/variance rejection; later observations cannot change earlier forecasts;
future evaluation changes cannot change training fits or calibration factors;
unseen-group variance, local RNG determinism, sampler diagnostics, protected-event
refusal before native payload access, exact dataset/manifest integrity and immutable
outputs. Save dataset/rejection inventory, model configs/fits, all forecasts,
calibration membership, all-chain posterior summaries/draws, metrics, environment,
input/code hashes and completion manifest last. Bulk data/weights remain ignored;
compact model/data cards, full aggregate evidence and reports belong in Git.
Real race archives must pass offline replay; full regression/lint and Python
3.11/3.12 CI must pass before both backlog rows close. No automatic R2/kernel
promotion follows; R023 robust observation modelling remains a separate task.
