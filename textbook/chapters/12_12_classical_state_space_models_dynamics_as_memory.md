# 12. Classical State-Space Models: Dynamics as Memory

> **Instructor objective:** Understand state-space recurrence mathematically, inspect stability, and connect classical dynamical systems to modern sequence models.

![12. Classical State-Space Models: Dynamics as Memory](../figures/11_ssm.png)

## The problem that earns this chapter

GRUs learn memory through generic gates. State-space models begin with an explicit dynamical view: a hidden state evolves under a transition and receives input. This structure can represent long memory efficiently, but an unstable transition can explode over repeated steps.

### Predict before reading

For the scalar recurrence `x_t = 1.05 x_{t-1} + u_t`, what happens after inputs become zero? What changes if the transition coefficient is 0.95?

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

A discrete linear state-space model is

\[x_t=Ax_{t-1}+Bu_t,\qquad y_t=Cx_t+Du_t.\]

The hidden state `x` is memory; `A` controls how it persists and mixes; `B` writes input; `C` reads output. Repeated powers of `A` determine whether past information decays, persists, oscillates or explodes.

Many modern SSMs begin from continuous-time dynamics and discretize them for sampled sequences. This connects model behaviour to the time step. A change from 5 Hz to 20 Hz should not be treated as an arbitrary tensor resize when the transition is supposed to represent time.

Linear recurrence alone cannot model all nonlinear racing dynamics, but it exposes memory timescales and stability more directly than a generic black box.

## Vocabulary that now has a job

**Concept: State matrix A**
- **Meaning in plain language:** Controls hidden-state propagation between steps.
- **Role inside APEX:** Determines memory decay, coupling and stability.

**Concept: Input matrix B**
- **Meaning in plain language:** Controls how current telemetry writes into memory.
- **Role inside APEX:** Maps actions/context into dynamical state.

**Concept: Readout C**
- **Meaning in plain language:** Maps hidden memory to predicted output.
- **Role inside APEX:** Produces next-state features from SSM memory.

**Concept: Spectral radius**
- **Meaning in plain language:** Largest absolute eigenvalue of A; a key discrete stability indicator.
- **Role inside APEX:** Values above one can amplify state without bound.


## Worked example: calculate it by hand

For `x_t = a x_{t-1}` after input stops:

- If `a=1.05`, then after 20 steps `x` is multiplied by `1.05²⁰ ≈ 2.65`.
- If `a=0.95`, it is multiplied by `0.95²⁰ ≈ 0.358`.
- If `a=1`, memory persists exactly.
- If `a=−0.95`, memory alternates sign while decaying.

For a matrix, eigenvalues play the role of these scalar factors along different modes. Stability does not guarantee usefulness: a transition that decays too quickly forgets everything.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/13_linear_ssm`

### What we are about to build

Run a two-dimensional linear SSM under an input pulse and observe one state component react immediately while another integrates it more slowly.

### Runnable implementation

```python
import numpy as np
A=np.array([[0.95,0.0],[0.1,0.85]]); B=np.array([[0.2],[0.05]]); x=np.zeros(2)
for u in [1,1,0,0,0]:
    x=A@x+B[:,0]*u; print(x.round(3))

```

### Observed output from the packaged solution

```text
[0.2  0.05]
[0.39  0.112]
[0.37  0.135]
[0.352 0.151]
[0.334 0.164]
```

### Read the important lines like English

**Code: A=np.array([[0.95,0.0],[0.1,0.85]])**
- **What the line is doing:** Define decay and coupling of two hidden modes.
- **What to inspect:** Diagonal values set persistence; off-diagonal 0.1 transfers state.

**Code: B=np.array([[0.2],[0.05]])**
- **What the line is doing:** Define how the scalar input writes into both modes.
- **What to inspect:** Different modes receive different input strength.

**Code: x=A@x+B[:,0]*u**
- **What the line is doing:** Apply one state-space transition.
- **What to inspect:** Repeated multiplication reveals stability and memory.


### State and tensor trace

```text
u₀=1 → immediate mode rises strongly; slow mode rises slightly
u₁=1 → both accumulate
u₂=0 → immediate mode decays; slow mode still receives coupled memory
u₃=0 → both decay on different timescales
```

Plot each hidden dimension. A hidden state is useful because its dynamics differ, not because it has many numbers.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Change a diagonal value in `A` to 1.2 and roll for 100 zero-input steps. Then set both diagonal values to 0.1.

### Diagnose from the earliest failed contract

Measure hidden-state norm and eigenvalues. Explosion points to unstable propagation; rapid collapse points to memory that decays faster than the required dependency.

### Repair and lock the repair with a test

Parameterize stable decay, constrain eigenvalues or add normalization/clipping as appropriate. Add tests that hidden state stays finite under bounded inputs for the intended horizon.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Fixed linear SSM**
- **Choose it when:** System identification, interpretability and approximately linear dynamics.
- **Do not choose it when:** Strong context-dependent nonlinear transitions dominate.

**Implementation: Nonlinear readout**
- **Choose it when:** Memory dynamics are simple but state-to-output mapping is nonlinear.
- **Do not choose it when:** Input must alter the memory law itself.

**Implementation: Input-dependent SSM**
- **Choose it when:** Different telemetry regimes require selective writing/forgetting.
- **Do not choose it when:** A fixed transition already works and simplicity matters.

**Implementation: GRU**
- **Choose it when:** You need a proven generic nonlinear recurrent baseline.
- **Do not choose it when:** Long-sequence efficiency or structured timescales are the measured bottleneck.


APEX includes a small SSM-style challenger with bounded decay and input-dependent updates. It is taught as a selective recurrent model, not represented as a complete optimized Mamba implementation.

## Transfer the lesson into Project APEX

Inspect the SSM cell parameters and plot hidden norms across a full session. Compare horizon curves and latency with the GRU under the same data and budget.

### Repository path to inspect

```text
labs/13_linear_ssm/solution.py
projects/07_selective_ssm/main.py
apex_engine/src/apexsim/models/ssm_world_model.py
debugging_cases/10_exploding_ssm
```

## Connection to research

S4 and related structured SSMs use mathematical parameterizations and efficient convolution/recurrent forms to handle long sequences. The classical equation here is the conceptual root that makes those designs readable.

## Check your understanding before continuing

1. Why can a stable SSM still be a bad memory model?
2. What does an off-diagonal element of A do?
3. How does sample rate affect a transition intended to represent physical time?

## Solutions and reasoning

**1.** It may decay too quickly, ignore relevant inputs or lack nonlinear/selective behaviour.
**2.** It transfers information from one hidden component into another during propagation.
**3.** A smaller time step represents less elapsed time per transition; continuous-time parameterization/discretization can adjust accordingly, while a fixed discrete A changes physical meaning.

## Independent build challenge

Construct a three-mode SSM with fast, medium and slow decay. Feed braking pulses of different duration and show which hidden mode retains each timescale.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
