# 11. Recurrent Memory and the GRU From the Inside

> **Instructor objective:** Earn recurrent memory by exposing the limits of fixed-frame transitions, then inspect how GRU gates update hidden state.

![11. Recurrent Memory and the GRU From the Inside](../figures/10_gru.png)

## The problem that earns this chapter

Current speed, throttle and brake may not reveal whether the car has been accelerating for two seconds, exiting a corner, heating tyres or recovering from a braking event. A fixed-frame model sees only the present. We need a mechanism that carries a learned summary of the past.

### Predict before reading

Two sequences end with the same final frame `[speed=50, throttle=0.5, brake=0]`. Sequence A accelerated steadily; sequence B braked hard and recovered. Should a recurrent model be able to produce different next-state predictions? What must differ internally?

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

A recurrent neural network updates hidden memory as each frame arrives. The final hidden state is not a literal copy of history; it is a learned summary optimized for the training objective. A vanilla recurrent cell can struggle when useful information must survive many updates because gradients repeatedly pass through the same transition.

A GRU adds gates. The update gate decides how much old memory to keep versus replace. The reset gate controls how much previous memory influences the candidate update. These are soft, feature-wise decisions, not binary switches. The same hidden dimension can retain long-term tyre information while rapidly updating braking state.

Using `nn.GRU` does not guarantee meaningful memory. You still need enough history, correct ordering, no hidden-state leakage across independent sequences, and evaluation that tests whether memory improves the target horizon.

## Vocabulary that now has a job

**Concept: Hidden state**
- **Meaning in plain language:** A learned vector carried across sequence steps.
- **Role inside APEX:** Compressed recent driving and unobserved dynamical context.

**Concept: Update gate**
- **Meaning in plain language:** Controls interpolation between old memory and candidate memory.
- **Role inside APEX:** Lets some information persist while other information changes.

**Concept: Reset gate**
- **Meaning in plain language:** Controls how previous memory contributes to the candidate update.
- **Role inside APEX:** Allows rapid forgetting when current evidence changes regime.

**Concept: Sequence boundary**
- **Meaning in plain language:** The point where hidden memory must be reset or intentionally transferred.
- **Role inside APEX:** Driver/session windows cannot share hidden state accidentally.


## Worked example: calculate it by hand

A simplified update is

\[h_t=(1-z_t)h_{t-1}+z_t	ilde h_t.\]

If old memory is `h=0.8`, candidate memory is `−0.2`:

- With update gate `z=0.1`: `h_t=0.9(0.8)+0.1(−0.2)=0.70`. Most old memory survives.
- With `z=0.9`: `h_t=0.1(0.8)+0.9(−0.2)=−0.10`. The new evidence largely overwrites memory.

This interpolation makes a gate interpretable at the mechanism level, although individual learned dimensions may not map cleanly to human concepts.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/12_gru_gates`

### What we are about to build

Feed three simple one-hot-like inputs through a GRUCell and print hidden state after each step. The goal is to see memory as a changing vector rather than a black box.

### Runnable implementation

```python
import torch

torch.manual_seed(2); cell=torch.nn.GRUCell(2,4); h=torch.zeros(1,4)
for x in [torch.tensor([[1.,0.]]),torch.tensor([[0.,1.]]),torch.tensor([[0.,1.]])]:
    h=cell(x,h); print(h.detach().numpy().round(3))

```

### Observed output from the packaged solution

```text
[[ 0.354 -0.151 -0.384  0.149]]
[[ 0.278  0.282 -0.371  0.408]]
[[ 0.322  0.39  -0.39   0.542]]
```

### Read the important lines like English

**Code: cell=torch.nn.GRUCell(2,4)**
- **What the line is doing:** Create a transition from a 2-feature input and 4-value memory to new memory.
- **What to inspect:** The hidden size is model capacity, not a known physical variable count.

**Code: h=torch.zeros(1,4)**
- **What the line is doing:** Initialize memory for one sequence.
- **What to inspect:** Initial-state policy affects early predictions.

**Code: h=cell(x,h)**
- **What the line is doing:** Combine current observation and previous memory into next memory.
- **What to inspect:** Sequence order changes the result.


### State and tensor trace

```text
x₁ + h₀=0  → h₁
x₂ + h₁    → h₂
x₃ + h₂    → h₃
                 ↓
          decoder predicts future
```

For batched sequences, PyTorch commonly uses `[batch, time, features]` when `batch_first=True`. The returned hidden state is typically `[layers, batch, hidden]`. Name these axes every time.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Reuse the hidden state from one session as the initial state for an unrelated session. Also shuffle time within each sequence while preserving rows.

### Diagnose from the earliest failed contract

If validation varies with dataloader order or batch grouping, inspect hidden-state lifetime. Hidden memory should reset at independent sequence boundaries unless stateful streaming is an explicit design.

### Repair and lock the repair with a test

Add a test where two sequences processed separately match the same sequences processed in a batch with zero initial states. Add session-boundary reset logic and make stateful mode explicit.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Vanilla RNN**
- **Choose it when:** Tiny educational tasks and very short dependencies.
- **Do not choose it when:** Long/noisy telemetry histories.

**Implementation: GRU**
- **Choose it when:** Strong compact recurrent baseline with fewer parameters than LSTM.
- **Do not choose it when:** You have evidence that longer structured memory or parallel training is required.

**Implementation: LSTM**
- **Choose it when:** You value an explicit cell state and gates and have sufficient compute/data.
- **Do not choose it when:** Extra complexity provides no measured gain.

**Implementation: Temporal convolution**
- **Choose it when:** Dependencies fit a fixed receptive field and parallel computation matters.
- **Do not choose it when:** You need adaptive unbounded recurrence or stateful streaming.


The GRU is APEX V1’s primary deterministic world model because it is understandable, stable, compact and strong enough to establish the pipeline. SSM and RSSM models are challengers, not automatic replacements.

## Transfer the lesson into Project APEX

Trace the GRU world model from history encoder to autoregressive decoder. Print hidden shape, decoder input shape and output state at each horizon for a batch of one.

### Repository path to inspect

```text
labs/11_rnn_from_scratch/solution.py
labs/12_gru_gates/solution.py
projects/06_gru_forecaster/main.py
apex_engine/src/apexsim/models/gru_world_model.py
debugging_cases/07_hidden_state_reuse
```

## Connection to research

Recurrent state is a deterministic belief summary. Dreamer’s RSSM retains a recurrent deterministic state while adding a stochastic latent variable to represent uncertainty and ambiguity.

## Check your understanding before continuing

1. Why can two sequences with the same final observed frame produce different hidden states?
2. Does a larger hidden size always improve memory?
3. When should hidden state persist across API requests?

## Solutions and reasoning

**1.** The recurrence applies ordered updates, so earlier frames alter the memory entering later frames.
**2.** No. It increases capacity but may overfit, slow training or store irrelevant detail; history, objective and optimization also limit memory.
**3.** Only in an explicitly stateful stream with stable entity/session identity, ordering guarantees and reset rules. Stateless scenario requests should rebuild from supplied history.

## Independent build challenge

Implement a GRU forecaster and a frame-only MLP with matched parameter counts. Create a synthetic target dependent on an event ten steps ago and compare performance as history length changes.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
