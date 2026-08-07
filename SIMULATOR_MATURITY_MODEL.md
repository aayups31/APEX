# APEX Simulator Maturity Model

Progress is measured by evidence, not by feature count. A later level may not be claimed while an earlier gate remains open.

| Level | Name | Capability | Required evidence | Forbidden claim |
|---|---|---|---|---|
| R0 | Deterministic fixture | Reproducible synthetic laps/races | invariant tests, seed stability, artifact lineage | “realistic” |
| R1 | Equation replications | Paper equations execute independently | equation map, unit tests, published-case reconstruction where possible | “paper reproduced” without metric match |
| R2 | Public-data descriptive model | Fits historical timing/telemetry | session-level splits, baseline comparison, uncertainty or residual report | causal counterfactuals |
| R3 | Calibrated single-car replay | Replays held-out controls and laps | distance/time alignment, section metrics, open-loop error, parameter identifiability | autonomous lap simulation |
| R4 | Stable closed-loop single car | Generates its own controls for complete laps | track closure, bounded state, intervention tests, compounding-error curves | race-strategy realism |
| R5 | Tyre/fuel/ERS race model | Multi-stint race with resource constraints | terminal energy legality, tyre thermal/wear validation, pit crossover tests | full-field realism |
| R6 | Stochastic full field | Traffic, overtaking, flags, failures, weather | distribution calibration, Monte Carlo convergence, rank/strategy robustness | deterministic certainty |
| R7 | Adaptive strategy system | DP/MINLP/MPC/RL/Monte Carlo planners | small-case optimality, regret, disturbance response, runtime | optimality without oracle |
| R8 | Multi-agent decision model | Opponent-conditioned and game-theoretic behavior | self-play stability, exploitability, unseen-opponent tests, ablations | human/team equivalence |
| R9 | Cross-domain simulator validation | Public data + game telemetry + synthetic/optimization evidence agree | pre-registered game experiments, source-domain shift analysis, causal direction tests | game equals reality |
| R10 | Research-grade public simulator | End-to-end calibrated, uncertain, reproducible and auditable | multiple held-out seasons/tracks, release benchmark, model cards, red-team report | confidential team-simulator parity |

## Quantitative gate families

### Physical feasibility

- no negative fuel, impossible battery state, non-monotone race time or teleportation;
- force, speed, temperature and wear remain inside documented envelopes;
- track closure and pit-lane geometry pass tolerances;
- regulation constraints are versioned by season.

### Predictive accuracy

Report at least:

- one-step, section-horizon, lap-horizon and stint-horizon error separately;
- MAE/RMSE plus normalized or probabilistic metrics;
- seen-track and unseen-track results;
- clean-air, traffic, pit, flag and weather regimes;
- calibration/test separation by entire event.

### Decision quality

- compare against persistence, fixed strategy, rules, random, DP/beam-search and optimization when feasible;
- report race-time regret, finishing-position distribution, constraint violations and runtime;
- test nominal and disturbed scenarios;
- measure sensitivity to model error and opponent assumptions.

### Uncertainty

- distinguish aleatoric event randomness from epistemic model uncertainty;
- report interval coverage and sharpness;
- use uncertainty in strategy ranking, not only in plots;
- abstain or widen intervals outside validated support.

## Required promotion artifacts

Every component promoted from research to the production kernel must include:

- paper/assumption ID;
- equation and unit map;
- dataset card;
- immutable training/calibration manifest;
- matched baseline table;
- ablation table;
- error-by-regime plots;
- model or component card;
- reproducible command;
- regression tests;
- rollback path.
