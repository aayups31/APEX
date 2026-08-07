# Evaluation and Acceptance Gates

## Evaluation pyramid

### Layer 1 — Data integrity

- units correct;
- timestamps monotonic;
- sampling gaps marked;
- lap boundaries correct;
- no duplicate frames;
- joins within tolerance;
- train/test sessions disjoint.

### Layer 2 — Physical invariants

- speed, fuel, battery and tyre health remain bounded;
- no backward lap teleportation;
- track closure holds;
- pit state transitions are legal;
- friction demand is finite;
- fixed seed is reproducible.

### Layer 3 — Component replay

- coasting deceleration;
- braking envelope;
- acceleration envelope;
- corner speed;
- tyre degradation;
- pit loss;
- weather effect.

### Layer 4 — Multi-step replay

Evaluate horizons in seconds and track distance, not only steps:

- speed MAE/RMSE;
- acceleration MAE;
- lap-distance error;
- lap-time error;
- horizon error curve;
- uncertainty coverage.

### Layer 5 — Closed-loop lap

- completion rate;
- lap-time error;
- speed-profile similarity;
- control realism;
- physical violation count;
- stability over repeated laps.

### Layer 6 — Race outcome

- lap/position trajectory error;
- pit timing reproduction;
- stint pace/degradation;
- final classification/rank correlation;
- event calibration;
- strategy regret against held-out outcomes where meaningful.

## Mandatory baselines

- persistence speed;
- constant acceleration;
- curvature speed envelope;
- linear/Ridge transition;
- deterministic physics prior;
- historical average stint degradation;
- no-traffic race.

## Acceptance gates

### Gate A — Data adapter

Pass when one event can be rebuilt from a clean cache with >99% schema-valid rows, documented join tolerances and zero session leakage.

### Gate B — Track map

Pass when closure error is small, reconstructed length is stable across laps, curvature is finite and held-out laps project consistently.

### Gate C — Physics replay

Pass when recorded-control replay beats constant-acceleration over matched horizons and every parameter has a plausible range/uncertainty note.

### Gate D — Closed-loop driver

Pass when the policy completes held-out laps with no physical violations and beats the reference driver on imitation/trajectory evidence—not just lap time.

### Gate E — Hybrid world model

Pass when the residual model materially improves held-out multi-step replay over the frozen physics prior and uncertainty intervals are calibrated.

### Gate F — Multi-car race

Pass when 20-car races complete reproducibly, position ordering is valid, pit/flag transitions pass tests and runtime meets the target.

### Gate G — Strategy planner

Pass when strategy rankings are stable across increased rollout budgets and recover known synthetic optima before any real-race claim.

### Gate H — Product demo

Pass when every chart links to run ID, dataset/model version, uncertainty and limitations.

## Red-team tests

- impossible throttle+brake sequence;
- zero grip;
- heavy rain on slicks;
- depleted fuel/energy;
- duplicated/out-of-order telemetry;
- 30-second source gap;
- unseen track;
- unseen driver;
- safety-car during pit window;
- all cars pit simultaneously;
- intervention outside training support;
- residual model proposes impossible state.

## Current delivered verification

The complete-simulation edition adds six tests to the original six. The delivered package passes **12 tests** and the demo produces a completed six-car race with telemetry, pit events and standings. This verifies code execution, not real-world accuracy.
