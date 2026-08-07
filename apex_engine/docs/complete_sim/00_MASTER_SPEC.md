# APEX Complete Simulation — Master Specification

## 1. Mission

Build a credible, reproducible, uncertainty-aware motorsport simulation platform from public and synthetic data without depending on telemetry from an official racing game.

APEX should support three modes:

1. **Replay:** reconstruct what happened and measure model error against recorded data.
2. **Counterfactual:** change a bounded action, condition or strategy and estimate what could have happened.
3. **Planning:** compare candidate future decisions under uncertainty and rank them by expected outcome and risk.

## 2. Definition of “complete”

A complete V1 is not a photorealistic game. It is a systems-complete race simulation containing:

- track geometry and lap progress;
- longitudinal and lateral feasibility;
- driver controls or policy;
- tyres, tyre temperature, wear and compounds;
- fuel mass and consumption;
- a simplified, explicitly uncertain energy store;
- aero/drag/downforce priors;
- weather, surface grip and wetness;
- multiple cars, gaps, traffic and overtaking opportunities;
- DRS-like drag reduction as a configurable race rule;
- pit strategy and pit time loss;
- yellow, virtual-safety-car, safety-car and red-flag state;
- race order, lap timing, finish and retirement;
- calibration from historical data;
- deterministic baselines and learned residual models;
- matched replay and rollout evaluation;
- strategy search with uncertainty;
- artifact lineage and experiment reproducibility;
- an API/UI layer that never outruns model evidence.

## 3. Scope ladder

### V0 — Delivered vertical slice

- synthetic closed track;
- six cars;
- point-mass dynamics;
- tyre grip/temperature/wear;
- fuel and simplified energy store;
- weather keyframes;
- DRS zones and eligibility;
- pits and compounds;
- race-control schedule;
- telemetry and standings;
- calibration/replay/strategy interfaces;
- unit and integration tests.

### V1 — Credible historical replay

- one season era;
- three representative circuits;
- practice/qualifying laps first;
- stable track reconstruction;
- per-track and per-driver calibration;
- recorded-control replay;
- multi-step error and physical validity report;
- confidence intervals across sessions.

### V2 — Single-car counterfactual simulation

- closed-loop driver policy;
- pace modes;
- pit entry/exit path;
- compound strategy;
- rainfall and dry-line evolution;
- learned residual world model;
- uncertainty head or ensemble;
- intervention support checks.

### V3 — Full-field race simulation

- 20 configurable entries, not licensed replicas;
- starting grid and timing loops;
- traffic, dirty air and pass probability;
- pit stacking and pit-lane congestion;
- race-control state machine;
- weather forecast uncertainty;
- Monte Carlo strategy ranking;
- race outcome calibration.

### V4 — Research-grade planner

- receding-horizon planning;
- candidate action generation;
- CEM/MPC or dynamic-programming strategy search;
- risk-sensitive objective;
- uncertainty propagation;
- off-policy evaluation;
- human-readable decision trace.

## 4. Core state

Use Frenet-like track coordinates instead of unconstrained world XY for simulation:

```text
car state x_t
  time, lap, s, lateral offset, speed, yaw error
  fuel, battery/energy proxy
  tyre compound, age, health, temperature
  damage, pit state, race status

control u_t
  throttle, brake, steering/racing-line target
  energy deployment request, drag-reduction request

context c_t
  local curvature, width, elevation/grade
  air/track temperature, rain, standing water, wind
  flag state, traffic gap, pit/rule state
```

Public telemetry may omit lateral offset, steering angle, brake pressure, tyre temperature, fuel and deployment. Those variables must be treated as latent estimates with uncertainty—not silently filled with constants and later called observations.

## 5. System decomposition

```text
Public data + synthetic generator
              ↓
Source manifests and immutable raw cache
              ↓
Source adapters and temporal alignment
              ↓
Race/lap/stint/telemetry canonical tables
              ↓
Track reconstruction + quality reports
              ↓
Parameter calibration and baseline replay
              ↓
Physics transition prior
              ↓
Learned residual / latent world model
              ↓
Driver policy + race systems
              ↓
Counterfactual rollout ensemble
              ↓
Strategy planner and decision report
              ↓
Registry, API, UI and reproducible artifacts
```

## 6. Modeling doctrine

### Begin with an inspectable prior

The deterministic simulator should explain as much as possible with:

- power-limited acceleration;
- grip-limited traction and braking;
- drag and rolling resistance;
- downforce and curvature;
- tyre/environment grip;
- mass change from fuel;
- traffic and rule constraints.

### Learn residuals, not magic

The learned model should estimate bounded corrections such as:

- speed/acceleration residual;
- track-specific aero/grip residual;
- tyre-state residual;
- driver-action distribution;
- uncertainty.

It should not be allowed to teleport the car, increase fuel, violate track boundaries or invent impossible pit states.

### Separate policy from dynamics

A world model predicts what happens after an action. A driver policy chooses the action. Race strategy chooses higher-level actions such as pace, pit timing and compound. Keeping these separate is essential for counterfactual validity.

## 7. Output contracts

Every run must produce:

```text
manifest.json        exact config, code version, data hashes, seed
quality_report.json  missingness, alignment, units, leakage checks
calibration.json     fitted parameters and confidence/fit metrics
metrics.json         replay, rollout, physical and race metrics
telemetry.parquet    simulated state/action/context timeline
laps.parquet         lap-level outcomes
stints.parquet       stint-level outcomes
standings.json       final classified result
interventions.json   every scenario change and support warning
plots/               generated evidence, not decorative claims
```

CSV is acceptable for the delivered demo. Move to Parquet when real data volume increases.

## 8. Acceptance philosophy

No milestone is passed because the dashboard “looks right.” Each gate requires:

- a frozen dataset split;
- an explicit baseline;
- an error metric at the intended rollout horizon;
- physical invariants;
- failure examples;
- artifact lineage;
- a written go/no-go decision.

## 9. Honest product language

Allowed:

> APEX is a public-data-calibrated hybrid racing simulator for replay, bounded counterfactual analysis and strategy experimentation.

Not allowed until independently demonstrated:

> APEX accurately predicts real Formula 1 race outcomes.

> APEX reproduces team-grade vehicle dynamics.

> APEX knows hidden ERS, setup or tyre state.

## 10. Success criteria for the portfolio version

The strongest portfolio demonstration is not “20 AI cars racing.” It is a traceable investigation:

1. ingest a held-out historical session;
2. reconstruct a circuit and validate lap alignment;
3. replay recorded controls through the physics prior;
4. show where the prior fails;
5. train a residual model only on training sessions;
6. reduce held-out multi-step error;
7. perform one bounded counterfactual;
8. propagate uncertainty;
9. compare strategies;
10. explain which assumptions dominate the answer.
