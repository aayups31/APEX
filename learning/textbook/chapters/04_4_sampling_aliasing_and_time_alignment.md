# 4. Sampling, Aliasing and Time Alignment

> **Instructor objective:** Turn asynchronous telemetry into a defensible time grid without creating fake evidence or future leakage.

![4. Sampling, Aliasing and Time Alignment](../figures/04_sampling.png)

## The problem that earns this chapter

Speed may arrive at one frequency, weather at another, and event data only when something changes. A neural network expects aligned rows. Joining by nearest timestamp can quietly attach a future weather measurement to an earlier car frame. Interpolation can make missing data look observed.

### Predict before reading

An 8 Hz oscillation is sampled at 5 Hz. Sketch the samples. Will the observed sequence reveal an 8 Hz signal, a slower false signal, or no signal? Then decide what a model might learn from it.

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

Sampling converts a continuous process into discrete observations. If the sample rate is too low for the dynamics, high-frequency behaviour aliases into a different pattern. No architecture can reconstruct information that the sensor never captured without additional assumptions.

Alignment chooses which measurements describe the same model time. A backward as-of join says: at each car timestamp, use the latest context that was already available. A nearest join may use the future. A tolerance limits how stale a matched measurement may be. These are causal policies, not dataframe trivia.

Resampling onto a uniform grid simplifies windows and batch training, but interpolation must respect feature type. Continuous speed may be linearly interpolated across short gaps. Gear and flags are categorical and generally require forward fill or explicit unknown values. Long gaps should be marked invalid, not painted over.

## Vocabulary that now has a job

**Concept: Sampling rate**
- **Meaning in plain language:** How many observations are recorded per second.
- **Role inside APEX:** Defines temporal resolution and sequence length.

**Concept: Aliasing**
- **Meaning in plain language:** A high-frequency process appears as a different lower-frequency pattern.
- **Role inside APEX:** Can hide braking spikes or steering oscillations.

**Concept: As-of join**
- **Meaning in plain language:** Match each timestamp with a nearby record under a direction and tolerance policy.
- **Role inside APEX:** Aligns weather, position and telemetry streams.

**Concept: Staleness**
- **Meaning in plain language:** How old a context value is when reused.
- **Role inside APEX:** A monitoring feature and validation rule.


## Worked example: calculate it by hand

The Nyquist guideline says a sinusoid of frequency \(f\) requires sampling above \(2f\) to avoid ambiguity. An 8 Hz oscillation needs more than 16 Hz. At 5 Hz, sample times are 0, 0.2, 0.4… seconds. The phase advances `8 × 0.2 = 1.6` cycles per sample, equivalent to an apparent 0.6-cycle advance after wrapping. The observed pattern therefore resembles a 3 Hz oscillation (`0.6 × 5`).

For alignment, suppose car timestamps are 0.0, 0.2, 0.4, 0.6 and rain observations are 0.05 and 0.55. A backward join at 0.4 uses rain from 0.05; a nearest join uses 0.55, leaking a future value by 0.15 seconds.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/19_time_alignment`

### What we are about to build

A backward `merge_asof` with an explicit tolerance. You will inspect which rain observation is attached to each car frame and identify unmatched stale rows.

### Runnable implementation

```python
import pandas as pd

car=pd.DataFrame({'t':[0.0,0.2,0.4,0.6],'speed':[10,12,14,16]})
weather=pd.DataFrame({'t':[0.05,0.55],'rain':[0.0,0.3]})
aligned=pd.merge_asof(car.sort_values('t'),weather.sort_values('t'),on='t',direction='backward',tolerance=0.3)
print(aligned)

```

### Observed output from the packaged solution

```text
t  speed  rain
0  0.0     10   NaN
1  0.2     12   0.0
2  0.4     14   NaN
3  0.6     16   0.3
```

### Read the important lines like English

**Code: sort_values('t')**
- **What the line is doing:** Satisfy the ordered-time precondition of an as-of join.
- **What to inspect:** Unsorted data can fail or produce invalid matches.

**Code: direction='backward'**
- **What the line is doing:** Use only context observations at or before the car timestamp.
- **What to inspect:** This encodes online availability and blocks future leakage.

**Code: tolerance=0.3**
- **What the line is doing:** Reject a match older than the allowed staleness.
- **What to inspect:** Choose tolerance from domain timing, not convenience.


### State and tensor trace

```text
car t=0.00 ─► no earlier rain measurement ─► missing
car t=0.20 ─► rain at 0.05 (age 0.15 s) ─► valid
car t=0.40 ─► rain at 0.05 (age 0.35 s) ─► rejected by 0.30 s tolerance
car t=0.60 ─► rain at 0.55 (age 0.05 s) ─► valid
```

A table row should carry not only the matched value but ideally the age of that value.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Change `direction` to `nearest` and remove the tolerance. Add a future rain spike at 0.41. Observe how an earlier car frame receives information from the future.

### Diagnose from the earliest failed contract

Compare source timestamp, target timestamp and signed age. The earliest failed contract is availability time, not model performance.

### Repair and lock the repair with a test

Persist measurement timestamps and create a test asserting `context_time <= frame_time` for online features. Add a maximum staleness threshold and an explicit missingness mask.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Backward as-of**
- **Choose it when:** Features must reflect information available online.
- **Do not choose it when:** The quantity is defined as a symmetric offline estimate.

**Implementation: Nearest join**
- **Choose it when:** Both streams are synchronized measurements and future use is scientifically acceptable.
- **Do not choose it when:** Forecasting, control or causal analysis.

**Implementation: Linear interpolation**
- **Choose it when:** A continuous signal has short, well-sampled gaps.
- **Do not choose it when:** Categorical states, discontinuities or long outages.

**Implementation: Forward fill**
- **Choose it when:** A discrete state remains active until changed.
- **Do not choose it when:** A rapidly varying continuous sensor.


APEX chooses a canonical frequency, aligns source streams under causal policies, records staleness, and rejects gaps that exceed configured limits. The policy is part of the dataset version.

## Transfer the lesson into Project APEX

The FastF1 and OpenF1 adapters normalize timestamps and stream-specific fields before producing the canonical frame. Window construction assumes the alignment contract is already satisfied.

### Repository path to inspect

```text
labs/04_sampling_aliasing/solution.py
labs/19_time_alignment/solution.py
apex_engine/src/apexsim/data/fastf1_adapter.py
apex_engine/src/apexsim/data/openf1_adapter.py
```

## Connection to research

Sequence models are often blamed for missing rapid dynamics that were already destroyed by low-rate or misaligned observations. Data acquisition defines the ceiling of learnable temporal behaviour.

## Check your understanding before continuing

1. Why does increasing model capacity not solve aliasing?
2. What does a join tolerance represent physically?
3. When can interpolation create false certainty?

## Solutions and reasoning

**1.** The distinct high-frequency processes map to identical samples, so the information is absent from the data.
**2.** The maximum age or temporal mismatch at which a context measurement is still considered representative.
**3.** When it fills a long or discontinuous gap with smooth values and the training pipeline treats those values as directly observed.

## Independent build challenge

Create two asynchronous synthetic streams with a known causal delay. Compare nearest, backward and interpolated alignment by measuring how well each preserves the known delay.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
