# Build Plan

This plan assumes part-time work during a study term. Each phase has an artifact and a go/no-go gate.

## Phase 0 — Understand the delivered vertical slice

**Goal:** You can explain and modify every equation in `sim_core`.

Build:

- run tests and demo;
- graph speed, controls, tyre state, fuel, DRS and position;
- remove one subsystem at a time;
- write five expected-cause experiments.

Exit artifact: `V0_UNDERSTANDING_REPORT.md`.

## Phase 1 — Real-data acquisition and contracts

Build:

- versioned download manifests;
- FastF1 single-session downloader;
- OpenF1 full-field downloader;
- Jolpica metadata fetcher;
- canonical Parquet tables;
- alignment and quality report.

Exit gate: A.

## Phase 2 — Track reconstruction

Build:

- accurate-lap filtering;
- lap-distance alignment;
- median reference line;
- signed curvature;
- closure/length uncertainty;
- pit and DRS zones.

Exit gate: B.

## Phase 3 — Recorded-control replay

Build:

- coasting/braking/acceleration segment extraction;
- longitudinal parameter fit;
- track grip fit;
- replay dashboard;
- matched baselines;
- per-track failure report.

Exit gate: C.

## Phase 4 — Driver policy

Build:

- curvature target-speed baseline;
- behavior cloning dataset;
- GRU/MLP action model;
- policy rollout constraints;
- held-out driver/track tests.

Exit gate: D.

## Phase 5 — Tyres, fuel and weather

Build:

- stint table;
- compound-specific degradation model;
- warmup proxy;
- fuel correction;
- wetness/dry-line state;
- uncertainty ranges.

Exit artifact: calibrated stint simulator.

## Phase 6 — Hybrid residual world model

Build:

- frozen physics prior dataset;
- residual targets;
- linear/XGBoost baseline;
- GRU residual;
- RSSM/SSM only if justified;
- ensemble uncertainty;
- support detector.

Exit gate: E.

## Phase 7 — Multi-car race systems

Build:

- vectorized state;
- traffic and pass opportunity;
- pit-lane path and queues;
- race-control state machine;
- 20-car performance tests;
- full-field replay.

Exit gate: F.

## Phase 8 — Strategy planner

Build:

- enumerated one/two-stop candidates;
- Monte Carlo weather/traffic;
- objective and risk measure;
- rollout budget study;
- synthetic known-optimum benchmark;
- CEM/MPC if needed.

Exit gate: G.

## Phase 9 — Product layer

Build:

- race replay timeline;
- evidence-linked scenario editor;
- uncertainty bands;
- strategy comparison;
- run/model/data provenance;
- limitation and support warnings.

Exit gate: H.

## First 30 build sessions

1. Run and inspect demo telemetry.
2. Draw every state transition.
3. Unit-test coasting.
4. Unit-test braking.
5. Unit-test curvature limit.
6. Unit-test tyre wet mismatch.
7. Add plots for V0.
8. Build source manifest schema.
9. Download one FastF1 session locally.
10. Save raw hash and session metadata.
11. Extract one accurate lap.
12. Validate units and timestamps.
13. Build first track map.
14. Plot closure and curvature.
15. Replay recorded controls.
16. Measure horizon error.
17. Extract coasting segments.
18. Fit drag/rolling prior.
19. Extract braking segments.
20. Fit braking envelope.
21. Extract acceleration segments.
22. Fit power prior.
23. Freeze physics-v1 config.
24. Build persistence baseline.
25. Build constant-acceleration baseline.
26. Build linear residual baseline.
27. Compare matched horizons.
28. Write failure analysis.
29. Choose next model from evidence.
30. Publish first technical report/demo.
