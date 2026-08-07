# 2. State, Action, Context and the Markov Question

> **Instructor objective:** Design a causal telemetry schema and discover when the visible state is insufficient for predicting the future.

![2. State, Action, Context and the Markov Question](../figures/02_state_action_context.png)

## The problem that earns this chapter

Suppose two cars have the same speed and throttle. One is on fresh soft tyres in dry weather; the other is on worn hards in rain. A model that sees only speed and throttle receives identical input for futures that should differ. The failure is not “the neural network needs more layers.” The state description is incomplete.

### Predict before reading

Classify each variable as state, action, context, target, or identifier: speed, throttle, rain intensity, driver number, tyre age, next speed, track name, brake. Explain any variable whose category could change depending on the system boundary.

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

State is the information the transition needs to carry. Action is the intervention being chosen. Context changes the transition but is not controlled by the agent inside the model. Identifiers describe an entity or grouping and should not automatically become numeric features.

The Markov property says the next state is conditionally independent of the distant past once the present state and action are known. Real telemetry is rarely perfectly Markov. Tyre temperature, fuel mass, setup, and previous cornering load may be hidden. A recurrent model compensates by compressing history into memory. But recurrence is not permission to ignore schema design: hidden memory cannot recover information that was never observed.

A practical state contract should be sufficient, measurable, stable across data sources, and safe to use at inference time. A variable known only after the race cannot be an input to an online simulator.

## Vocabulary that now has a job

**Concept: Markov state**
- **Meaning in plain language:** A state that contains enough information to predict the next transition when combined with the action.
- **Role inside APEX:** The ideal telemetry state; approximated using features plus history.

**Concept: Context**
- **Meaning in plain language:** An external condition that modifies dynamics.
- **Role inside APEX:** Rain, track geometry, session phase and compound.

**Concept: Identifier**
- **Meaning in plain language:** A label used for grouping or lookup, not automatically a causal feature.
- **Role inside APEX:** Session ID, driver code and event ID.

**Concept: Partial observability**
- **Meaning in plain language:** Important state exists but is not directly measured.
- **Role inside APEX:** Tyre temperature or setup may need history, proxies or latent state.


## Worked example: calculate it by hand

Consider the transition

\[v_{t+1}=v_t + (4a_t-7b_t-0.02v_t-3r_t)\Delta t\]

where `a` is throttle, `b` is brake, and `r` is rain intensity. At `v=50 m/s`, throttle `0.8`, brake `0`, rain `0.5`, and `dt=0.2`:

1. Engine contribution: `4 × 0.8 = 3.2 m/s²`.
2. Drag contribution: `0.02 × 50 = 1.0 m/s²`.
3. Rain/grip penalty: `3 × 0.5 = 1.5 m/s²`.
4. Net acceleration: `3.2 − 1.0 − 1.5 = 0.7 m/s²`.
5. Speed change: `0.7 × 0.2 = 0.14 m/s`.
6. Next speed: `50.14 m/s`.

If rain were omitted, the same visible state/action would predict `50.44 m/s`. That 0.30 m/s discrepancy is a schema problem before it is a modelling problem.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/01_units_and_shapes`

### What we are about to build

A two-feature telemetry tensor with explicit time and feature axes. The point is not the arithmetic; it is learning to make shape and semantics part of the data contract.

### Runnable implementation

```python
import numpy as np

speed_kmh = np.array([0.0, 72.0, 144.0])
speed_mps = speed_kmh / 3.6
telemetry = np.stack([speed_mps, np.array([0.0, 0.5, 1.0])], axis=1)
print("speed_mps:", speed_mps)
print("telemetry shape [time, features]:", telemetry.shape)
assert telemetry.shape == (3, 2)

```

### Observed output from the packaged solution

```text
speed_mps: [ 0. 20. 40.]
telemetry shape [time, features]: (3, 2)
```

### Read the important lines like English

**Code: speed_mps = speed_kmh / 3.6**
- **What the line is doing:** Convert a display unit into the canonical physical unit.
- **What to inspect:** The numerical values change while the physical quantity does not.

**Code: np.stack([...], axis=1)**
- **What the line is doing:** Create one row per time step and one column per feature.
- **What to inspect:** `axis=1` establishes `[time, features]`.

**Code: assert telemetry.shape == (3, 2)**
- **What the line is doing:** Turn the axis contract into an executable check.
- **What to inspect:** A shape check cannot verify feature order or units by itself.


### State and tensor trace

```text
row 0 = [0.0 m/s, 0.0 throttle]
row 1 = [20.0 m/s, 0.5 throttle]
row 2 = [40.0 m/s, 1.0 throttle]
shape = [3 time steps, 2 features]
```

If you transpose it, the shape becomes `[2 features, 3 time steps]`; the numbers still exist, but every downstream interpretation changes.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Transpose the array and remove the shape assertion. Write a function that assumes rows are time. Observe that it can compute plausible but meaningless statistics.

### Diagnose from the earliest failed contract

The earliest failed contract is axis semantics, not the model. Print shape, feature names, units, and one known row before debugging anything downstream.

### Repair and lock the repair with a test

Create a dataclass or Pydantic model that stores `feature_names`, `units`, `sample_hz`, and the array. Add tests for feature order, legal ranges, and axis length.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Flat numeric vector**
- **Choose it when:** The state is small, fixed and well documented.
- **Do not choose it when:** Variables have complex structure or missingness semantics.

**Implementation: Typed record / dataframe**
- **Choose it when:** You are ingesting and validating human-readable telemetry.
- **Do not choose it when:** You need high-throughput batched neural computation.

**Implementation: History encoder**
- **Choose it when:** The observed frame is partially Markov and recent history contains useful proxies.
- **Do not choose it when:** Missing variables are unrelated to anything observed.

**Implementation: Latent state model**
- **Choose it when:** Hidden dynamics and uncertainty must be inferred.
- **Do not choose it when:** A transparent state vector already predicts well enough.


APEX uses named tabular records at ingestion, then ordered tensors for learning. Conversion happens at an explicit boundary so readability and computational efficiency are both preserved.

## Transfer the lesson into Project APEX

The canonical contract distinguishes state features, control features, context features and identifiers. The window builder constructs history and future-control tensors without exposing future target state.

### Repository path to inspect

```text
apex_engine/src/apexsim/contracts.py
apex_engine/src/apexsim/data/features.py
apex_engine/src/apexsim/data/windows.py
```

## Connection to research

RSSMs exist partly because observations are incomplete. Their deterministic hidden state and stochastic latent state summarize what the agent believes about the world. That belief is only as good as the evidence and intervention contract supplied to it.

## Check your understanding before continuing

1. Can tyre age be state and context at the same time?
2. Why is driver ID dangerous as a direct numeric feature?
3. What evidence would show that a single telemetry frame is not Markov enough?

## Solutions and reasoning

**1.** The label depends on the chosen boundary. If tyre age evolves inside the simulator, it is state; if supplied as a fixed scenario condition, it behaves like context.
**2.** Numeric encoding invents an ordering and can let the model memorize identities instead of dynamics. Use a justified embedding or group-specific analysis.
**3.** A history-aware model consistently outperforming an equal-capacity frame model, especially after controlling leakage, suggests the past carries missing state information.

## Independent build challenge

Write the complete APEX V1 schema on paper. For every field, state its category, unit, legal range, availability at inference, and expected causal relationship.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
