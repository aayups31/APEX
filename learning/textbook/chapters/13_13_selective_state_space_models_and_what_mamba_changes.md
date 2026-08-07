# 13. Selective State-Space Models and What Mamba Changes

> **Instructor objective:** Build an input-dependent memory cell, understand selection, and separate the core Mamba idea from implementation hype.

![13. Selective State-Space Models and What Mamba Changes](../figures/12_selective_ssm.png)

## The problem that earns this chapter

A fixed SSM remembers every input according to the same transition. Racing telemetry is regime dependent: a yellow flag, braking spike or rain change may deserve a strong memory write, while repetitive straight-line frames may be compressed or forgotten.

### Predict before reading

Imagine a memory of “recent heavy braking.” Should the same decay apply during ten ordinary straight-line frames and during a sudden lock-up indicator? How could the current input alter write and forget behaviour?

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

Selection means model parameters or gates depend on the current input. Instead of one fixed `A` and `B`, the sequence determines how strongly memory persists and what content is written. This gives content-aware recurrence while preserving a state-space perspective.

Mamba combines selective state-space dynamics with hardware-aware computation so long sequences can be processed efficiently. The important conceptual move for this curriculum is not “replace everything with Mamba.” It is: **make memory propagation conditional on the token when fixed dynamics are insufficient.**

A small selective cell can be written as `h_t = a(x_t) ⊙ h_{t-1} + (1−a(x_t)) ⊙ b(x_t)`. It resembles a gated recurrent update. The difference between educational cell and research architecture must remain explicit.

## Vocabulary that now has a job

**Concept: Selection**
- **Meaning in plain language:** Current input changes how memory is written, retained or read.
- **Role inside APEX:** Braking, weather or geometry can trigger different memory behaviour.

**Concept: Input-dependent decay**
- **Meaning in plain language:** The retention factor is computed from the current token.
- **Role inside APEX:** Adaptive timescales across race regimes.

**Concept: Scan**
- **Meaning in plain language:** Efficiently apply a recurrence across sequence positions.
- **Role inside APEX:** Important for long histories and GPU throughput.

**Concept: Mamba block**
- **Meaning in plain language:** A complete architecture combining projections, selective SSM computation and implementation details.
- **Role inside APEX:** A future challenger; not identical to the toy selective cell.


## Worked example: calculate it by hand

Let old memory be `h=0.9`.

- Ordinary input produces retention `a=0.95` and candidate `b=0.2`: `h'=0.95(0.9)+0.05(0.2)=0.865`.
- Critical braking input produces retention `a=0.2` and candidate `b=−0.8`: `h'=0.2(0.9)+0.8(−0.8)=−0.46`.

The same memory dimension changes slowly during routine input and rapidly under a meaningful event. Selection is useful only if training learns gates that correspond to predictive needs rather than arbitrary noise.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/14_selective_ssm`

### What we are about to build

Implement a small PyTorch selective cell where decay and candidate write are functions of each input token. Feed basis vectors and inspect hidden updates.

### Runnable implementation

```python
import torch
from torch import nn

class SelectiveCell(nn.Module):
    def __init__(self,d):
        super().__init__(); self.decay=nn.Linear(d,d); self.write=nn.Linear(d,d)
    def forward(self,x,h):
        a=torch.sigmoid(self.decay(x))*0.99
        b=torch.tanh(self.write(x))
        return a*h+(1-a)*b
cell=SelectiveCell(3); h=torch.zeros(1,3)
for x in torch.eye(3): h=cell(x[None],h); print(h.detach().numpy().round(3))

```

### Observed output from the packaged solution

```text
[[-0.114 -0.033 -0.16 ]]
[[ 0.203  0.146 -0.244]]
[[ 0.335 -0.015 -0.351]]
```

### Read the important lines like English

**Code: a=torch.sigmoid(self.decay(x))*0.99**
- **What the line is doing:** Compute bounded input-dependent retention.
- **What to inspect:** Multiplying by 0.99 prevents exact unit retention in this toy cell.

**Code: b=torch.tanh(self.write(x))**
- **What the line is doing:** Compute candidate content to write.
- **What to inspect:** Tanh bounds the candidate but can saturate.

**Code: return a*h+(1-a)*b**
- **What the line is doing:** Interpolate between persistent memory and new content per dimension.
- **What to inspect:** Inspect gate distributions across regimes.


### State and tensor trace

```text
input x_t
  ├─► decay network ─► retention a_t ─┐
  └─► write network ─► candidate b_t ─┼─► h_t
previous h_{t-1} ──────────────────────┘
```

Log `a_t` by feature regime. A gate that is always 0.5 is technically selective but may not be learning meaningful specialization.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Remove the sigmoid/bound and allow retention greater than one. Then initialize decay so gates saturate near zero or one.

### Diagnose from the earliest failed contract

Track hidden norm, gate histograms, gradient norms and horizon errors. Explosion, frozen memory and always-overwritten memory have different signatures.

### Repair and lock the repair with a test

Use stable parameterization, sensible initialization and regular diagnostic plots. Add tests for finite bounded-state behaviour under bounded inputs, but do not force gates to a preferred distribution without evidence.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Toy selective cell**
- **Choose it when:** Learning the mechanism and testing whether input-dependent memory helps.
- **Do not choose it when:** Claiming Mamba-equivalent speed or quality.

**Implementation: Official Mamba implementation**
- **Choose it when:** Long sequences and benchmarks justify the dependency and hardware path.
- **Do not choose it when:** Your data are small, horizons short, or environment support is fragile.

**Implementation: GRU**
- **Choose it when:** A stable gated recurrent baseline is sufficient.
- **Do not choose it when:** Measured long-context/throughput limitations motivate another architecture.

**Implementation: Transformer**
- **Choose it when:** Global content interactions and parallel token processing dominate.
- **Do not choose it when:** Quadratic attention cost is unjustified and recurrent deployment state is useful.


APEX V1 retains a GRU primary and an SSM-style challenger. Fine-tuning or replacing with a full Mamba model should begin only after sequence length, data scale and latency measurements establish the need.

## Transfer the lesson into Project APEX

Compare GRU and SSM models with identical windows, splits, normalization, hidden size budget and evaluation. Add gate plots to the SSM run artifacts.

### Repository path to inspect

```text
labs/14_selective_ssm/solution.py
projects/07_selective_ssm/main.py
apex_engine/src/apexsim/models/ssm_world_model.py
apex_engine/configs/ssm_fast.yaml
```

## Connection to research

The Mamba paper motivates selection because content-dependent reasoning is a weakness of fixed linear time-invariant SSMs. Its efficiency claims depend on the complete algorithm and hardware-aware implementation, not merely using a gate.

## Check your understanding before continuing

1. What makes a state update selective?
2. Why is bounded retention helpful but not sufficient?
3. What evidence would justify a full Mamba dependency in APEX?

## Solutions and reasoning

**1.** The current input changes parameters controlling memory propagation, writing or reading.
**2.** It reduces explosion risk, but the model can still forget too quickly, ignore inputs or learn useless gates.
**3.** Long histories where GRU/Transformer baselines fail or are too slow, sufficient data, reproducible gains by horizon, and deployment hardware that benefits from the implementation.

## Independent build challenge

Create a dataset with rare event tokens that determine a target many steps later. Compare fixed linear SSM, selective cell and GRU while plotting learned retention around events.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
