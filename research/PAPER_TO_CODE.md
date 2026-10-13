# Paper-to-Code Map

## P0: foundation papers

### FIENI_2025 — joint fuel, battery, tyre and pit strategy

**What enters APEX:** lap-wise resource states, compound legality, mass-dependent wear, nominal lap-time maps plus wear correction, mixed continuous/discrete actions, terminal resource feasibility, an exact/near-exact optimization benchmark and a fast policy.

**Code now:** `apexsim.research.fienia_strategy`, `apexsim.research.strategy_env`.

**Boundary:** this is an adaptation with transparent surrogate coefficients.
The [equation review](equations/FIENI_2025.md) and frozen hand fixtures record
matches, corrections and omissions. Tiny finite-grid enumeration benchmarks the
approximate beam; neither supplies the paper's nonlinear lap maps or MINLP result.

### TODD_2025 — tyre-energy forecasting and explainability

**What enters APEX:** four-wheel prediction targets, 0.1 s temporal framing, event-level splits, seen/unseen tracks, RNN/GRU/TFT/XGBoost comparisons, section-wise error maps, temporal feature importance and intervention explanations.

**Code now:** `apexsim.research.tyre_energy`, `apexsim.research.tyre_forecasting`.

R024 adds `apexsim.research.tyre_energy_dataset`: a source-bound causal proxy
dataset on five development races, with 50 labelled fields, UNKNOWN measured
wheel targets and complete source-row accounting. Its
[report](../docs/verification/tyre-energy-dataset-report.md) records native
irregular sampling and short-sequence limits. R025 adds
`apexsim.research.forecast_benchmark` and `temporal_fusion`: all six families
train genuinely on matched causal histories, with validation-only selection and
checkpoint replay. The [architecture map](equations/TEMPORAL_FUSION_PROXY_V1.md)
and [comparison report](../docs/verification/robust-tyre-forecast-report.md)
retain actual model rankings and proxy-target limits. R026's
`apexsim.research.track_generalization` adds frozen-weight cross-season seen/unseen
scores and hierarchical event/sequence confidence. Its
[report](../docs/verification/track-generalization-report.md) records limited
cohort support and weak unseen quantile coverage. Explanation faithfulness and
feasible counterfactuals remain separate pending work.

**Boundary:** measured tyre energy is proprietary. The included estimator is a physics-informed proxy useful for interface and experiment development; it must never be labelled as ground truth.

### HEILMEIER_2018 + HEILMEIER_2020_MC — race kernel and stochastic events

**What enters APEX:** lap-wise race orchestration, tyre/fuel/pit effects, overtaking, probabilistic lap and pit variation, accidents/failures, full-course-yellow/safety-car logic and Monte Carlo strategy robustness.

**Code now:** `apexsim.sim_core.race`, `strategy`, `weather`; distribution identification and safety-car calibration remain work items.

### DUHR_2023 — hybrid power-unit energy allocation

**What enters APEX:** resource-constrained minimum-race-time energy allocation, lap maps, terminal energy targets and shrinking-horizon response to disturbances.

**Code now:** battery/fuel feasibility and action projection in `fienia_strategy`; a sector-level ERS optimizer remains to be built.

### PERANTONI_2014 — minimum-lap-time vehicle optimal control

**What enters APEX:** curvilinear track coordinates, vehicle state equations, direct transcription, nonlinear constraints, racing-line/control co-optimization and track-specific setup sensitivity.

**Code now:** transparent track/vehicle crosswalk only. This paper defines the upgrade path from the current point-mass kernel to a validated minimum-lap-time solver.

### TREMLETT_2016 + WEST_2020 + FARRONI_2017 — tyre thermodynamics and wear

**What enters APEX:** carcass/surface temperature states, heat generation and transfer, temperature-dependent grip, sliding-energy wear, load sensitivity and multi-lap tyre management.

**Code now:** bounded temperature/wear states and a four-wheel sliding-energy proxy. The full thermodynamic optimal-control model is protocol-defined, not reproduced.

### CAPPELLO_2025 — probabilistic latent degradation

**What enters APEX:** fuel-corrected lap-time observations, latent tyre pace, stint resets, robust observation noise, predictive distributions and rolling-origin validation.

**Code now:** `apexsim.research.tyre_pace` and `hierarchical_tyre` add training-only
Gaussian state fitting, causal rolling forecasts and conditional Bayesian
compound/track/driver inference. R021/R022 use five non-benchmark development races;
the [report](../docs/verification/tyre-degradation-report.md) retains the nominal
90% coverage shortfall. This is an independently specified Gaussian adaptation
motivated by the reviewed abstract, not a full-paper replication. The legacy
starter remains educational. R023 adds `apexsim.research.skew_tyre`: the
[Hansen density and conditional particle filter](equations/ROBUST_TYRE_OBSERVATIONS_V1.md)
retain Gaussian-trained group draws/Q/R. The robust comparison is accepted for
conditional research, with raw interval undercoverage and no production promotion.

### THOMAS_2025 — explainable race-strategy RL

**What enters APEX:** portable strategy states/actions, finishing-position objective, seen/unseen-track evaluation, feature importance, surrogate policy explanations and counterfactual explanations.

**Code now:** unified interface and reward topology. Full training and result reproduction require the specified race environment and evaluation campaign.

### FIENI_2026_MULTI + WUTHRICH_2026_RLMPC — multi-agent and hybrid online planning

**What enters APEX:** aerodynamic interaction, opponent-conditioned strategy, self-play, discrete pit decisions from a policy, continuous energy refinement by MPC, warm starts, terminal critic and disturbance adaptation.

**Code now:** the interfaces and single-agent mathematical core. This is the target strategy architecture after R6, not the first implementation milestone.

## P1: strengthening papers

- **HEINE_2023:** exact dynamic-programming oracle for small pit-strategy instances.
- **AGUAD_2024:** Stackelberg/game-theoretic strategy and risk-aware winning probability.
- **HEILMEIER_2020_VSE:** learned pit/no-pit and compound decision imitation.
- **BOTTINGER_2023:** Gym-style race environments, observation/reward ablations and historical calibration.
- **PlaNet, DreamerV3, TD-MPC2:** latent dynamics, imagination and continuous planning.
- **Iso-Dream:** factorize controllable ego dynamics from opponents, weather and race-control dynamics.

## P2: reference models

- **Pacejka 1989:** force-slip envelope and tyre-force sanity checks. It is not a wear model.
- Higher-detail tyre and vehicle models should be added only when their parameters are identifiable from available evidence or explicitly treated as uncertain priors.

## Final hybrid stack

```text
minimum-lap-time / transparent physics prior
             +
probabilistic hidden-state estimators
             +
learned residual dynamics
             +
stochastic race-event model
             +
exact small-case or optimization oracle
             +
fast RL/world-model policy
             +
MPC constraint and energy refinement
```

No one paper is sufficient for the complete simulator. The value of APEX is the controlled integration and cross-validation of these research families.
