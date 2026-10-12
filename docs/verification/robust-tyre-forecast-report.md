# R023/R025 robust tyre observations and matched proxy forecasting

## A. Outcome and baseline

**R023 DONE; R025 DONE**, 2026-10-12. Research inventory **25/73 DONE**, build
inventory **13/66 DONE**. Scoped research maturity remains R1; production kernel
remains R0. No production component or R2 gate is promoted.

The baseline was 018c198, with 23 research tasks done. Fresh baseline checks
passed 28 relevant tests in 13.19 seconds and reloaded the sealed R022/R024
artifacts. Existing user `artifacts/` were not accessed or staged. Scientific
implementation checkpoint **8c474740de4eac50aa6d3c4d9a49938fbc23ecd3** is pushed directly to main.

## B. Frozen scope and inputs

The [R023 plan](../../research/protocols/ROBUST_TYRE_OBSERVATIONS.md) and
[R025 plan](../../research/protocols/TYRE_FORECAST_BENCHMARK.md) were committed
before outcome inspection. R023 compared robust observations first; R025 then
implemented the six requested fitted families. These are ADAPTATIONS, not paper
reproductions. Source review and deviations are recorded in the
[robust equation map](../../research/equations/ROBUST_TYRE_OBSERVATIONS_V1.md) and
[TFT architecture map](../../research/equations/TEMPORAL_FUSION_PROXY_V1.md).

R023 fixes the R022 posterior summary `107dbe9d7c8a7757d99f0a5a24e4ee9bef8880dc111e2c61b0b831644bf9de95` and R021
pace dataset `d79966d3b13c06cb8a0bd6f6bcff1690a10965d6414e0e71840ecf6d7811d6a2`. R025 fixes R024 manifest
`7793df65b58884be74529ecf3114ccf2efc310d0a3dd99dfa9edec4d961c2272`. All five races are development events. Train:
Bahrain/Australia. Validation: Miami. Test: Monza/Singapore. Earlier descriptive
inspection and reused development tests are disclosed. The nine permanent
whole-event benchmark weekends remain protected; no telemetry was acquired.

## C. R023 implementation and decision

Normalized Hansen skew-t density, CDF, inverse and local sampling are implemented
with independent moment/limit checks. A causal bootstrap state filter conditions
on each fixed group drift draw; a matched Gaussian control uses exact conditional
Kalman states. The Gaussian-trained hierarchy and Q/R are unchanged. This is
conditional modular inference rather than a new joint skew-t hierarchy.

Training likelihood selected nu=4, skew=.5, NLL
782.655005875 from the frozen 12-point grid.
Both shape values lie on grid boundaries. Evaluation uses 32 posterior draws,
64 state particles per draw and seeds 11/23/37. Seed replicas share the same
underlying observations and are not counted as independent data.

Decision: **ACCEPT_CONDITIONAL_RESEARCH**. Every horizon improves both CRPS and RMSPE,
passing the frozen gate. No calibration repair is claimed.

| Horizon (laps) | Unique test origins | Gaussian CRPS (s) | Skew-t CRPS (s) | CRPS gain | Gaussian RMSPE | Skew-t RMSPE | Skew-t raw 90% coverage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1,877 | 0.307896 | 0.282811 | 8.15% | 0.658148% | 0.627392% | 89.11% |
| 3 | 1,689 | 0.377599 | 0.353884 | 6.28% | 0.770556% | 0.738026% | 88.18% |
| 5 | 1,501 | 0.421756 | 0.401104 | 4.90% | 0.847675% | 0.816723% | 88.36% |

The 94-segment paired cluster bootstrap uses 500 resamples, seed 2023. All three
95% intervals for skew-minus-Gaussian CRPS are negative; complete bounds and
per-event/seed scores are retained in the evidence JSON. Raw coverage remains
about 88–89%, below nominal 90%. R022's validation interval adjustment was not
reapplied. Fixed fuel assumptions remain PRIOR; corrected pace remains PROXY.

The final metadata-complete run reproduces predictions, ensembles, posterior and
configuration files byte for byte from the first frozen run. Saved ensemble CRPS
recomputation passes. Final R023 summary seal: `b0dbcad581395d9bba763d6065f842747977de34db7bba280db23e30a999ee2a`.

