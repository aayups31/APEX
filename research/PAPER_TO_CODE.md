# Paper-to-Code Map

## P0: foundation papers

### FIENI_2025 — joint fuel, battery, tyre and pit strategy

**What enters APEX:** lap-wise resource states, compound legality, mass-dependent wear, nominal lap-time maps plus wear correction, mixed continuous/discrete actions, terminal resource feasibility, an exact/near-exact optimization benchmark and a fast policy.

**Code now:** `apexsim.research.fienia_strategy`, `apexsim.research.strategy_env`.

**Boundary:** the code reproduces the mathematical topology with transparent surrogate coefficients. It does not claim to reproduce the paper’s confidential nonlinear lap maps or exact MINLP result.

### TODD_2025 — tyre-energy forecasting and explainability

**What enters APEX:** four-wheel prediction targets, 0.1 s temporal framing, event-level splits, seen/unseen tracks, RNN/GRU/TFT/XGBoost comparisons, section-wise error maps, temporal feature importance and intervention explanations.

**Code now:** `apexsim.research.tyre_energy`, `apexsim.research.tyre_forecasting`.

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

**Code now:** a lightweight interpretable state-space starter. Bayesian hierarchical inference and skewed-t observation models remain planned.

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
