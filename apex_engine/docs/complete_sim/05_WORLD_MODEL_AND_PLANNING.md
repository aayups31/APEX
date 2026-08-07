# World Model and Planning

## Separate three decisions

### Dynamics

What state follows from the current state and action?

### Driver policy

What control will a driver choose at 4–10 Hz?

### Strategy policy

What high-level decision should be made over laps or race phases?

The current APEX neural code mainly addresses dynamics conditioned on future controls. The complete simulator adds driver and strategy layers.

## Driver imitation

Training targets:

- throttle and brake distribution;
- gear/drag-reduction request where observed;
- target speed or pace residual;
- racing-line/lateral target where reconstructable.

Condition on:

- upcoming curvature window;
- speed and acceleration;
- tyre/fuel latent estimates;
- weather;
- traffic gaps;
- driver and session embeddings;
- pace label inferred from context.

Evaluation:

- action error;
- closed-loop lap time;
- intervention stability;
- cross-driver/track generalization;
- policy diversity without impossible behavior.

## World-model training

Use the deterministic physics transition as an input and predict residuals. Train with:

- one-step loss;
- scheduled multi-step rollout loss;
- physical penalty terms;
- uncertainty/calibration loss;
- masks for missing/unobserved fields;
- session-level splits.

Do not train on future labels accidentally embedded in lap outcome or final classification features.

## Planner ladder

1. enumerate small pit windows;
2. dynamic programming over lap-level stint model;
3. Monte Carlo full-race evaluation;
4. CEM over continuous pit/pace actions;
5. receding-horizon MPC during replay/live mode;
6. actor-critic only after a trusted simulator exists.

The delivered `MonteCarloStrategyPlanner` already accepts a simulator factory so the planner and simulator remain decoupled.

## Objective

A risk-sensitive objective may combine:

```text
expected finishing position
expected race time
probability of retirement/invalid outcome
position or time variance
pit/tyre-rule violations
energy/fuel feasibility
```

Never optimize only expected lap time if the actual user question is finishing position under uncertain traffic and weather.

## Counterfactual support

Before accepting an intervention, compute whether it stays near observed/calibrated support:

- throttle/brake range;
- speed-curvature envelope;
- tyre age/compound range;
- weather range;
- traffic gap range;
- track/driver embeddings;
- action-sequence likelihood.

Return warnings such as:

```text
SUPPORTED
WEAK_SUPPORT
EXTRAPOLATION
PHYSICALLY_REJECTED
RULE_REJECTED
```

## Uncertainty

Minimum acceptable method: ensemble of independently initialized residual models plus stochastic scenario draws. Report:

- median outcome;
- 50% and 90% intervals;
- ensemble disagreement;
- sensitivity to major assumptions;
- rank stability across rollout budgets.

A single smooth line is not a strategy forecast.
