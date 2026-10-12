# R021/R022 public-data tyre-pace study

## A. Current state

2026-10-11, baseline 1f77156. Research R1/kernel R0, 20/73 research tasks DONE.
R021/R022 TODO before this slice. Fresh baseline 450 passed, two existing warnings,
127.44 s at `.cache/r021-r022-baseline-20261011`. Existing qualifying-only
development corpus cannot establish race-stint degradation. The legacy Kalman
starter uses a whole-sequence percentile baseline; it is retained as an educational
demo and will not be reused for causal public-data evaluation. Artifacts are preserved.

## B. Scope

Complete R021 fuel-corrected latent pace fitting with whole-event rolling metrics,
then R022 compound/track/driver hierarchical Bayesian prediction and validation-only
calibration. No permanent benchmark access, skewed-t R023 implementation, production
policy integration, physical-wear ground-truth or world-model promotion.

## C. Inputs

Master guide, replication standard, CAPPELLO_2025 starter/registry, sealed benchmark
policy, FastF1 native archive contracts and tests, and the new
[preregistered protocol](../../research/protocols/TYRE_DEGRADATION.md).
Five non-protected development races are selected before acquisition.

## D. Implementation

Acquire/replay archives; build source-labelled slim lap/stint dataset with exclusion
reasons; add training-only Gaussian state fit and rolling predictions; add conditional
Bayesian hierarchical Gibbs inference with unseen-group uncertainty; freeze Miami
calibration before Monza/Singapore evaluation; immutable CLI/artifacts/cards/tests.

## E. Gate

Use the protocol's frozen numerical, causality, held-out, sampler and coverage gates.
Real data and all methods use identical eligible origins/horizons. Failed gates are
not replaced by a synthetic-only pass. Both rows remain IN_PROGRESS until evidence,
full regression and matrix CI pass. No retrospective test-driven retuning.

## F. Risks

Unmeasured fuel, pace/wear/driver/traffic confounding, upstream reconstructed fields,
retrospective masks, limited training tracks, correlated observations, weak group
hyperparameter identification and Gaussian tails. Preserve per-event failures and
raw-vs-calibrated intervals. Do not reinterpret uncertainty calibration as accuracy
of a current Formula 1 car or a paper reproduction.

## G. Order

Baseline/source review; freeze protocol; acquire development races; dataset/state
model/tests and checkpoint push; hierarchical model/tests and checkpoint push;
real frozen study and inspection; regression/CI; evidence/cards and closure push.
Status IN_PROGRESS; requested stopping condition is both R021 and R022 complete.
