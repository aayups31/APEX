# 7. Windows, Session Splits and Normalization Without Leakage

> **Instructor objective:** Turn canonical sessions into causal training examples while keeping validation and test evidence genuinely independent.

![7. Windows, Session Splits and Normalization Without Leakage](../figures/06_windows.png)

## The problem that earns this chapter

A telemetry session yields thousands of overlapping windows. If you randomly split those windows, nearly identical frames from the same lap appear in both training and test. The test score becomes a measure of memorization under overlap, not generalization to a new session.

### Predict before reading

A 100-frame session uses 20 history frames and 5 future frames with stride 1. How many windows can be created? If windows 1 and 2 are put in different splits, how many frames do they share?

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

A sequence example has three distinct pieces: history observations, future interventions/context, and future target state. The model must not receive the future target inside its inputs. This sounds obvious, but dataframe slicing and feature lists can quietly duplicate it.

Split units should match the deployment claim. If the engine will simulate a new race session, split by session or event before making windows. A time-based holdout within one session answers a narrower question. Random windows almost always overstate performance when overlap is high.

Normalization must be fitted only on training data. Validation and test are transformed using stored training statistics. Otherwise the mean and variance leak information about future or held-out distributions, and deployment cannot reproduce the transform.

## Vocabulary that now has a job

**Concept: History length**
- **Meaning in plain language:** How many past frames are visible before a forecast begins.
- **Role inside APEX:** Controls memory evidence and input cost.

**Concept: Forecast horizon**
- **Meaning in plain language:** How many future transitions are predicted.
- **Role inside APEX:** Defines simulation duration and error accumulation.

**Concept: Split unit**
- **Meaning in plain language:** The independent entity assigned wholly to train, validation or test.
- **Role inside APEX:** Usually session/event, not overlapping windows.

**Concept: Train-only normalizer**
- **Meaning in plain language:** Scaling statistics fitted exclusively on training observations.
- **Role inside APEX:** Persisted with the model artifact.


## Worked example: calculate it by hand

For length `N=100`, history `H=20`, future `F=5`, stride 1, the first window consumes frames 0–24 and the last begins at 75, so the count is

\[N-H-F+1=100-20-5+1=76.\]

Window 1 uses frames 0–24; window 2 uses 1–25. They share 24 of 25 frames. Assigning them to different splits creates almost complete leakage.

For normalization, training speeds `[40, 50, 60]` have mean 50 and standard deviation about 8.165. A test speed 70 becomes `(70−50)/8.165 ≈ 2.45`. Recomputing the mean with test data would shrink that value and leak the test distribution.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/08_dataset_windows`

### What we are about to build

Create history/target windows and inspect shapes and boundaries. Then map the same logic to the production window builder, which also carries future controls and session identifiers.

### Runnable implementation

```python
import numpy as np
from education.core import sliding_windows

values=np.arange(30,dtype=float).reshape(10,3)
x,y=sliding_windows(values,history=4,horizon=2)
print("x",x.shape,"y",y.shape)
print("first history\n",x[0]); print("first future\n",y[0])

```

### Observed output from the packaged solution

```text
Traceback (most recent call last):
  File "/mnt/data/Project_APEX_Engineering_Apprenticeship/labs/08_dataset_windows/solution.py", line 2, in <module>
    from education.core import sliding_windows
ModuleNotFoundError: No module named 'education'
```

### Read the important lines like English

**Code: for start in range(...)**
- **What the line is doing:** Enumerate valid causal cut points.
- **What to inspect:** The upper bound must leave enough future target frames.

**Code: history = data[start:start+H]**
- **What the line is doing:** Select only evidence available before forecast time.
- **What to inspect:** Verify the last history timestamp precedes the first target timestamp.

**Code: target = data[start+H:start+H+F]**
- **What the line is doing:** Select the future trajectory to learn.
- **What to inspect:** Do not accidentally include target state in future inputs.


### State and tensor trace

```text
session frames:  0 1 2 3 4 5 6 7 8 9
history H=4:     [0 1 2 3]
future controls:         [4 5 6]
future targets:          [4 5 6]
next window:       [1 2 3 4] → [5 6 7]
```

Controls and target states share timestamps but not semantics. Future throttle may be supplied; future speed is what must be predicted.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Create all windows first and randomly split them. Train a nearest-neighbour or linear baseline. Compare its test score with a session-level split.

### Diagnose from the earliest failed contract

Inspect source session IDs and frame-index overlap across splits. If any raw session contributes to multiple splits, your claimed generalization unit is false.

### Repair and lock the repair with a test

Assign sessions/events deterministically to splits before windowing. Fit normalization on training windows only. Add tests for disjoint identifiers and for target columns absent from model inputs.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Random window split**
- **Choose it when:** Only for debugging shape/training code, never for a generalization claim with overlap.
- **Do not choose it when:** Any realistic telemetry evaluation.

**Implementation: Session split**
- **Choose it when:** Deployment targets unseen sessions under similar tracks/drivers.
- **Do not choose it when:** You specifically study later portions of the same session.

**Implementation: Event/track split**
- **Choose it when:** You need evidence of transfer to new circuits or events.
- **Do not choose it when:** The dataset is too small to support that claim.

**Implementation: Rolling temporal split**
- **Choose it when:** Production learns from past sessions and forecasts future dates.
- **Do not choose it when:** Timestamp order does not correspond to deployment.


APEX V1 splits by session before creating windows and stores the split assignment. Normalization statistics are versioned artifacts loaded by training, evaluation, simulation and UI.

## Transfer the lesson into Project APEX

Trace one `WindowDataset` sample. Print history, future inputs, targets, session ID, start timestamp and feature names. Then inspect the split tests.

### Repository path to inspect

```text
apex_engine/src/apexsim/data/windows.py
apex_engine/src/apexsim/pipeline/stages.py
apex_engine/tests/test_windows.py
debugging_cases/04_random_window_split
debugging_cases/06_normalizer_leak
```

## Connection to research

World-model papers often report benchmark splits that already define episodes. In custom telemetry projects, defining the episode and independence unit is part of the research contribution, not preprocessing trivia.

## Check your understanding before continuing

1. Why can overlapping windows inflate scores even without exact duplicate rows?
2. Should validation statistics be used to choose normalization?
3. What deployment claim does a track holdout support?

## Solutions and reasoning

**1.** They share most temporal context and local dynamics, so the model sees nearly the same trajectory during training.
**2.** No. Normalization is learned from training only; validation is used for model and hyperparameter selection under that fixed transform.
**3.** Evidence that the learned dynamics and representation transfer to an unseen circuit distribution, subject to the held-out tracks tested.

## Independent build challenge

Implement a split audit that reports shared session IDs, shared raw frame identifiers, time overlap and distribution differences for every pair of splits.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
