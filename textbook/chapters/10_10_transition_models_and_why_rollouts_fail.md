# 10. Transition Models and Why Rollouts Fail

> **Instructor objective:** Build a one-step neural transition, convert it into an autoregressive simulator, and measure error compounding honestly.

![10. Transition Models and Why Rollouts Fail](../figures/09_rollout.png)

## The problem that earns this chapter

A model can be excellent at predicting the next frame when given the true current frame, yet collapse when asked to simulate ten frames. During rollout it consumes its own imperfect predictions, a distribution it did not see during teacher-forced training.

### Predict before reading

A model has a constant +0.1 m/s bias per predicted step and no corrective feedback. What speed bias do you expect after 20 autoregressive steps? What if the transition also multiplies the current error by 1.05 each step?

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

One-step supervised training samples inputs from real data. Autoregressive inference samples later inputs from the model. This train–inference distribution shift is exposure bias. Even unbiased local noise can alter future controls' effects because the state enters nonlinear dynamics.

A rollout function must specify which future variables are known and which are predicted. In APEX, future controls/context can be provided by a scenario, while future state is generated. After each step, predicted state replaces the state portion of the next input; controls remain externally supplied.

Evaluation should report error by horizon rather than averaging all future steps. The shape of the curve distinguishes immediate bias, unstable compounding and long-memory failure.

## Vocabulary that now has a job

**Concept: Teacher forcing**
- **Meaning in plain language:** Train each transition using the true previous state.
- **Role inside APEX:** Stable supervised training for GRU/RSSM components.

**Concept: Autoregressive rollout**
- **Meaning in plain language:** Feed predicted state back to generate later states.
- **Role inside APEX:** The actual simulation mode.

**Concept: Exposure bias**
- **Meaning in plain language:** The model trains on true states but runs on its own imperfect states.
- **Role inside APEX:** A central source of horizon degradation.

**Concept: Horizon curve**
- **Meaning in plain language:** Error reported separately at each future step.
- **Role inside APEX:** Primary evidence for useful simulation duration.


## Worked example: calculate it by hand

With additive bias `e_{t+1}=e_t+0.1`, starting at zero, error after 20 steps is 2.0 m/s.

With amplification `e_{t+1}=1.05e_t+0.1`,

\[e_{20}=0.1rac{1.05^{20}-1}{1.05-1}pprox3.31	ext{ m/s}.\]

The one-step bias is still only 0.1, but the system dynamics amplify it. This is why one-step MAE cannot certify a simulator.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/07_pytorch_module`

### What we are about to build

Use a small PyTorch transition module as the building block, then write a loop that feeds predicted state back while taking future controls from an external sequence.

### Runnable implementation

```python
import torch
from torch import nn

class Transition(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(5,16),nn.ReLU(),nn.Linear(16,2))
    def forward(self,x): return self.net(x)

model=Transition(); x=torch.randn(4,5); y=model(x)
print(model); print("input",x.shape,"output",y.shape)

```

### Observed output from the packaged solution

```text
Transition(
  (net): Sequential(
    (0): Linear(in_features=5, out_features=16, bias=True)
    (1): ReLU()
    (2): Linear(in_features=16, out_features=2, bias=True)
  )
)
input torch.Size([4, 5]) output torch.Size([4, 2])
```

### Read the important lines like English

**Code: prediction = model(current_input)**
- **What the line is doing:** Predict the next state from current state/action/context.
- **What to inspect:** Confirm output contains only target state variables.

**Code: current_state = prediction**
- **What the line is doing:** Move the imagined world forward using its own result.
- **What to inspect:** Detach only when appropriate; training through rollout may need gradients.

**Code: next_input = concat(current_state, future_control[t])**
- **What the line is doing:** Combine generated state with externally specified intervention.
- **What to inspect:** Never overwrite the future control with a predicted target column.


### State and tensor trace

```text
real history → encoded state
step 1: predicted state₁ + supplied action₁ → input₂
step 2: predicted state₂ + supplied action₂ → input₃
step 3: predicted state₃ + supplied action₃ → input₄
```

At each step, log both normalized and physical-unit state. Violations may be hidden in normalized space.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

During rollout, accidentally keep feeding the last real state instead of each prediction. The multi-step score may look surprisingly strong because you are not actually simulating.

### Diagnose from the earliest failed contract

Trace the source of every input tensor at every horizon. Mark each element as observed, supplied intervention, static context or model-generated. A rollout audit catches “teacher forcing at test time.”

### Repair and lock the repair with a test

Add a test with a deterministic transition where the exact multi-step trajectory is known. Assert that changing a predicted state changes later predictions. Report teacher-forced and free-running metrics separately.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: One-step training**
- **Choose it when:** A stable starting point with abundant transition examples.
- **Do not choose it when:** You treat its metric as rollout certification.

**Implementation: Multi-step loss**
- **Choose it when:** Long-horizon accuracy matters and compute allows unrolled training.
- **Do not choose it when:** Early training is unstable or the horizon curriculum is not controlled.

**Implementation: Scheduled sampling**
- **Choose it when:** You want gradual exposure to model-generated states.
- **Do not choose it when:** You assume it guarantees consistent probabilistic learning.

**Implementation: Direct multi-horizon model**
- **Choose it when:** Fixed-horizon forecasts matter more than a reusable transition.
- **Do not choose it when:** You need arbitrary-length interactive simulation.


APEX trains a stable sequence world model and evaluates it under free-running rollouts. Any reported simulation horizon is tied to its error and violation curves, not a marketing duration.

## Transfer the lesson into Project APEX

Inspect `simulation.py` and identify the exact line where predicted state is inserted into the next model input. Add a debug mode that records provenance for every future feature.

### Repository path to inspect

```text
projects/04_mlp_transition/main.py
apex_engine/src/apexsim/simulation.py
apex_engine/src/apexsim/evaluation.py
apex_engine/src/apexsim/models/gru_world_model.py
```

## Connection to research

World-model planning magnifies rollout weaknesses because a planner searches for trajectories that exploit them. Reliable imagination requires evaluating model-generated state distributions, not only posterior-conditioned reconstruction.

## Check your understanding before continuing

1. Why can zero-mean one-step noise still create biased long rollouts?
2. What future variables may legitimately be supplied to a simulator?
3. What does a flat horizon-error curve suggest?

## Solutions and reasoning

**1.** Nonlinear dynamics and constraints can transform symmetric local noise into asymmetric state evolution.
**2.** Known scenario interventions and exogenous forecasts, provided their availability is explicit; future target state cannot be supplied.
**3.** The model may be stable over that range, or errors may be dominated by a constant initial bias rather than compounding; inspect conditions and baselines.

## Independent build challenge

Train the same transition with one-step and five-step losses. Compare horizon curves, training stability and compute. Record which objective you choose for APEX V1 and why.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
