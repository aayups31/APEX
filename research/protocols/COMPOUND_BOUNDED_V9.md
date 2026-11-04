# R041 bounded residual development, v9

## A. Current state

Foundation R1, production R0; R040 is done and R041 is IN_PROGRESS. The v8
confirmation is rejected: Qatar pace MAE 0.801/0.839 s exceeds reference
persistence 0.349/0.387 s. Preserve that result and every earlier rejection.
Baseline commit: 6658a20. The 18 existing compound tests pass; frozen v8 panel
replays exactly. Research and six-car/six-lap demos run, with no race quality
violations. The full baseline suite is running separately.

## B. Scope

R041 only: test whether bounded, support-checked residuals and already recorded
context improve whole-event generalization. This is research on conditional
fuel-prior-corrected pace, not physical wear, causal compound effects or a
production promotion. R042 remains next after R041's acceptance evidence.

## C. Inputs and boundaries

Follow the master guide, tyre-pace data card and v4-v8 cohort/UTC contracts.
Append the now-opened Miami/Imola/Qatar panel to the sealed v8 training corpus.
Keep all 358 cases, 22 supported events, 24 source events, and both empty events
(2023 Australia and 2025 Miami). Verify native archives and permanent benchmark
exclusion before payload access. Never overwrite previous sealed evidence.

The retrospective 12-consecutive-common-age cohort and nine-lap horizon stay
fixed. Future current-stint targets and future weather/field observations may
not affect predictions. Causal context includes absolute tyre age, weather
observed no more than 120 seconds before forecast, a past 600-second temperature
change, and completed same-compound matching-age field windows. Missing or stale
weather stays explicit. Completed field windows carry contributing lap-end
timestamps. No future traffic sensor or future tyre allocation is invented.

## D. Method

Implement a new research interface; leave source-bound v1-v8 modules unchanged.
Predict a residual from one of three transparent baselines: reference
persistence, contrast persistence, or their midpoint. Fit ridge to the midpoint
of the two contrast labels, standardizing only on training events. Give each
event equal total weight and each unique current-stint target equal weight
within an event; detect contradictory repeated current targets.

Predeclare the small grid: baseline reference/contrast/midpoint; feature groups
pace/context; ridge alpha 10/100; symmetric residual bound 0/0.25/0.5 seconds.
Zero bound is a baseline comparator. Context adds tyre age, known weather and
completed field drift; pace features retain compound, reference change, local
prefix slope and contrast. Outside the training feature range for the current
compound, or with fewer than three training events for it, use the selected
baseline. Log correction before/after bounding, support reasons and every
fallback. Do not remove fallback cases from metrics.

Compare this ladder with unbounded v8-family ridge and a fixed-seed tree
baseline under identical inputs and folds. Event classification retains the
v8 feature contract and C grid 0.1/1/10, thresholds 0.35..0.65 in 0.01 steps.
Select it separately, recording that scores are uncalibrated decisions.

Use nested whole-event validation: inner leave-one-event-out selects baseline,
features, alpha and bound by macro mean of both-label MAE, with deterministic
simpler-model tie breaks. Outer held-out events estimate the selected procedure.
Event-head selection maximizes the minimum pooled precision/recall under both
labels on inner folds. Never use an outer event to choose its model or threshold.
Also save the full non-nested development comparison table as selection evidence,
clearly separated from outer estimates.

Calibrate empirical 90% absolute-error radii using cross-event prediction errors,
not training residuals. Report coverage and width; cross-validation residual
radii are descriptive and do not confer finite-sample coverage guarantees.

## E. Qualification and stopping gate

Do not open fresh race outcomes unless the nested procedure beats BOTH simple
baselines in macro MAE under BOTH labels, and its pooled event precision AND
recall reach 50% under BOTH labels. Report all event-level failures and zero-event
controls regardless. A failed qualification ends this experiment; do not search
fresh races until one happens to pass.

If qualification passes, a separate prospective protocol must freeze model,
source hashes, untouched events and support/zero-event rules before acquisition.
R041 completion still requires independent held-out crossover confirmation,
pace MAE no worse than both baselines per supported event under both labels,
at least 50% crossover precision/recall on informative events, explicit negative
controls, independent source/scalar audit, causal tests, exact replay and CI.
Development qualification alone cannot close R041.

## F. Risks

Only 22 supported events; multiple development attempts; tyre naming differs
with allocation; weather is sparse; fuel and clean-lap eligibility remain
priors/proxies; field context may be absent; source clocks do not establish true
sensor latency. A hard correction bound limits damage, not forecast error.

## G. Order

1. Add bounded model and causal context tests, including corruption and future
   data mutations; push verified implementation.
2. Rebuild append-only, source-bound development data and inspect joins.
3. Run and seal full-grid and nested whole-event results, fallback/error tables
   and uncertainty diagnostics; reproduce them exactly.
4. Qualify or reject before considering fresh acquisition; report the evidence.
5. Run full applicable regression/CI and update truthful project status.
