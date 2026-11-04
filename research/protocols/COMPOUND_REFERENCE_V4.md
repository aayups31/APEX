# R041 completed-reference, current-stint forecast (v4)

## State, scope and development decision

Research foundation R1; production R0. R040 is complete; R041 remains open.
The v1-v3 rejections remain authoritative. This is an effective pace-proxy
forecast, with physical wear unidentifiable from these timing data. No production
promotion or maturity change follows from passing this experiment.

When forecasting a later stint, the earlier stint's target-age lap times have
already happened. Predict only the later stint's pace change; retain the known
earlier curve. Require the end of every reference lap to precede or equal the
forecast time (the end of the current three-lap prefix). Preserve timestamps in
each prediction. Future current-stint times are evaluation targets only.

Use the already opened 2025 Monza, Abu Dhabi, Bahrain and Spain archives for
development. Normalize scope-less safety-car deployments with the v3 correction.
Retain v2 green/dry stint interiors, same-driver different-compound pairs,
consecutive common ages, disjoint 12-age blocks, nine-lap horizon, and sustained
three-age median contrasts beyond 0.15 s on both sides of a sign change.
This remains a retrospectively scored clean/dry cohort, conditional on recorded
future lap availability; it does not forecast future flags or pit decisions.

Development comparison included current-prefix local slope, ridge shrinkage,
compound median drift and persistence. Three-lap local slopes were noisy. Select
the small robust compound-median drift model using these development results
only. Deduplicate repeated later-stint/age targets across reference pairs before
fitting, to avoid giving a later stint extra influence because it has more
available earlier stints. Fit a signed nine-lap pace change for each compound,
with at least three unique development windows. Signed drift is an effective
pace proxy, not a claim that physical wear reverses. Keep the older nonnegative
2024 compound age priors as an additional comparison.

## Frozen equations and information

For current prefix p and reference target r (three timed laps each),
predict the target contrast as median(r) - median(p) - delta[compound].
For consistency, score actual and prefix contrasts as differences of the
respective three-lap medians. This differs from v2's median of pairwise
differences, which need not equal a difference of medians. Publish both label
definitions as a sensitivity diagnostic; the gate must pass under both.
Also record the empirical 90th-percentile absolute training residual per
compound as a descriptive uncertainty radius; report held-out coverage and
width without claiming nominal calibration. No future traffic data is needed.

Baselines share the same cohort and available reference curve:

1. Original contrast persistence: repeat prefix contrast.
2. Completed-reference persistence: median(r) - median(p).
3. Completed-reference plus frozen 2024 compound drift.

Freeze code, protocol, data hashes and parameters before acquiring new race lap
outcomes. Independent confirmation: Canada 2025 round 10 (session 9963,
meeting 1263), Austria round 11 (session 9955, meeting 1264). Session identities
were inspected as metadata only. Protect all permanent benchmark reservations.
Fetch five OpenF1 endpoint tables per event; save immutable manifest hashes,
queries, retrieval time and source/terms references. Do not acquire intervals.

## Acceptance and stopping gate

In EACH fresh race: nonzero observed and predicted crossovers, at least half of
observed and half of predicted crossovers matched, and contrast MAE no worse
than BOTH persistence baselines. Apply the same checks to the original v2
pairwise-median labels and predictions as a label-definition sensitivity.
Report additional 2024-prior baseline error, RMSE, uncertainty coverage, compound
breakdowns, missing support and timestamp exclusions. Preserve failed results.
No threshold or parameter may change after opening these outcomes under a
claim of independent confirmation. A later attempt must declare a fresh split.

Tests cover hand calculations, forecast-time rejection, duplicate calibration
windows, archive/source integrity and mutation of future current-stint targets
without any change in the prediction. Replay saved results exactly, inspect
artifacts, run applicable tests/lint and complete CI before closing R041.
Rollback consists of retaining R041 open and using the prior frozen candidates.

Public source: https://api.openf1.org/v1/ ; documentation and terms:
https://openf1.org/ . Public durations are measured; fuel correction is a proxy
using the retained priors 105 kg, 1.4 kg/lap, and 0.03 seconds/kg.
