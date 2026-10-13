# R026 frozen seen/unseen-track evaluation

Preregistered 2026-10-13, baseline c62a5bc. Fresh baseline: 497 tests pass in
264.73 seconds; synthetic research and six-car/six-lap race previews run, with
race quality checks passing. Research inventory 25/73; scoped research R1/kernel R0.

## Claim and boundary

Evaluate the R025 frozen six-family proxy forecasters on separate events at
training-seen and training-unseen circuits. No retraining, test selection,
hyperparameter search, scaler/vocabulary fitting or interval calibration occurs.
R026 is a retrospective cross-season DEVELOPMENT evaluation, not a prospective
deployment or permanent-benchmark result. Targets remain PROXY_NOT_MEASURED.

Frozen R025 summary c8f538d7ae46ec06a46d9af1b37fb9e4fe7429ac3c942845976fe2ccf189fe9f;
training Bahrain/Australia 2024, validation Miami 2024. Reuse all ten selected
checkpoints, their training-only scalers/vocabularies and the validation-selected
XGBoost candidate. No model is selected using R026 scores. Earlier 2024
Monza/Singapore development inspection is disclosed.

## Membership frozen before telemetry acquisition

| Event | Circuit ID | Stratum | Race date |
| --- | --- | --- | --- |
| F1_2023_R01 | bahrain | seen | 2023-03-05 |
| F1_2023_R03 | albert_park | seen | 2023-04-02 |
| F1_2023_R14 | monza | unseen | 2023-09-03 |
| F1_2023_R15 | marina_bay | unseen | 2023-09-17 |

The verified Jolpica 2023 calendar seal is
62f7dad20cf71d1a5b00a5c9476d95f7ca0972d4b16bdbae369f03cc034162c8.
Metadata-only FastF1 scheduling independently confirms these exact round/name/date
identities. Use completed-event provider numbering rather than the original
[announced calendar](https://www.formula1.com/en/results/2023/races).
All four events pass the existing permanent-benchmark guard; none of the nine
reserved whole-event weekends may be acquired. Download trusted isolated archives,
verify them, and require exact fresh-process offline replay with zero requests.

Both strata use the same 2023 season. This avoids assigning one season only to
one stratum, but car/driver/regime/layout differences still confound any causal
interpretation of track novelty. Seen means the circuit identifier occurs in
R025's TRAINING vocabulary, not that the event or every geometry version was seen.

Drivers 4/44 are fixed with no outcome-driven replacement. Build the same R021
clean-dry retrospective eligibility mask, six-lap minimum segments and unchanged
fuel priors. Reuse the R024 physical proxy equations, support thresholds, vehicle
priors, labels, native exclusions and no filling/projection policy. Keep original
R024/R025 artifacts immutable; new data gets its own input seal. A missing stream
or inadequate coverage fails the gate rather than prompting event substitution.

## Information, metrics and uncertainty

Reuse eight native past samples and four targets at sample horizons 1/3/5,
with identical origin keys for all methods. Enforce sequence/event/driver/stint
and native-row boundaries. Holdout vocabularies are never fitted: use frozen
training vocabularies with explicit UNKNOWN. Report actual elapsed-horizon
distributions separately by stratum. Reject circuit identity mismatches or
duplicate event membership before telemetry inference.

Methods: all selected linear/ridge/XGBoost/GRU/LSTM/TFT checkpoints, causal
persistence and last-three-energy trend. Preserve raw and declared nonnegative
projected outputs, counts/magnitudes, per-seed/wheel/horizon/event MAE/RMSE/SMAPE
(epsilon .001 kJ), and raw/projected TFT quantiles with uncalibrated 80% coverage.

Report both frame-weighted scores and equal-event scores; the latter are primary.
Primary event RMSE is sqrt(mean(event MSE)), not the mean of event RMSE values.
For each stratum, use 500 hierarchical bootstrap replicates, seed2026: resample
events then whole sequence clusters within each sampled event. Pair each model
with persistence on the exact same sampled clusters. Save RMSE intervals and
paired MSE-difference intervals, plus unseen-minus-seen MSE-gap intervals.
Average seed-specific MSE differences for a fixed family only for the declared
family decision; do not treat seeds as independent events or ensemble predictions.
Report point MAE/SMAPE tradeoffs as well as primary MSE.

Two circuits/events per stratum are sufficient for this descriptive completion
gate but insufficient for broad population claims; report that limitation beside
the confidence intervals. Race, sequence and wheel correlations remain relevant.

## Frozen decisions and completion

For the validation-selected XGBoost family only, flag
SUPPORTED_IN_FROZEN_DEVELOPMENT_COHORT if equal-event RMSE improves at least1%
over persistence in BOTH strata and BOTH paired MSE-difference upper95% bounds
are negative. Otherwise NO_CROSS_TRACK_PROMOTION. Other models are reported
without test-driven selection. Neither flag promotes the simulator or R2 maturity.

R026 DONE requires all four sealed real-event datasets/replays, at least1000
complete matched origins per event, both drivers represented in the cohort,
both strata with two circuit identities, all requested frozen model checkpoints
reloaded and evaluated, separate confidence intervals, immutable prediction and
manifest reload, causality/leakage/boundary/cluster-statistic tests, full regression,
lint and Python3.11/3.12 CI. Negative generalization findings can close an honestly
completed evaluation. SIMULATED smoke cannot close the public research task.

Stopping scope: R026 and its reusable guarded evaluation plumbing, evidence,
model/data cards and closure push. R027 explanation faithfulness follows;
measured-energy validation, closed-loop replay and team-ready strategy evidence
remain later gates. No claim of F1 team interest follows from this experiment.