## D. R025 implementation and complete benchmark

All six requested families genuinely fit training data: ordinary linear, ridge,
native XGBoost 3.0.5, GRU, LSTM and compact TFT. Persistence and causal trend are
independent controls. TFT includes GRNs, per-variable selection, four static
contexts, LSTM encoding/decoding, gated skips, static enrichment, shared-value
causal attention and ordered .1/.5/.9 heads. Its pinball loss differs explicitly
from the recurrent point-MSE objective; median forecasts share the point metric.

There are **19,515 training**, **12,671 validation** and **32,582 test origins**, each with four targets
at all three horizons. All methods use identical keys and eight native past
samples. No future telemetry or durations enter inputs. Scalers/vocabularies fit
training only; sequence/event/driver/stint and native-row discontinuities reject
windows. The median elapsed test horizons are 0.240/0.760/1.281
seconds; these are sample-index forecasts, not fixed 0.1-second horizons.

Configuration/family selection uses validation only. Selected family:
**xgboost**, validation RMSE **2.614995 kJ**. The lowest descriptive
test RMSE belongs to **tft**; this test ranking does not select or retune
the candidate. Table values for two-seed families are means of separate seed
metrics, not ensemble predictions. Negative-cell counts sum across saved seeds.

| Method | Validation RMSE (kJ) | Test MAE (kJ) | Test RMSE (kJ) | Test SMAPE | Projected negative cells |
| --- | --- | --- | --- | --- | --- |
| persistence | 3.358770 | 1.140654 | 2.494280 | 74.64% | 0 |
| trend | 6.106383 | 1.758470 | 4.616837 | 111.51% | 105,216 |
| linear | 2.712804 | 1.301734 | 2.137924 | 95.45% | 24,968 |
| ridge | 2.712740 | 1.301471 | 2.137670 | 95.45% | 24,944 |
| xgboost | 2.614995 | 1.183830 | 2.160083 | 79.32% | 3,693 |
| gru | 2.697040 | 1.252795 | 2.127814 | 91.60% | 52,742 |
| lstm | 2.766159 | 1.189271 | 2.144333 | 93.23% | 92,215 |
| tft | 2.774101 | 0.989620 | 2.038929 | 75.83% | 12,496 |

The validation-selected XGBoost improves test RMSE by 13.40% versus
persistence, while its test MAE and SMAPE are worse. TFT has the lowest descriptive
test RMSE, improving it by 18.26% versus persistence, and also improves
MAE. Its nominal 80% intervals cover only about 72–75%. These tradeoffs remain
visible: the completed benchmark does not establish universal superiority or
well-calibrated neural uncertainty.

The common declared projection sets negative energy predictions to zero. Raw
scores and correction magnitudes remain visible in the evidence; no silent
clipping or measured-energy claim is made. Full per-wheel/horizon/event scores,
trial histories, parameter/tree counts and timing are retained.

| Selected checkpoint | Fixed configuration | Best epoch | Test RMSE (kJ) | Paired MSE minus persistence, sequence-cluster 95% interval (kJ squared) |
| --- | --- | --- | --- | --- |
| linear_seed11 | {} | n/a | 2.137924 | [-1.897983, -1.425091] |
| ridge_seed11 | {"alpha": 0.1} | n/a | 2.137670 | [-1.899094, -1.426167] |
| xgboost_seed11 | {"depth": 3, "trees": 150} | n/a | 2.162812 | [-1.809614, -1.304908] |
| xgboost_seed23 | {"depth": 3, "trees": 150} | n/a | 2.157354 | [-1.826756, -1.336656] |
| gru_seed11 | {"hidden": 16, "learning_rate": 0.001} | 12 | 2.133662 | [-1.930958, -1.443118] |
| gru_seed23 | {"hidden": 16, "learning_rate": 0.001} | 12 | 2.121965 | [-1.981531, -1.481585] |
| lstm_seed11 | {"hidden": 16, "learning_rate": 0.001} | 11 | 2.146138 | [-1.864748, -1.394826] |
| lstm_seed23 | {"hidden": 16, "learning_rate": 0.001} | 10 | 2.142527 | [-1.892705, -1.398916] |
| tft_seed11 | {"hidden": 32, "learning_rate": 0.0003} | 11 | 2.061723 | [-2.196970, -1.766438] |
| tft_seed23 | {"hidden": 32, "learning_rate": 0.0003} | 12 | 2.016135 | [-2.368143, -1.960609] |

