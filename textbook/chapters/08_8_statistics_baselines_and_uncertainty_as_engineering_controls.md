# 8. Statistics, Baselines and Uncertainty as Engineering Controls

> **Instructor objective:** Use simple models and residual analysis to determine what the data contains before escalating to deep sequence architectures.

![8. Statistics, Baselines and Uncertainty as Engineering Controls](../figures/07_baseline.png)

## The problem that earns this chapter

A GRU can produce a low loss for the wrong reason: leaked targets, easy persistence, narrow test conditions or an imbalanced metric. A baseline is the control group that tells you whether complexity has earned its place.

### Predict before reading

At 5 Hz, speed changes slowly between adjacent frames. Which will be harder to beat for one-step speed prediction: a constant mean, persistence (`next speed = current speed`), or a linear action-conditioned model? Explain how the answer may change at a longer horizon.

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

Start with the distribution: means, spreads, missingness, correlations and conditional relationships. Then create baselines that correspond to real hypotheses. Persistence says the world changes slowly. Linear regression says the change is approximately additive in observed features. A physics baseline says known equations explain most of the transition.

Residuals—target minus prediction—show what the baseline failed to explain. Plot residuals against speed, curvature, rain, tyre age and horizon. Structured residuals are a blueprint for the next model. Random-looking residuals near measurement noise may mean a larger model has little room to help.

Uncertainty has several meanings. Aleatoric uncertainty reflects inherently variable outcomes or noisy measurements. Epistemic uncertainty reflects lack of knowledge, often rising outside the training distribution. A point predictor does not automatically communicate either.

## Vocabulary that now has a job

**Concept: Persistence baseline**
- **Meaning in plain language:** Predict that the next state equals the current state.
- **Role inside APEX:** Strong short-horizon speed control.

**Concept: Residual**
- **Meaning in plain language:** Observed target minus model prediction.
- **Role inside APEX:** Reveals missing nonlinearities, context or delay.

**Concept: Calibration**
- **Meaning in plain language:** Predicted uncertainty/probability matches empirical frequency or error.
- **Role inside APEX:** Needed before presenting confidence in imagined futures.

**Concept: Distribution shift**
- **Meaning in plain language:** Deployment evidence differs from training evidence.
- **Role inside APEX:** New tracks, weather, drivers or game telemetry.


## Worked example: calculate it by hand

Suppose true next speeds are `[50.2, 60.1, 69.7]` and persistence predicts `[50.0, 60.0, 70.0]`.

Absolute errors are `[0.2, 0.1, 0.3]`; MAE is `(0.2+0.1+0.3)/3 = 0.2 m/s`.

A neural model with MAE 0.18 improves by 0.02 m/s, or 10% relative. That gain might matter—or it might vanish on a new session, cost far more compute, and introduce physical violations. Compare by horizon, subgroup, latency and stability before declaring victory.

If residuals under braking average +0.8 m/s (targets are higher than predictions), the baseline is overestimating deceleration. That points to brake scaling, delay or grip context.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/05_regression_baseline`

### What we are about to build

Fit a Ridge transition model to synthetic speed, throttle and brake data, inspect coefficients and calculate test MAE.

### Runnable implementation

```python
import numpy as np
from sklearn.linear_model import Ridge

rng=np.random.default_rng(4)
speed=rng.uniform(20,80,1000)
throttle=rng.uniform(0,1,1000)
brake=rng.uniform(0,1,1000)
y=speed + 0.7*throttle - 1.1*brake - 0.0008*speed**2 + rng.normal(0,0.05,1000)
X=np.column_stack([speed,throttle,brake])
model=Ridge(alpha=1.0).fit(X[:800],y[:800])
print("coefficients:", model.coef_)
print("test MAE:", np.mean(np.abs(model.predict(X[800:])-y[800:])))

```

### Observed output from the packaged solution

```text
coefficients: [ 0.91911817  0.68984381 -1.03384695]
test MAE: 0.18453407932904015
```

### Read the important lines like English

**Code: X=np.column_stack([speed,throttle,brake])**
- **What the line is doing:** Construct one row per transition with named causal inputs.
- **What to inspect:** Column order must match stored feature metadata.

**Code: Ridge(alpha=1.0).fit(X[:800],y[:800])**
- **What the line is doing:** Estimate a regularized linear transition using training rows.
- **What to inspect:** The split here is educational; real telemetry should split by session.

**Code: model.coef_**
- **What the line is doing:** Expose the learned direction and relative scale of each feature.
- **What to inspect:** Interpret coefficients only after accounting for units and scaling.


### State and tensor trace

```text
[speed, throttle, brake]
          ↓ linear weighted sum
predicted next speed
          ↓ subtract observed next speed
residual
          ↓ group/plot by condition
model-improvement hypothesis
```

The residual is not merely an error score; it is evidence about missing structure.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Add the target next speed as an input feature and watch MAE collapse. Then randomize brake while preserving speed. Compare coefficient signs and residuals.

### Diagnose from the earliest failed contract

A suspiciously perfect baseline should trigger a feature audit and time-index trace before celebration. Check that every input is available at forecast time and that split entities are disjoint.

### Repair and lock the repair with a test

Maintain an allow-list of input features, unit-test target exclusion, and report persistence beside every model. Add residual plots by horizon and condition to evaluation artifacts.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Persistence**
- **Choose it when:** Very short horizons and slowly changing states.
- **Do not choose it when:** Actions or geometry cause rapid transitions.

**Implementation: Linear / Ridge**
- **Choose it when:** You need interpretability, speed and a strong control.
- **Do not choose it when:** Residuals show substantial nonlinear or temporal structure.

**Implementation: Gradient-boosted trees**
- **Choose it when:** Tabular nonlinearities dominate and fixed windows can summarize history.
- **Do not choose it when:** You need smooth autoregressive latent dynamics or differentiable planning.

**Implementation: Probabilistic baseline**
- **Choose it when:** Forecast intervals or multi-modal outcomes matter.
- **Do not choose it when:** You have not first validated deterministic error and calibration.


APEX keeps persistence and a linear transition baseline in the same evaluation harness as learned world models. A complex model is promoted only when it improves the relevant horizons without unacceptable violations or operational cost.

## Transfer the lesson into Project APEX

Open the baseline implementation and evaluation report. Add a residual plot against curvature and a table comparing relative improvement over persistence.

### Repository path to inspect

```text
apex_engine/src/apexsim/models/baselines.py
apex_engine/src/apexsim/evaluation.py
apex_engine/src/apexsim/pipeline/stages.py
debugging_cases/03_target_leakage
```

## Connection to research

Strong baselines protect research from architecture-driven conclusions. If a latent world model cannot outperform persistence on the actual decision horizon, its representation may still be useful—but that claim needs a different evaluation.

## Check your understanding before continuing

1. Why is relative improvement over persistence more informative than a standalone MAE?
2. What does a curved residual-vs-speed plot suggest?
3. Can uncertainty be low while the prediction is wrong?

## Solutions and reasoning

**1.** It shows how much predictable change the model captures beyond the natural smoothness of telemetry.
**2.** The transition contains nonlinear speed dependence or the feature scaling/model form is misspecified.
**3.** Yes. An uncalibrated model can be confidently wrong, especially under distribution shift.

## Independent build challenge

Create persistence, linear and polynomial baselines under the same session split. Produce a one-page model card explaining which baseline wins at 1, 5 and 20 steps and why.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
