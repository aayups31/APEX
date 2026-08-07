# 17. Evaluation, Ablation and Out-of-Distribution Testing

> **Instructor objective:** Build an evaluation matrix that reveals where a world model works, why it works, and when it should refuse to be trusted.

![17. Evaluation, Ablation and Out-of-Distribution Testing](../figures/17_evaluation.png)

## The problem that earns this chapter

A single average MAE can hide catastrophic braking failures, worsening long-horizon error, impossible speeds, or performance limited to one track. A simulation engine needs evidence across horizons, features, conditions and interventions.

### Predict before reading

Model A has lower average speed MAE than Model B, but A predicts negative speed in 2% of wet-braking rollouts while B never does. Which model is better? State the missing operational information required to decide.

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

Evaluation begins with the decision. If a race engineer uses the simulator to compare a six-second throttle scenario, horizon-six causal sensitivity and physical validity matter more than one-step average fit. Metrics are measurements of requirements, not a scoreboard detached from use.

Ablation removes or changes one information source while holding other factors fixed. It answers causal questions about the implementation: Does weather context help? Does VH-like second channel—here, perhaps curvature or tyre age—matter? Randomly changing many settings answers nothing cleanly.

Out-of-distribution tests define shifts deliberately: unseen track, heavier rain, longer tyre age, unusual controls, different sample rate. Failure under OOD is expected; the goal is to detect and quantify it, then decide whether to abstain, retrain or constrain use.

## Vocabulary that now has a job

**Concept: Horizon metric**
- **Meaning in plain language:** Error measured separately at each future step.
- **Role inside APEX:** Defines useful simulation duration.

**Concept: Guardrail metric**
- **Meaning in plain language:** A metric that must remain within a safety/validity limit even if primary error improves.
- **Role inside APEX:** Negative speed, progress bounds and control sensitivity.

**Concept: Ablation**
- **Meaning in plain language:** A controlled removal or replacement testing one hypothesis.
- **Role inside APEX:** State-only, no weather, no geometry, model-family comparisons.

**Concept: OOD test**
- **Meaning in plain language:** Evaluation under a deliberately shifted distribution.
- **Role inside APEX:** Unseen circuits, weather or control regimes.


## Worked example: calculate it by hand

Suppose Model A and B have:

| Metric | A | B |
|---|---:|---:|
| 1-step MAE | 0.4 | 0.5 |
| 20-step MAE | 8.0 | 5.0 |
| Negative-speed rate | 2% | 0% |
| Scenario latency | 30 ms | 12 ms |

If the UI serves 20-step scenarios, B is stronger despite worse one-step fit. If only one-step filtering is needed, A may be acceptable if violations are constrained. The “best model” is a vector of requirement tradeoffs plus thresholds, not one scalar.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/09_loss_comparison`

### What we are about to build

Compare loss functions on controlled predictions, then connect optimization loss to evaluation metrics. The loss trains parameters; the metric judges the product and need not be identical.

### Runnable implementation

```python
import torch
from torch.nn import functional as F

pred=torch.tensor([0.,1.,2.,20.]); target=torch.tensor([0.,1.,2.,3.])
print("MSE",F.mse_loss(pred,target).item())
print("MAE",F.l1_loss(pred,target).item())
print("Huber",F.huber_loss(pred,target).item())

```

### Observed output from the packaged solution

```text
MSE 72.25
MAE 4.25
Huber 4.125
```

### Read the important lines like English

**Code: mse = ...**
- **What the line is doing:** Penalize squared residuals, emphasizing large errors.
- **What to inspect:** Sensitive to scale and outliers.

**Code: mae = ...**
- **What the line is doing:** Measure average absolute physical error.
- **What to inspect:** More robust but less smooth at zero.

**Code: compare losses**
- **What the line is doing:** Reveal how optimization priorities differ on the same predictions.
- **What to inspect:** Do not select by training loss alone.


### State and tensor trace

```text
run artifact
  ├─ overall metrics
  ├─ horizon curves
  ├─ per-feature errors
  ├─ subgroup tables
  ├─ physical violations
  ├─ intervention sensitivity
  └─ baseline-relative improvement
```

Every plot should include sample count and split identity.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Average all horizons and all conditions into one MAE. Then remove weather from inputs but accidentally change random seed and training epochs too.

### Diagnose from the earliest failed contract

Ask whether compared runs share dataset hash, split, normalizer, seed set, budget and evaluation code. If multiple variables changed, the result is not an ablation.

### Repair and lock the repair with a test

Store experiment manifests and compare matched runs. Add confidence intervals across seeds/sessions where feasible. Make promotion gates explicit: primary metric, guardrails, latency and artifact completeness.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: MAE/RMSE**
- **Choose it when:** Continuous state error in interpretable units.
- **Do not choose it when:** They are the only evidence for a simulator.

**Implementation: Horizon curves**
- **Choose it when:** Autoregressive use or planning matters.
- **Do not choose it when:** Never; at least inspect them for rollouts.

**Implementation: Physical penalties**
- **Choose it when:** Known invalid regions can be expressed and monitored.
- **Do not choose it when:** They replace empirical outcome evaluation.

**Implementation: Human scenario review**
- **Choose it when:** Qualitative causal behaviour and UI trust matter.
- **Do not choose it when:** It substitutes for reproducible quantitative tests.


APEX reports baseline-relative error by horizon, per-feature metrics, physical violations, scenario sensitivity and run metadata. Model promotion is a documented decision, not automatic best-MAE selection.

## Transfer the lesson into Project APEX

Run the GRU, SSM and RSSM references. Build one comparison report with matched data and budgets, then explain why the simplest winning model remains primary.

### Repository path to inspect

```text
apex_engine/src/apexsim/evaluation.py
apex_engine/src/apexsim/pipeline/stages.py
apex_engine/artifacts/runs/
field_workbook/
```

## Connection to research

World-model papers choose benchmarks and metrics that reflect their claims. When adapting a paper to F1, reproduce the mechanism but redefine evaluation around telemetry dynamics, interventions, uncertainty and deployment conditions.

## Check your understanding before continuing

1. What makes an experiment a true ablation?
2. Why should error be normalized as well as reported in physical units?
3. What is an abstention policy?

## Solutions and reasoning

**1.** One targeted component changes while data, split, budget, evaluation and other variables remain fixed.
**2.** Physical units are interpretable; normalized error helps compare features with different scales. Both are useful.
**3.** A rule that withholds or flags predictions when evidence is outside trusted conditions or uncertainty/violations exceed thresholds.

## Independent build challenge

Design a complete APEX evaluation matrix across three horizons, three tracks, wet/dry conditions and five metrics. Define promotion and abstention criteria before seeing results.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