These intervals use sequence clusters, 500 resamples and seed 2025. Negative
intervals favor the candidate; intervals crossing zero are inconclusive and
positive intervals favor persistence. Seeds are reported separately.

TFT quantiles are native uncalibrated output. Nominal coverage is 80%:

| Checkpoint | Actual coverage | Mean width (kJ) |
| --- | --- | --- |
| tft_seed11 | 71.99% | 2.558830 |
| tft_seed23 | 74.94% | 2.728566 |

All **10 selected checkpoints** reload on the complete test set
without retraining, including raw TFT quantiles. Train-only scalers are
recomputed. An independent artifact audit reproduces all point metrics, common
projections, causal controls, quantile coverage and validation selection.
Final R025 summary seal: `c8f538d7ae46ec06a46d9af1b37fb9e4fe7429ac3c942845976fe2ccf189fe9f`. Training/evaluation took
1119.38 seconds on the recorded CPU environment;
concurrent local checks can affect wall-clock timings.

R025 is complete because the frozen benchmark executes all requested methods
and preserves honest comparisons. Model size is not an acceptance criterion.
Every target remains **PROXY_NOT_MEASURED**. All test tracks are unseen in this
five-event slice; broader seen/unseen evidence remains R026.

## E. Verification and version control

- New combined targeted checks: 19 passed; expanded quantile checkpoint checks:
  8 passed. Independent density moments/limits, causality, RNG isolation, split
  leakage, protected inputs, all genuine fits, relocation/tamper and replay are covered.
- Full local regression: **497 passed**, 2 dependency deprecation warnings,
  294.65 seconds. Lint and `git diff --check` pass.
- [Implementation CI](https://github.com/aayups31/APEX/actions/runs/38285768668): **Python 3.11 and 3.12 pass**,
  including lint, all tests, both new model smoke checks and all existing artifact
  checks. Smoke evidence validates execution and cannot close research tasks.
- Both full public artifact verifiers pass with closure eligibility true. Bulk
  data, weights and ensembles remain in ignored local storage. Compact evidence,
  manifests, model cards, source maps, results and task status are committed.

Local artifact paths: `.cache/robust-tyre-final-20261012` and `.cache/tyre-forecast-research-20261012`.
Run/reload instructions: [R023 model card](../models/robust-tyre-observations-v1.md),
[R025 model card](../models/tyre-forecast-benchmark-v1.md). Evidence seal:
`63eacb4e38346f0ea0942419b6e3edf8168502388f01b8927f000ac94760bc66` in
[robust-tyre-forecast-evidence.json](robust-tyre-forecast-evidence.json).

## F. Remaining limits

R023 conditions on a Gaussian-trained parameter fit and finite particle/draw
budgets. Its raw intervals under-cover nominal 90%, and grid-boundary shape
selection is not a fully optimized Bayesian posterior. R025 predicts a proxy
computed with fixed vehicle/slip priors, over short irregular histories, within
a small CPU search budget. Energy-proxy errors cannot establish measured wheel
energy accuracy. Attention/selection weights do not establish XAI faithfulness.
Neither study establishes stable imagined rollouts, intervention validity,
autonomous race engineering or production world-model promotion.

## G. Next dependency

**R026:** freeze a broader development-event seen/unseen-track protocol, keep
event-level separation, fit preprocessing on training only, reuse the matched
model ladder and report separate track/sequence uncertainty. The current two
test tracks are both unseen, so they cannot close the seen-track half of R026.
R027/R028 explanation and feasible-counterfactual work follows its evidence.
Permanent benchmark acquisition/evaluation and a separate R2 maturity review
remain later gates. This pass stops after R023 and R025 closure.
