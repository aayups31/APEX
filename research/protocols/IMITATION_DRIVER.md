# R036 conditional steering imitation and dataset aggregation

Preregistered2026-11-01 before R036 expert selection, model fitting or held-out
learner simulation. Research-only ADAPTATION. User explicitly requests R036 before
R037/R038; those broader multi-lap/OOD gates remain open. No production promotion.

## A. Current state

Base `3b83de4b2c12aa514e18622af8e81e43a56dab8f`;690 tests and artifact workflows
passed Python3.11/3.12 in CI41244984366. Fresh baseline:689 passed, one existing
Jolpica offline-child subprocess timeout, two dependency warnings. Its traceback
reports a negative remaining timeout(-5748.641s) during the clock/date change;
reported elapsed82330.38s is not a valid compute benchmark. The unchanged isolated
test passes in21.82s. This timing anomaly is explained without changing source or
relaxing a test timeout; final regression must pass in a stable clock interval.
Fresh R035 synthetic disturbed-circle reference passes, seal
`89d42bea396787ed2f518ae1968c8665ad7bbedd0fcb6e03dc01dd89e84583df`;
R035 calibration scientific replay also passes unchanged. Foundation R1/kernel R0.
R035 is DONE for conditional generated-action laps, not measured-car calibration.

## B. Scope and dependencies

Train a causal steering-residual policy from explicitly SIMULATED expert labels,
with whole-event train/validation/test separation. Demonstrate improvement over
the frozen R035 transparent driver under identical map, pace and vehicle conditions.
No observed human steering exists in this public cohort. This is not human-style
recovery, real-car imitation, faster F1 pace, RL/MPC, a world model or formal R4.
Longitudinal control remains transparent and shared by every method; learned
steering is bounded in influence and passes the same physical actuators.

## C. Source truth, cohorts and paper

Require accepted R035 study seal
`58a8e7a318e12c0db80a9c70c2dfffb6fd5818534a15fa657a8e33d6b0b49ae0` and calibration
seal `2dc610c27b9219caf53759c0d8f1211a8b5d492b82758c04743997e099059b1e`.
Freeze their source package, supplied R029 maps and fraction.65/cap60m/s pace.
Guard every event before binary reads. Nine permanent benchmark events stay
untouched. R036 learner selection does not consume Monza2024 outcomes.

Use first two frozen laps per driver4/44 for each2023 event as training conditions
(eight nominal conditions). Generate nominal and signed small-disturbance episodes
for each: initial lateral +.4m/heading+.01rad for driver4, negative for44.
Training total16 episodes per collection round. Validation is first two2024
Bahrain laps per driver, four nominal cases. Test is first two2024 Monza laps per
driver, each nominal and the same signed disturbance: eight required cases.
IDs select conditions; event/driver/lap IDs and absolute station/XY are not model
features. All chassis states/actions after initialization are SIMULATED, car
parameters PRIOR, supplied map RECONSTRUCTED and initial source speed parsed-source.
Maps are known offline conditions and reused development data, not unseen-track proof.

Method reference: Ross, Gordon and Bagnell2011, *A Reduction of Imitation Learning
and Structured Prediction to No-Regret Online Learning*, PMLR15:627–635,
[fixed paper](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf), read2026-11-01.
Adapt Algorithm3.1: collect expert-labelled visited states, fit supervised models,
execute a learner on training conditions, aggregate its newly expert-labelled
states and refit. One finite aggregation round is not the paper's asymptotic
guarantee or racing-game reproduction. No paper performance magnitude is claimed.

## D. Expert, features, training and interfaces

Keep R035/R032 accepted source behavior unchanged. A new research rollout runner
shares the R032 integrator and matches R035 force/actuator equations exactly.
No pose/speed resets or chassis state clipping. Every applied action and physical
projection is retained. Generated raw steering is the only learned action.

The analytic expert adds feedforward preview to R035:
`delta_expert_raw = delta_R035_raw + (L+K*v²)*(kappa(s+tau*v)-kappa(s))`,
`K=m/L*(b/Cf-a/Cr)`. Known-map preview is allowed for every baseline; it is not
future measured steering, speed or state. Select tau from {.025,.05,.075,.10}s
by equal-driver/lap validation station-weighted lateral MSE, among complete
physically supported candidates. Retain every candidate/failure. Expert selection
is an explicit controller improvement; student imitation cannot be credited with
inventing that improvement. Report the expert as an additional matched comparator.

