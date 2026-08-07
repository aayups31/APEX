# 9. Tensors, Autograd and the Training Loop You Can Explain

> **Instructor objective:** Build a PyTorch training loop while understanding every tensor, gradient and parameter update rather than memorizing boilerplate.

![9. Tensors, Autograd and the Training Loop You Can Explain](../figures/08_autograd.png)

## The problem that earns this chapter

Many learners can write `loss.backward()` but cannot say what changed afterward. This becomes dangerous when gradients accumulate, validation tracks graphs, or tensor axes are swapped. We will turn the training loop into an observable state machine.

### Predict before reading

Immediately after `loss.backward()` and before `optimizer.step()`, have the model weights changed? Where is the information needed to change them stored? What happens if `zero_grad()` is omitted for two iterations?

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

A tensor is an array plus shape, dtype, device and—when requested—a connection to a computation graph. The forward pass applies parameterized operations. The loss reduces prediction error to a scalar. Backpropagation computes derivatives of that scalar with respect to leaf parameters and stores them in `.grad`. The optimizer then uses those gradients to update parameters.

Gradients accumulate by default. That enables deliberate gradient accumulation but causes a bug when forgotten. Evaluation must switch behaviour-sensitive layers with `model.eval()` and disable graph construction with `torch.no_grad()`.

The most effective way to learn this is to print parameter values, gradients and loss before and after each line on a tiny problem whose correct mapping is known.

## Vocabulary that now has a job

**Concept: Computation graph**
- **Meaning in plain language:** The recorded chain of operations connecting inputs, parameters and loss.
- **Role inside APEX:** Enables gradient-based training of all world models.

**Concept: Gradient**
- **Meaning in plain language:** Local sensitivity of loss to a parameter.
- **Role inside APEX:** Stored in each trainable parameter after backward.

**Concept: Optimizer state**
- **Meaning in plain language:** Extra memory used to turn gradients into updates.
- **Role inside APEX:** Adam moments are checkpointed with the model during resumable training.

**Concept: Train/eval mode**
- **Meaning in plain language:** Switch for layers such as dropout and batch normalization.
- **Role inside APEX:** Ensures deterministic, correctly normalized validation and rollout.


## Worked example: calculate it by hand

