# R041 causal trajectory repair, v11

Baseline a73f15a: research foundation R1, production R0, R041 IN_PROGRESS.
The v10 source passes 817 tests on Python 3.11 and 3.12. Its 13 failed
development events remain failures. Baseline targeted tests and full native
cohort reconstruction pass again before this experiment.

## Hypothesis and unchanged task

Three current laps may give an unstable local trend. Test whether the earlier
observed portion of that SAME current stint and the completed reference's
trajectory provide transferable information. Unlike the old nine-lap-prefix
diagnostic, DO NOT move forecast time six laps later or shorten the horizon.
Keep exactly the 392 cases, both target definitions, 28 sources, masks and
forecast clocks of v10. Do not fetch new outcomes or reserved benchmark races.

At each original forecast clock, collect at most twelve consecutive retained
current-stint laps ending at the third prefix age. Stop at the first quality
gap. Also collect the twelve original matched ages of the completed reference.
Every contributing lap must end by the forecast clock. Keep native clocks and
ages beside each pace value. No later current lap is an input. Preserve original
case fields exactly; record unavailable history rather than dropping cases.

## Fixed models, before viewing v11 scores

Primary: absolute-error gradient boosting, 128 trees, depth 2, minimum leaf
16, learning rate 0.03, full sampling, seed 41. Predict nine-age-lap current
pace change, then subtract it from completed-reference persistence. Correction
is bounded at 2 seconds (an explicit experimental influence prior, not a
physical constraint). Report every bound hit. Unsupported compound training
support (<3 events) falls back to reference persistence, counted in all metrics.

Features: existing six causal conditioned features; current starting age;
history length; horizon-scaled median pair slopes over trailing 3, 6 and 12
laps; median absolute residual about the trailing-12 robust line; latest
three-lap median minus the full history median; reference horizon-scaled
median pair slope, dispersion around its robust line, and last-minus-first
three-lap median change. Compound identities remain the provider's relative
labels. These are pace proxies, not measured wear or physical allocations.

Fit with equal event mass and duplicate-target weights. Compare three fixed
ablations with the same learner: six original features, current history only,
and full trajectory (primary). Add a train-scaled ridge alpha 10 on full
trajectory as a statistical comparator. No search, score-driven selection,
threshold adjustment or replacement of the primary after results are opened.
Prediction uses the same point forecast for both-prefix-agreement crossover
decisions, margin 0.15 seconds. Report reference/contrast persistence too.

## Evaluation, limits and stopping gate

Leave out whole events for every fit. Each fixed recipe is evaluated separately;
there is no tuning using outer labels. Preserve every fold, prediction and
failure. The v10 readiness gate is unchanged: every supported event passes
both pace baselines and both precision/recall gates, zero false alarms in
negative controls, and at least two informative supported events.

Report both-label MAE/RMSE, compound breakdown, bound/fallback counts and
descriptive error distribution. Do not claim calibrated predictive intervals
from these development folds. Only a primary pass permits a separately frozen
prospective protocol; development success alone cannot complete R041.
If primary fails, reject this hypothesis and preserve the results. Do not
consume the remaining fresh races to rescue a failed development candidate.

## Verification

Check native archive seals and benchmark guards before payload access. Audit
each appended lap independently against native age, time, compound and fuel
correction; disclose the scope of that audit. Verify old fields/cohort unchanged,
future-target mutation invariance, future-history rejection, gap handling,
duplicate target weighting, hand-calculated trajectory features, finite
arithmetic and exact replay. Retain source hashes, environment, tests and CI.
Keep historical v1-v10 implementations and seals intact. No production change.
