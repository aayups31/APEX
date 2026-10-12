# R024 public tyre-energy proxy dataset

## A. Current state

Baseline 7fefeb4, scoped research R1/kernel R0; 22/73 research rows DONE. R024
starts IN_PROGRESS. Relevant fresh baseline: five tests pass in 21.14 s;
research-demo inspected finite predictions and resource states. Existing full
regression/CI: 469 passed. Pre-existing artifacts remain preserved.

## B. Scope

Build a causal native-sample four-wheel proxy dataset with explicit priors,
unknown measured quantities, source-row lineage and portable reload validation.
Two fixed drivers, five existing development races. No forecasting training or
production promotion; R023 remains pending.

## C. Source of truth

Master guide, maturity model, R024/backlog, existing R006 estimator, TODD protocol,
FastF1 archive contracts, sealed R021 eligible lap mask, and the
[frozen plan](../../research/protocols/TYRE_ENERGY_DATASET.md).

## D. Implementation plan

Causal car derivative and backward-only position join; local quadratic geometry
proxy; strict support/exclusion rules; labelled canonical schema; immutable
Parquet artifacts and source manifests; boundary/numerical/artifact tests.

## E. Acceptance

Frozen five-event coverage, label completeness, finite targets and lineage,
no future-input influence, immutable/reload/tamper tests, full regression and CI.
Rows close only after public evidence exists and all gates pass.

## F. Limits

These energies are proxies under assumed vehicle/slip/coordinate conventions.
They are not measured tyre energy, steering, force or wear. The retrospective
clean-lap mask and irregular sampling are recorded explicitly.

## G. Order

Implement/test/push; build public artifact; inspect and publish evidence/card;
run regression/CI; close R024 and move to matched forecast baselines R025.
