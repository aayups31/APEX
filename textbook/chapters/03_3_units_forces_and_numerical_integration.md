# 3. Units, Forces and Numerical Integration

> **Instructor objective:** Build a physically interpretable transition, use dimensional analysis to catch errors, and understand the limits of toy physics.

![3. Units, Forces and Numerical Integration](../figures/03_physics_integrator.png)

## The problem that earns this chapter

Telemetry sources use kilometres per hour, metres per second, percentages, normalized controls, degrees, radians and timestamps in different formats. A model can fit unit mistakes without raising an exception. The result may look statistically smooth while violating the world.

### Predict before reading

A formula subtracts `0.02 * speed²` from acceleration, but speed is supplied in km/h although the coefficient was fitted in m/s. Predict whether the drag is too large or too small and by what factor.

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

Dimensional analysis asks whether the units on both sides of an equation agree. It is one of the cheapest and strongest debugging tools in simulation engineering. If force is in newtons and mass is in kilograms, acceleration is metres per second squared. If speed enters a squared term, a unit conversion error is squared too.

A toy longitudinal model combines engine force, braking force and drag. It will not reproduce downforce, tyre load sensitivity, energy recovery, differential behaviour or setup effects. That is fine when the model's purpose is to generate causal examples and test software contracts. It is dangerous if the UI presents the result as lap-time truth.

The hand-written model also teaches residual learning: instead of asking a neural network to rediscover every obvious relationship, we can predict the correction to a known physics approximation. Whether that helps is an empirical decision.

## Vocabulary that now has a job

**Concept: Dimensional analysis**
- **Meaning in plain language:** Check that quantities combined by an equation have compatible units.
- **Role inside APEX:** Catches km/h–m/s and timestamp errors before training.

**Concept: Force balance**
- **Meaning in plain language:** Net force is the sum of propulsive and resisting forces.
- **Role inside APEX:** Provides an interpretable synthetic transition.

**Concept: Residual model**
- **Meaning in plain language:** A learned correction added to a known baseline model.
- **Role inside APEX:** Possible hybrid physics/ML architecture.

**Concept: Numerical stability**
- **Meaning in plain language:** Whether repeated computation remains bounded and sensible.
- **Role inside APEX:** Critical for long autoregressive rollouts and SSM state.


## Worked example: calculate it by hand

Suppose the drag acceleration term is \(c v^2\). Converting from m/s to km/h multiplies speed by 3.6. Squaring multiplies the drag term by \(3.6^2=12.96\). The model therefore applies nearly thirteen times too much drag.

For a 50 m/s car with mass 800 kg:

- Engine force: 8,000 N
- Brake force: 0 N
- Drag: 2,500 N
- Net force: 5,500 N
- Acceleration: `5500 / 800 = 6.875 m/s²`
- At `dt=0.1`, velocity increases by `0.6875 m/s`

If speed were incorrectly treated as 180 in a coefficient calibrated for 50, the quadratic term would dominate and could create impossible negative velocity.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/03_force_model`

### What we are about to build

A longitudinal force model with engine, brake and aerodynamic drag contributions. You will inspect every term separately before summing them.

### Runnable implementation

```python
from education.core import CarState, step_car

state = CarState(0.0, 0.0, 40.0)
for i in range(5):
    state = step_car(state, throttle=0.7, brake=0.0, dt=0.1)
    print(i, state)

```

### Observed output from the packaged solution

```text
Traceback (most recent call last):
  File "/mnt/data/Project_APEX_Engineering_Apprenticeship/labs/03_force_model/solution.py", line 1, in <module>
    from education.core import CarState, step_car
ModuleNotFoundError: No module named 'education'
```

### Read the important lines like English

**Code: engine = max_engine_force * throttle**
- **What the line is doing:** Scale available forward force by a normalized control.
- **What to inspect:** Throttle range must be validated as 0–1.

**Code: drag = drag_coefficient * speed**2**
- **What the line is doing:** Apply a quadratic resistance that grows rapidly with speed.
- **What to inspect:** The coefficient depends on the speed unit.

**Code: acceleration = net_force / mass**
- **What the line is doing:** Use Newton’s second law to convert force into acceleration.
- **What to inspect:** Mass must be positive and use kilograms.


### State and tensor trace

```text
throttle ──► engine force ─┐
brake ─────► brake force ──┼─► net force ─► divide by mass ─► acceleration
speed ─────► drag force ───┘
```

At every arrow, annotate the unit. That annotation is an executable design review even before a test exists.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Feed speed in km/h without conversion. Then set mass to zero or throttle above one. Observe which failures become exceptions and which silently produce nonsense.

### Diagnose from the earliest failed contract

Start with invariants: mass > 0, 0 ≤ controls ≤ 1, speed unit known, drag ≥ 0, and braking should not increase velocity. Then inspect individual force terms.

### Repair and lock the repair with a test

Introduce typed conversion functions, range validation, and property tests: increasing brake at fixed state must not increase next speed; increasing throttle must not decrease it in a regime without traction limits.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Pure hand-written physics**
- **Choose it when:** You need interpretability, counterfactual control and known equations.
- **Do not choose it when:** Unknown tyre/track interactions dominate error.

**Implementation: Pure learned dynamics**
- **Choose it when:** You have broad representative data and care about predictive fit.
- **Do not choose it when:** Safety or extrapolation requires hard physical guarantees.

**Implementation: Residual learning**
- **Choose it when:** A baseline captures broad physics and data can learn systematic corrections.
- **Do not choose it when:** The baseline is badly misspecified and constrains learning in the wrong direction.

**Implementation: Physics-informed loss**
- **Choose it when:** Violations can be expressed as differentiable penalties.
- **Do not choose it when:** The penalty is only a weak proxy and overwhelms observed evidence.


APEX V1 uses the toy force model to create controllable offline data, while the predictive models learn directly from canonical telemetry. Physical validity checks remain part of evaluation rather than being assumed from the architecture.

## Transfer the lesson into Project APEX

Inspect how the synthetic generator computes curvature demand, grip, drag, controls and state updates. Then compare those equations with the features available to the learned models.

### Repository path to inspect

```text
projects/03_lap_physics/main.py
apex_engine/src/apexsim/data/synthetic.py
apex_engine/src/apexsim/evaluation.py
```

## Connection to research

World models often optimize data likelihood or prediction error, not the laws of mechanics. Adding inductive bias can improve sample efficiency, but every constraint is a claim that must be tested under the target domain.

## Check your understanding before continuing

1. Why can two unit errors cancel during training but still fail in deployment?
2. What is the advantage of predicting a residual?
3. Name one invariant that should hold for all APEX rollouts.

## Solutions and reasoning

**1.** A model can learn coefficients adapted to the mistaken training scale; a different source or UI conversion changes the scale and exposes the mismatch.
**2.** The baseline supplies known structure, so the learner spends capacity on unmodelled effects and can be easier to interpret.
**3.** Examples include finite values, nonnegative speed, track progress wrapped into its legal interval, and controls within their defined range.

## Independent build challenge

Add a tyre-grip limit to the force model. Show a case where more throttle no longer produces more acceleration, and explain why a monotonicity test must be conditional rather than universal.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
