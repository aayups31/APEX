# R023 frozen robust observation comparison

2026-10-12, baseline018c198. Research R1/kernel R0; 23/73 DONE. Fresh relevant
baseline28 tests pass in13.19s; both R022/R024 artifact reloads pass. Prior full
regression478 tests and Python3.11/3.12 CI pass. No permanent benchmark access.

Classification ADAPTATION. Use Hansen's standardized zero-mean/unit-variance
skewed Student-t density (nu>2, |lambda|<1), independently implemented and checked
against normalization/moments/CDF inverses and its symmetric Student-t limit.
Sources: Hansen1994 primary paper and official arch distribution documentation.
This is not reproduction of Cappello's proprietary case or observation family.

Keep R022's sealed Gaussian-trained Bayesian group posterior and Q/R fixed;
this is conditional/modular inference, not a new jointly fitted skew-t hierarchy.
Fit observation shape on Bahrain+Australia only by a fixed training particle
marginal-likelihood grid: nu4/8/20, skew-.25/0/.25/.5. Use512 particles per
training segment and point posterior group drift; seed101 plus stable segment
hash. No test or validation values enter shape fitting. Selection is minimum
training NLL. Priors, drift/Q/R, eligibility mask and data remain unchanged.

Evaluation: freeze32 stratified posterior drift draws per segment,64 state
particles per draw, seeds11/23/37. Each draw's bootstrap filter conditions on past
observations using skew-t likelihood, with systematic resampling; group posterior
weights remain fixed (cut feedback). Flat-intercept initialization reflects
observation noise about the first observed value. Predict horizons1/3/5 before
target updates, combining latent process and observation uncertainty. Gaussian
control uses exact per-drift Kalman state filtering and the same group draw subset.
Save predictive draws, forecast keys, means, intervals/PIT, CRPS and RMSPE.

Miami is validation diagnostics only. Monza/Singapore are final DEVELOPMENT tests
already inspected by earlier studies; they are not untouched benchmarks. No
test retuning. Compare on identical origin/horizon keys. Primary acceptance:
at least1% aggregate CRPS improvement at >=2 horizons, with RMSPE no worse than
5% at any horizon; or >=1% RMSPE improvement at >=2 horizons with CRPS no worse
than5% at any horizon. Report all seed/event/horizon and cluster-bootstrap paired
differences (500 resamples seed2023). Otherwise REJECT the robust candidate;
R023 is DONE when the complete comparison, accept/reject decision and tests exist.
No guaranteed repair of nominal coverage or production promotion is implied.

Numerical/causality/RNG/protected-input tests, immutable outputs, posterior/draw
reload, public artifact integrity, full regression/lint and matrix CI are required.
An execution smoke uses smaller particle counts and cannot close the task.
