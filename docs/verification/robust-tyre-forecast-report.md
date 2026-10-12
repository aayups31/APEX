# R023/R025 robust tyre observations and matched proxy forecasting

## A. Baseline
2026-10-12,018c198,scoped researchR1/kernelR0,23/73 DONE. Fresh28 relevant tests
pass13.19s; R022 and R024 immutable artifact reloads pass. Existing full478 tests
and final matrix CI pass. User artifacts preserved.

## B. Scope
Complete R023's conditional skew-t observation comparison first, then R025's
genuine linear/ridge/XGBoost/GRU/LSTM/TFT matched training benchmark. No benchmark
telemetry, paper reproduction, measured energy or automatic production promotion.

## C. Inputs
Sealed R022 posterior/R021 pace dataset; R024 canonical proxy data; published
Hansen density, official arch docs and Lim TFT architecture; existing contracts.
Frozen [R023](../../research/protocols/ROBUST_TYRE_OBSERVATIONS.md) and
[R025](../../research/protocols/TYRE_FORECAST_BENCHMARK.md) plans define the gates.

## D. Implementation
Normalized skew-t/math tests; causal particle-state inference and Gaussian control;
training-only shape choice and held-out scores; then boundary-safe windows,
train-only preprocessing, all six model families, fair validation selection and
immutable reloadable checkpoints.

## E. Stopping gate
R023 has a frozen accept/reject decision based on CRPS/RMSPE. R025 genuinely
trains all requested model families and scores identical keys/targets/horizons.
Both require real-data artifacts, unit/integration checks, regression and matrix
CI before DONE. No outcome-selected changes to frozen gates.

## F. Limits
Conditional robust inference fixes the Gaussian-trained group posterior/Q/R.
Particle approximation, reused development tests, proxy targets, short native
histories and CPU-limited model budgets remain explicit limitations.

## G. Order
R023 implementation/tests/checkpoint/public comparison; then R025 implementation/
tests/checkpoint/public benchmark; inspect artifacts; regression/CI; evidence/cards
and closure push. R023 is DONE; R025 remains IN_PROGRESS until its full public
training benchmark and checkpoint verification finish.

## R023 closure checkpoint

R023 is DONE, 2026-10-12. Its conditional research acceptance gate passes:
held-out CRPS improves 8.15%, 6.28% and 4.90% at 1/3/5 laps, and RMSPE improves
4.67%, 4.22% and 3.65%. Raw nominal 90% coverage remains about 88–89%.
Training selects nu=4/skew=.5 on frozen grid boundaries. Gaussian-trained group
posterior/Q/R and fuel priors remain fixed; no production promotion follows.

Final summary seal: `b0dbcad581395d9bba763d6065f842747977de34db7bba280db23e30a999ee2a`.
Final predictions, ensembles, group posterior and config are byte-identical to
the first frozen scientific run. Full public artifact verification passes.
Local full regression: 497 passed in 294.65 seconds; lint passes. Both Python
3.11/3.12 implementation CI jobs pass, including the new forecasting smoke.

[Complete R023 evidence](robust-tyre-evidence.json),
[equation map](../../research/equations/ROBUST_TYRE_OBSERVATIONS_V1.md),
[model card](../models/robust-tyre-observations-v1.md).
Research inventory: 24/73 DONE. R025 is still training its last two frozen TFT
candidates; all six real implementations and the regression/CI gates are ready.
The next action is complete public checkpoint replay and R025 closure.
