# R026 frozen seen/unseen-track evaluation

## A. Outcome and baseline

**R026 DONE**, 2026-10-13. Research inventory **26/73 DONE**; build inventory
**13/66 DONE**. Scoped research maturity remains R1 and production kernel R0.
No R2 or production promotion follows. R027/R028 remain pending P1 work.

Baseline c62a5bc: fresh497 tests pass264.73s. The synthetic research preview
runs, and all six cars finish the six-lap race with quality checks passing.
The legacy synthetic ridge preview emits an existing conditioning warning;
the frozen public evaluation uses existing verified weights and performs no fit.
User `artifacts/` are preserved. Preregistration a80a513 precedes all new telemetry
acquisition/outcome inspection. Implementation 5a00fd2acc4749a760e773901e830b8062a78d31 is pushed to main.

## B. Frozen study and source provenance

The [protocol](../../research/protocols/TRACK_GENERALIZATION.md) freezes four
2023 DEVELOPMENT races before acquisition: Bahrain/Australia seen circuits,
Monza/Singapore unseen circuits. Train/validation/checkpoints remain the R025
2024 study, summary `c8f538d7ae46ec06a46d9af1b37fb9e4fe7429ac3c942845976fe2ccf189fe9f`. No retraining, scaler or
vocabulary fitting, calibration or test-driven model choice occurs.