For a one-parameter model \(\hat y=wx\) with `x=2`, `y=6`, `w=1`, and squared loss \((\hat y-y)^2`:

1. Prediction: `1 × 2 = 2`.
2. Error: `2 − 6 = −4`.
3. Loss: `16`.
4. Gradient: `dL/dw = 2(wx−y)x = 2(−4)(2) = −16`.
5. With learning rate 0.1, SGD update: `w ← 1 − 0.1(−16) = 2.6`.
6. New prediction: `5.2`; new loss: `0.64`.

Backward computes −16; the optimizer performs the update to 2.6.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/10_training_loop`

### What we are about to build

Train a linear PyTorch module to sum three input features. Print training loss, gradient norm and validation loss each epoch.

### Runnable implementation

```python
import torch
from torch import nn

torch.manual_seed(1); x=torch.randn(128,3); y=x.sum(1,keepdim=True)
model=nn.Linear(3,1); opt=torch.optim.Adam(model.parameters(),lr=0.05)
for epoch in range(8):
    model.train(); opt.zero_grad(); pred=model(x); loss=((pred-y)**2).mean(); loss.backward()
    grad=float(model.weight.grad.norm()); opt.step()
    model.eval();
    with torch.no_grad(): val=((model(x)-y)**2).mean()
    print(epoch,float(loss),grad,float(val))

```

### Observed output from the packaged solution

```text
0 3.2264039516448975 3.7724902629852295 2.9054489135742188
1 2.9054489135742188 3.5811667442321777 2.6067750453948975
2 2.6067750453948975 3.390789270401001 2.3303141593933105
3 2.3303141593933105 3.2017178535461426 2.0752670764923096
4 2.0752670764923096 3.0143868923187256 1.8400570154190063
5 1.8400570154190063 2.829359292984009 1.6230223178863525
6 1.6230223178863525 2.6473701000213623 1.4232583045959473
7 1.4232583045959473 2.469295024871826 1.2406574487686157
/mnt/data/Project_APEX_Engineering_Apprenticeship/labs/10_training_loop/solution.py:11: UserWarning: Converting a tensor with requires_grad=True to a scalar may lead to unexpected behavior.
Consider using tensor.detach() first. (Triggered internally at /pytorch/torch/csrc/autograd/generated/python_variable_methods.cpp:836.)
  print(epoch,float(loss),grad,float(val))
```

### Read the important lines like English

**Code: opt.zero_grad()**
- **What the line is doing:** Clear gradients left by previous backward passes.
- **What to inspect:** It does not reset model weights.

**Code: pred=model(x)**
- **What the line is doing:** Run the forward computation using current parameters.
- **What to inspect:** Inspect prediction shape against target shape.

**Code: loss.backward()**
- **What the line is doing:** Populate `.grad` for parameters connected to the loss.
- **What to inspect:** Weights have not yet changed.

**Code: opt.step()**
- **What the line is doing:** Use gradients and optimizer state to update parameters.
- **What to inspect:** Compare parameter values before and after.

**Code: with torch.no_grad()**
- **What the line is doing:** Compute validation outputs without constructing a backward graph.
- **What to inspect:** Also call `model.eval()` for mode-dependent layers.


### State and tensor trace

```text
parameters θ₀
   ↓ forward
predictions ŷ
   ↓ loss
scalar L
   ↓ backward
θ.grad populated; θ still equals θ₀
   ↓ optimizer.step
parameters θ₁
```

Print `id(parameter)`, `parameter.detach()`, and `parameter.grad` around these steps once. That trace removes the mystery permanently.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Remove `zero_grad`, increase learning rate by 100×, and accidentally shape targets as `[B]` while predictions are `[B,1]`. Observe accumulation, divergence and broadcasting.

### Diagnose from the earliest failed contract

Check shapes first, then finite values, loss scale, gradient norms, parameter-update magnitude and mode. Debug the smallest batch before scaling to full telemetry.

### Repair and lock the repair with a test

Add assertions for exact prediction/target shape, finite loss and finite gradients. Add a one-batch overfit test and a deterministic seed. Make gradient accumulation an explicit configured feature if used.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: SGD**
- **Choose it when:** You want transparent updates and can tune schedules carefully.
- **Do not choose it when:** Sparse/noisy gradients need faster adaptive progress.

**Implementation: Adam/AdamW**
- **Choose it when:** A strong default for deep sequence models and fast iteration.
- **Do not choose it when:** You assume it removes the need for learning-rate and regularization experiments.

**Implementation: Gradient clipping**
- **Choose it when:** Recurrent or long-horizon training shows occasional exploding norms.
- **Do not choose it when:** It hides systematically bad scaling or unstable architecture.

**Implementation: Mixed precision**
- **Choose it when:** GPU throughput/memory matters and numerical checks pass.
- **Do not choose it when:** You have not established a stable full-precision reference.


APEX training records seed, configuration, gradient-related settings, checkpoint metric and normalizer. Validation is performed under eval/no-grad and the best checkpoint is restored before test evaluation.

## Transfer the lesson into Project APEX

Trace one batch through the GRU training function. Print every shape and compare parameter checksum before backward, after backward and after step.

### Repository path to inspect

```text
apex_engine/src/apexsim/training.py
apex_engine/src/apexsim/models/gru_world_model.py
debugging_cases/08_missing_eval_mode
debugging_cases/09_gradient_accumulation
```

## Connection to research

Research papers summarize optimization in a paragraph, but reproducing them depends on these details: gradient scale, target construction, optimizer state, evaluation mode, clipping, schedules and checkpoint selection.

## Check your understanding before continuing

1. What exactly does `backward()` mutate?
2. Why can broadcasting produce a low-looking loss with the wrong semantics?
3. What does successful one-batch overfitting prove and not prove?

## Solutions and reasoning

**1.** It accumulates gradients into `.grad` fields of leaf tensors requiring gradients; it does not update parameter values.
**2.** PyTorch expands compatible dimensions silently, comparing unintended pairs while still returning a scalar.
**3.** It proves the data path, model and optimizer can memorize a tiny sample; it does not prove generalization, correct splits or realistic rollout behaviour.

## Independent build challenge

Instrument a training step to write a JSON trace containing input shapes, loss, gradient norms and parameter-update norms. Use it to diagnose three intentionally broken configurations.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