Feature vector: v²/3600,50*kappa_current,50*kappa_preview, wrapped velocity-heading
error, atan(.8*e_y/(v+5)), v*kappa_current-yaw_rate, body sideslip, previous applied
steering. Units and reference scalings are declared priors. Feature extraction
reads current simulated state/actuator memory and known map only, never an expert
label or a future source row. Target is expert raw-steering minus R035 raw-steering,
in radians. Clamp learned residual to +/-.2rad as an exposed bounded-influence
architecture prior; log every intervention. R035 road-wheel/rate and force limits
still apply. Recompute longitudinal axle capacity using actual applied steering.

Fit train-only weighted mean/scale, then ridge on degree1 and degree2 monomials,
alphas {1e-8,1e-4}. Bias unpenalized, deterministic augmented least squares.
Equal events/drivers/laps/nominal-disturbance cases receive equal total weight;
row density must not dominate. These compact models are the strongest applicable
linear/polynomial baselines, not a neural-network size claim. All coefficients
must genuinely fit generated labels and be exportable without executable pickle.

Select the best behavior-cloning checkpoint by complete validation lateral MSE,
ties fewer parameters then larger alpha. Execute that learner without expert
interventions on the16 training conditions, query expert labels at its visited
states, append that complete round and refit the selected class/alpha. Choose
between initial and aggregated checkpoints using the same validation rule; an
exact numerical tie keeps initial BC. Failed training prefixes remain and are
reported; no failed case may be replaced. No validation/test rows enter either
scaler or coefficient fitting. Freeze/push dataset, expert choice, weights and
selection before test evaluation. Every model has source/config/data hashes.

## E. Evaluation and stopping gate

Report teacher-forced action errors, closed-loop path/finish/constraint metrics,
expert-to-learner drift, runtime/parameter count, physical bounds and interventions.
Full-lap held-control physical replay is reported separately from autonomous
policy performance; do not mislabel teacher forcing as free-running forecasts.
Compare frozen R035, selected analytic expert, best linear BC, initial selected BC
and selected final learner on the same eight test conditions. Keep duplicate
checkpoint identities explicit instead of counting them as independent evidence.

DONE requires all eight final-learner test cases complete within300s, maximum
reference error<=5m, P95<=2m, finite supported states, friction utilization<=1+1e-12,
positive contact, pitch residual<=1e-6Nm and power identity error<=1e-6W. Every small
disturbance must end with absolute reference error<.4m. Compare nominal cases with
station-weighted MSE on a shared2001-node reference grid: final learner macro RMSE
must improve at least10% over R035, each driver's RMSE at least5%, each driver's
P95 no more than5% worse, and each nominal finish no more than1% slower. No credit
for reduced speed, changed limits or forced path following. Source-time/speed
shortfall and lack of real-car validity remain visible, unchanged by task closure.

Repeat all four final nominal cases with RK4.01s versus.02s, commands held.1s:
finish difference<=.2s, common-station XY<=.5m and speed<=.5m/s. Independently replay
at least one complete final held-out lap plus eight representative intervals per
nominal case with scalar tyre/load-bisection/DOP853: XY<=.05m, body velocity<=.01m/s.
Independently check feature/label equations, weighted normalization and ridge fit;
deployed inference cannot call expert/training helpers. Separate exact artifact
hashes from numerical replay (rtol1e-7/atol1e-8; independently fit predictions1e-7rad).

Tests: hand polynomial/ridge, training weights, event-safe normalization/aggregation,
target perturbation, deployment expert independence, map/frame invariance, old
controller parity, bounds/disturbance recovery, frozen selection, portable outputs,
reserved-event guard before payload reads, tamper and resealed false completion.
All applicable regression/CI and published evidence/card/equation map are required.
Smoke is SIMULATED_EXECUTION_ONLY and cannot close public R036. If any mandatory
gate fails, preserve failure; no silent retuning on test or lowered threshold.

## F. Risks

Teacher bias; trivial-to-learn analytic target; generic vehicle and supplied-map
conditions; existing R035 test history; one validation/test event; source speed
is not body velocity; no uncertainty calibration. Learning from a better expert
demonstrates conditional imitation, not superiority to that expert, observed human
behavior or learning new physics. R037/R038 remain necessary before broader use.

## G. Execution order

Finish baseline diagnosis; commit protocol; implement/test policy/training/runner
on synthetic fixtures; push; freeze accepted-source dataset; select expert and
train/aggregate using train/validation only; push frozen choices/checkpoints;
evaluate the complete test catalog and independent/refinement gates; publish all
comparators and limitations; full regression/CI; close R036 only on every gate.