Both evaluation strata share2023, preventing a season label from being assigned
only to one stratum. It remains a retrospective 2024-trained/2023-tested study,
not a prospective forecast campaign. Circuit novelty derives from the actual
training vocabulary. Event/name/date/round identities agree between the frozen
Jolpica calendar and FastF1 metadata. The
[official completed race results](https://www.formula1.com/en/results/2023/races)
support the race dates; archived provider numbering supplies exact query IDs.
The nine permanent whole-event benchmarks remain protected and unacquired.

All four trusted full native archives verify and reproduce **46 tables each**
in fresh offline workers, with **zero network attempts and no mismatches**.
Complete manifests, source notes, environments and replay seals are in the
[evidence JSON](track-generalization-evidence.json). Source hashes demonstrate
local consistency rather than provider authentication.

## C. Dataset and implementation

Reuse R021's exact clean-dry retrospective mask and R024's source-bound motion/
energy equations, support thresholds, vehicle/slip priors and50-field labels.
The configuration matches R024 byte for byte. Drivers4/44 remain fixed, without
event/driver replacement or relaxed exclusions. Their **317 eligible laps**
yield **91,059 proxy samples** in **6,054 sequences**
from **320,562 native car rows**; every rejected row has a reason.
The all-driver lap mask is separately preserved; its all-driver count is not the
selected-driver evaluation count. Measured wheel quantities remain null UNKNOWN.

| Event | Circuit ID | Accepted proxy samples | Complete matched origins |
| --- | --- | --- | --- |
| F1_2023_R01 | bahrain | 23,207 | 10,352 |
| F1_2023_R03 | albert_park | 20,792 | 8,538 |
| F1_2023_R14 | monza | 25,089 | 12,795 |
| F1_2023_R15 | marina_bay | 21,971 | 9,979 |

There are **41,664 total matched origins**, each
with four wheel targets at1/3/5 native samples. No event/driver/stint/compound or
native-row discontinuity is bridged. Eight past samples and the original training
scaler/vocabulary are reused; new categories map to UNKNOWN. Native times remain
irregular. Actual horizon quantiles are recorded separately by stratum; median
durations are approximately0.240/0.760/1.281s seen and0.240/0.761/1.319s unseen.

All six fitted families reuse **ten frozen checkpoints**. Persistence and causal
last-three-energy trend use identical origins. Raw and common nonnegative
projected outputs are saved with correction counts/magnitudes. TFT raw/projected
quantiles and all per-wheel/horizon/event diagnostics remain inspectable.
The extended explicit-cohort/window plumbing preserves the original R025 replay;
no neural architecture, proxy equation or frozen weight is changed.

## D. Separate confidence and results

Primary RMSE is sqrt(mean(event MSE)), giving events equal weight. Family values
average errors across their fixed seeds on the same observations; they are not
ensemble predictions or independent data. Separate frame-weighted metrics,
individual seeds and per-wheel/horizon/event scores are retained in the evidence.

Confidence uses500 hierarchical replicates, seed2026: resample events, then whole
sequence clusters within sampled events. Model/persistence comparisons share
sampled clusters. **Only two events/circuits per stratum** make these descriptive
cohort intervals; they cannot establish broad population coverage or a causal
effect of circuit novelty.

### Seen circuits

18,890 matched origins; 1,260 sequence clusters; two events/circuits.

| Method | Equal-event RMSE (kJ) | 95% RMSE interval (kJ) | Paired MSE minus persistence, 95% interval (kJ squared) | Frame MAE (kJ) | Frame SMAPE |
| --- | --- | --- | --- | --- | --- |
| persistence | 3.498040 | [2.226228, 4.483824] | [0.000000, 0.000000] | 1.495542 | 74.22% |
| trend | 6.621941 | [4.176698, 8.547476] | [12.404596, 52.951229] | 2.352932 | 112.89% |
| linear | 2.495465 | [1.733946, 3.117641] | [-10.445691, -1.903839] | 1.307986 | 88.47% |
| ridge | 2.495447 | [1.733891, 3.117613] | [-10.445716, -1.904011] | 1.307942 | 88.46% |
| xgboost | 2.207045 | [1.489746, 2.793432] | [-12.379600, -2.724774] | 1.054551 | 68.46% |
| gru | 2.394449 | [1.607997, 3.022645] | [-11.015960, -2.358053] | 1.186562 | 81.20% |
| lstm | 2.385185 | [1.592591, 3.017817] | [-11.039334, -2.406874] | 1.170776 | 78.74% |
| tft | 2.427705 | [1.577368, 3.094289] | [-10.581751, -2.439658] | 1.004321 | 65.35% |
### Unseen circuits

22,774 matched origins; 1,315 sequence clusters; two events/circuits.

| Method | Equal-event RMSE (kJ) | 95% RMSE interval (kJ) | Paired MSE minus persistence, 95% interval (kJ squared) | Frame MAE (kJ) | Frame SMAPE |
| --- | --- | --- | --- | --- | --- |
| persistence | 2.250392 | [1.993006, 2.489108] | [0.000000, 0.000000] | 1.054673 | 73.41% |
| trend | 4.211813 | [3.642835, 4.766250] | [9.230465, 16.483795] | 1.656975 | 110.09% |
| linear | 2.068797 | [2.003045, 2.129824] | [-1.768421, 0.153351] | 1.322184 | 96.54% |
| ridge | 2.068577 | [2.002837, 2.129583] | [-1.769076, 0.152308] | 1.321969 | 96.53% |
| xgboost | 2.045111 | [1.867340, 2.210209] | [-1.381964, -0.452991] | 1.162415 | 80.50% |
| gru | 2.081024 | [1.994472, 2.155719] | [-1.571061, 0.062819] | 1.274339 | 93.09% |
| lstm | 2.069289 | [1.972269, 2.154638] | [-1.573485, -0.022751] | 1.182052 | 94.33% |
| tft | 1.872537 | [1.702351, 2.037719] | [-2.070182, -1.063500] | 0.949431 | 76.22% |

The validation-selected XGBoost family improves equal-event RMSE by
**36.91% seen** and
**9.12% unseen** versus
persistence, with both paired MSE upper95% bounds negative. Frozen decision:
**SUPPORTED_IN_FROZEN_DEVELOPMENT_COHORT**. This supports the specified development
cohort only and does not promote the simulator.

Tradeoffs remain visible. XGBoost has worse unseen MAE/SMAPE than persistence.
Linear/ridge/GRU unseen paired intervals cross zero, despite lower point RMSE.
TFT has the lowest descriptive unseen RMSE but is not selected using this test.
XGBoost's unseen-minus-seen equal-event MSE gap is -0.688567
kJ squared, 95% interval[-3.624887, 2.342636].
Its interval crosses zero, and easier/harder event regimes confound track novelty.

TFT intervals are native, uncalibrated nominal80% intervals:

| Checkpoint | Stratum | Actual coverage | Mean width (kJ) |
| --- | --- | --- | --- |
| tft_seed11 | seen | 82.55% | 3.225429 |
| tft_seed11 | unseen | 72.92% | 2.550096 |
| tft_seed23 | seen | 82.54% | 3.104852 |
| tft_seed23 | unseen | 74.90% | 2.766044 |

Coverage is about82.5% seen and73–75% unseen. Lower proxy RMSE does not establish
calibrated uncertainty or measured wheel-energy accuracy.

## E. Verification and version control

- **28 targeted checks pass** in32.12s; hand-calculated event balancing, fixed
  seed-loss aggregation, cluster duplication/RNG isolation, causality, protected
  cohorts, no held-out fitting, all families, portable replay and tamper/reseal
  refusal are covered.
- **508 full regression tests pass** in176.24s, with2 dependency deprecation
  warnings. Lint and diff checks pass.
- [Implementation CI](https://github.com/aayups31/APEX/actions/runs/38346434021): **Python3.11/3.12 pass**, including
  the new seen/unseen frozen-inference and confidence smoke step. SIMULATED
  execution checks cannot close this public study.
- The public dataset verifies; all **ten inference checkpoints and TFT quantiles**
  replay on the complete evaluation set without original caches or fitting.
  Saved scalar diagnostics, bootstrap confidence and the frozen decision reproduce.
- Independent NumPy auditing of saved public outputs reproduces all frame and
  event-macro errors, family loss aggregation, projection and quantile coverage.
  Every copied checkpoint is byte-identical to the original R025 weight file.

Dataset seal: `c2d1eb5b8cfea3f57d64869015b3f4551ad91debb6a638a64b138a2f223baaa6`.
Evaluation summary seal: `f565de0903a71ca19a6dc753fc96ffeb82410d11c00e317bb071ee3fc02bec18`.
Evidence seal: `bc50c937ea66783a600d06f320e01fc1d4df8476d1446615ab0a22b2fc8bb0ca`.
Bulk source caches/windows/predictions/weights remain ignored locally:
`.cache/r026-proxy-public-20261013` and `.cache/r026-track-generalization-research-20261013`. Compact evidence, reports and task status are committed.

[Dataset card](../data/track-generalization-proxy.md),
[model/run card](../models/track-generalization-v1.md), and
[engineering target](../project/engineering-target.md) explain use and limits.

## F. Limits and engineering relevance

The study tests reproducible transfer of short-history PROXY forecasts, not
proprietary measured tyre energy or actual wear. Public fields may contain
provider reconstructions; vehicle/slip parameters remain fixed priors. Temporal,
driver/car, layout and regime changes prevent a causal novelty claim. The two
events per stratum are far too few for broad seasonal guarantees. TFT uncertainty
transfer remains weak on unseen circuits. No future test retuning occurred.

This adds an auditable generalization check useful to an engineering reviewer.
It does not establish team interest, high-fidelity recorded-control replay,
validated imagined dynamics, autonomous race engineering or strategy value.
Those require their independent later calibration/closed-loop/optimization gates.

## G. Next priority

**R029 track reconstruction** is the earliest remaining dependency-ready P0
under the Master Build Guide's priority rule. R027 explanation faithfulness and
R028 feasible counterfactuals remain pending P1 research tasks, not completed or
removed. The preregistration's provisional next-work note did not change the
scientific cohort, weights, thresholds or outcomes. Subsequent work must turn
public position data into a validated curvilinear track before vehicle replay
calibration; explanation/counterfactual work retains its separate acceptance gates.
This pass stops after R026 closure.
