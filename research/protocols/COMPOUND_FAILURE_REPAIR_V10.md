# R041 failure audit and event-adaptive development, v10

## State and objective

Baseline f757aea: foundation R1, production R0, R041 IN_PROGRESS. Existing 32
R041 tests pass; retain full baseline and frozen v9 verification evidence.
Preserve every v1-v9 result and source-bound module. R040 is complete; R042
remains downstream. Audit failures before fitting another candidate.

## Inputs and scope

Use only previously opened data: v9 development plus its four-race confirmation,
392 cases / 24 supported events / 28 source events. Append parents without
overwriting seals. No fresh races or permanent benchmark payloads may be
acquired unless the new development gate passes. Missing physical wear, fuel
measurements and physical compound allocation remain unknown.

## Failure audit

Independently enumerate OpenF1 lap eligibility, all different-compound stint
pairs, contiguous common-age runs, causal reference availability and retained
12-age cases. Check exact agreement against published cases, including zero
support; report exclusion counts and unsupported-pair reasons. Preserve the
retrospective cohort; do not shorten horizons or relax quality masks to gain
support. FastF1 native verification retains a separate denominator scope label.
List pace regressions, false alarms, positive-event precision/recall failures,
missing support, uncertainty limitations and unknown physical quantities
separately. Audit invalid-input handling without rewriting historical code.

## Repair hypothesis

Test transparent event-adaptive pace estimates against reference, contrast,
midpoint, v9-family ridge and fixed tree baselines. A field estimate uses only
completed matching-age same-compound windows from OTHER drivers, equal driver
weight and retained timestamps. Compare reference persistence, pure field drift
and half-shrunk field drift; absent contributor support, use reference
persistence. Compare minimum distinct-driver support 1/3/5. Cap correction at
0.5 seconds and expose raw/clipped correction and fallback.

Derive crossover decisions from the same predicted contrast, requiring both
label prefixes to reverse beyond the original 0.15-second margins. Compare
decision margins 0.15/0.30 seconds; never call these calibrated probabilities.
Keep both-head agreement and accuracy tradeoffs visible.

## Validation and stopping gate

Use nested whole-event validation. Inner folds select settings by fewer failed
event/label gates, fewer negative-control false alarms, then macro both-label
pace error and simpler settings. The outer event cannot influence settings or
its uncertainty radius. Include every fallback in the same cohort.

Qualification is stronger than v9's macro/pooled gate: at least two informative
supported events, EVERY supported event passes both pace baselines under both
labels, every positive label reaches >=50% precision and recall, and every
zero-event label has zero false alarms. Keep all failures and empty sources
visible. If no candidate qualifies, reject the hypothesis and do not consume
more holdouts. Cross-event radii remain descriptive; physical wear stays unknown.

## Deliverables and order

1. Native cohort audit, failure inventory and tested stricter qualification gate.
2. New causal event-adaptive interface with invalid-input, contributor,
   future-target, future-context and empty-support tests.
3. Full-grid/nested tables, independent scalar audit, exact replay, tests/CI
   and truthful project status.
4. New prospective protocol only if stronger development qualification passes.

No production promotion or claim of perfect forecasting follows from this run.
