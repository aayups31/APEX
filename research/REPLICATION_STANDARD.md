# APEX Replication Standard

## Three labels only

### Reproduction

Use only when the original data/code and protocol are rerun with no material methodological change.

### Replication

Use only when the same hypothesis and evaluation are tested independently with comparable data and the result falls inside a pre-declared tolerance.

### Adaptation

Use when equations, architecture or experimental ideas are transferred to APEX with different data, parameters or scope. Most current APEX paper work is an **adaptation**.

## Required paper card

Each experiment must record:

- bibliographic ID and exact version;
- claim being tested;
- equations implemented and equations omitted;
- symbol-to-code map;
- units and coordinate frames;
- source of every parameter;
- data inclusion/exclusion rules;
- split strategy;
- baselines;
- metrics and tolerance decided before running;
- compute and random seeds;
- deviations from the paper;
- result, failure analysis and status decision.

## Equation fidelity checks

1. Write dimensional units beside every state and action.
2. Test zero, minimum, maximum and reset conditions.
3. Check monotonic directions claimed by the paper.
4. Compare numerical and analytic gradients where optimization depends on smoothness.
5. Run one hand-calculated transition and store it as a regression test.
6. Separate algebraic maps from dynamic states.
7. Do not silently clip; log all feasibility projections.

## Data and leakage rules

- split by full event, not random timestamp;
- fit scalers, priors and calibration parameters on training events only;
- keep a permanently untouched benchmark season/session set;
- report seen and unseen tracks separately;
- never use future track state, pit decision or outcome as an input unless it is explicitly part of a planned control sequence;
- distinguish measured, reconstructed, imputed and proxy fields.

## Baseline ladder

Every learned model competes against the strongest applicable simple methods:

1. persistence / previous lap;
2. constant acceleration or deterministic physics;
3. linear/ridge regression;
4. tree model;
5. state-space model;
6. exact small-instance DP/beam search/MINLP;
7. current production APEX component.

A larger model is not accepted because it is novel. It must add measured value.

## Closed-loop protocol

Report:

- teacher-forced one-step error;
- open-loop multi-step error;
- closed-loop state drift;
- completion/constraint-violation rate;
- sensitivity to small action perturbations;
- planner exploitation tests;
- recovery after disturbances.

## Explainability protocol

Explanations must be evaluated for faithfulness, not only visual plausibility:

- remove or perturb the claimed important feature and measure output change;
- compare local and global importance;
- test stability across seeds and nearby states;
- validate counterfactual feasibility;
- show when no reliable explanation can be produced.

## Result status

- `FAIL`: implementation, evidence or tolerance failed.
- `INCONCLUSIVE`: confidence interval or data support is insufficient.
- `DIRECTIONAL_MATCH`: causal direction matches but magnitude does not.
- `PARTIAL_REPLICATION`: subset of claims/conditions matches.
- `REPLICATED_WITHIN_TOLERANCE`: all pre-registered primary criteria pass.

Only the last two can justify production promotion, and only within their tested domain.
