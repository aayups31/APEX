# 16. JEPA, LeWorldModel and Fine-Tuning Existing Representations

> **Instructor objective:** Understand predictive representation learning, decide when not to reconstruct raw observations, and build a disciplined fine-tuning strategy.

![16. JEPA, LeWorldModel and Fine-Tuning Existing Representations](../figures/16_jepa.png)

## The problem that earns this chapter

Pixel or telemetry reconstruction forces a model to spend capacity on every observable detail, including noise that may not matter for future decisions. JEPA-style methods predict target representations instead. LeWorldModel-style work explores efficient latent world modelling and planning. The engineering question is not which acronym is newest; it is what target contains the information APEX needs.

### Predict before reading

Suppose two future telemetry frames differ only in an unpredictable sensor-noise feature. A raw reconstruction loss treats them as different. Should a predictive representation loss treat them as different? What determines the answer?

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

Joint-embedding predictive architectures encode context and target views, then train a predictor to infer the target representation from context. The target encoder defines what counts as meaningful similarity. Because the loss is in representation space, the model can ignore some raw variation—if the representation has learned to ignore it.

This creates a new failure possibility: representation collapse or shortcuts. Stop-gradient/target-encoder design, masking strategy and representation diagnostics matter. In telemetry, a future-latent target could emphasize dynamics while de-emphasizing sensor noise, but it might also discard rare safety-critical events.

Fine-tuning an existing model makes sense when its input semantics, sequence structure and learned invariances transfer. Adaptation choices range from a frozen encoder plus new head, through parameter-efficient adapters, to full fine-tuning. Start with the least invasive option that can represent the domain shift, and compare against training a small model from scratch.

## Vocabulary that now has a job

**Concept: Representation target**
- **Meaning in plain language:** The encoded feature vector the predictor must infer.
- **Role inside APEX:** Potential future-dynamics target instead of raw telemetry.

**Concept: Stop gradient / target encoder**
- **Meaning in plain language:** Prevents both sides from trivially co-adapting in unstable ways.
- **Role inside APEX:** Part of a non-collapsing predictive objective.

**Concept: Linear probe**
- **Meaning in plain language:** A simple supervised head used to test what information a representation contains.
- **Role inside APEX:** Measures speed, curvature, tyre or event information in latent state.

**Concept: Fine-tuning**
- **Meaning in plain language:** Adapt pretrained parameters to a new domain/task.
- **Role inside APEX:** Possible when a relevant sequence/world model checkpoint exists.


## Worked example: calculate it by hand

Compare two losses for target vector `y=[10.0, 0.02]` where the second feature is pure noise. Prediction A is `[9.8, 0.50]`; prediction B is `[9.8, −0.40]`. Raw MSE differs because of noise.

If a target encoder maps both raw targets to a dynamics representation `[speed_bin=10, regime=straight]`, their representation loss can be identical. This is desirable only if the discarded noise truly has no predictive or decision value.

For fine-tuning, suppose a pretrained encoder has one million parameters. A frozen-head experiment trains 5,000 parameters; an adapter trains 50,000; full tuning changes all million. These are nested hypotheses about how much the representation must change.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/15_autoencoder`

### What we are about to build

Use the autoencoder lab as a concrete representation baseline, then modify its objective conceptually: predict a future latent code rather than reconstruct the current input. Add a linear probe for a known future variable.

### Runnable implementation

```python
import torch
from torch import nn

torch.manual_seed(3); x=torch.randn(256,12)
enc=nn.Linear(12,3); dec=nn.Linear(3,12); opt=torch.optim.Adam(list(enc.parameters())+list(dec.parameters()),lr=0.03)
for _ in range(80):
    opt.zero_grad(); z=torch.tanh(enc(x)); recon=dec(z); loss=((recon-x)**2).mean(); loss.backward(); opt.step()
print("latent",z.shape,"loss",float(loss))

```

### Observed output from the packaged solution

```text
latent torch.Size([256, 3]) loss 0.7505914568901062
/mnt/data/Project_APEX_Engineering_Apprenticeship/labs/15_autoencoder/solution.py:8: UserWarning: Converting a tensor with requires_grad=True to a scalar may lead to unexpected behavior.
Consider using tensor.detach() first. (Triggered internally at /pytorch/torch/csrc/autograd/generated/python_variable_methods.cpp:836.)
  print("latent",z.shape,"loss",float(loss))
```

### Read the important lines like English

**Code: z=torch.tanh(enc(x))**
- **What the line is doing:** Produce a learned representation through a bottleneck.
- **What to inspect:** Inspect variance and pairwise similarity to detect collapse.

**Code: recon=dec(z)**
- **What the line is doing:** The original lab asks the latent to reconstruct raw input.
- **What to inspect:** Replace/augment this with future-target representation prediction.

**Code: loss=((recon-x)**2).mean()**
- **What the line is doing:** Raw reconstruction values every feature according to scale and frequency.
- **What to inspect:** Normalize or weight features, or choose a different target.


### State and tensor trace

```text
context history ─► context encoder ─► predictor ─► predicted target embedding
future target ───► target encoder ───────────────► target embedding
                                                ↓
                                      latent-space loss
```

After training, freeze the encoder and probe whether latent state predicts physical variables and future events.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Train both context and target encoders with no asymmetry or variance checks until they output nearly constant vectors. Observe low latent loss and useless probes.

### Diagnose from the earliest failed contract

Track per-dimension variance, embedding covariance, nearest-neighbour diversity and probe accuracy. Low loss with collapsed variance is not successful representation learning.

### Repair and lock the repair with a test

Use an appropriate target/stop-gradient design, masking that prevents shortcuts, normalization, and diagnostic probes. Add rare-event retrieval tests so abstraction does not erase critical evidence.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Raw reconstruction**
- **Choose it when:** Exact observation generation or interpretable state recovery matters.
- **Do not choose it when:** Unpredictable detail dominates and decisions depend on abstract dynamics.

**Implementation: Predictive latent loss**
- **Choose it when:** Future-relevant representation is the main goal.
- **Do not choose it when:** You cannot validate what information the latent discarded.

**Implementation: Frozen pretrained encoder**
- **Choose it when:** Source and target semantics align and data are limited.
- **Do not choose it when:** The representation lacks essential F1 variables.

**Implementation: Full fine-tuning**
- **Choose it when:** You have sufficient data/compute and major domain adaptation is needed.
- **Do not choose it when:** Small data risks catastrophic overfitting or a small scratch model is already competitive.


APEX V1 trains small models from scratch because the canonical telemetry state is compact and no assumed checkpoint perfectly matches its action/context semantics. The curriculum nevertheless prepares an adapter/probe-first fine-tuning experiment for future larger datasets.

## Transfer the lesson into Project APEX

Add a latent probe suite to GRU, SSM and RSSM hidden states. If using a pretrained sequence encoder, freeze it first, train the same prediction head, and compare data efficiency and horizon curves.

### Repository path to inspect

```text
labs/15_autoencoder/solution.py
apex_engine/src/apexsim/models/
apex_engine/src/apexsim/evaluation.py
research_reading/
```

## Connection to research

I-JEPA predicts representations of target image regions from context rather than reconstructing pixels. LeWorldModel explores latent world modelling and planning efficiency. Transfer their design principles only after mapping observation, action, target and evaluation semantics to the F1 domain.

## Check your understanding before continuing

1. Why can latent loss be low under representation collapse?
2. What should a linear probe tell you?
3. What is the safest first fine-tuning experiment?

## Solutions and reasoning

**1.** If both target and prediction are nearly constant, they match without containing information.
**2.** Whether a simple readout can recover a specified physical or predictive variable, revealing what information is accessible in the representation.
**3.** Freeze the pretrained backbone, train a small task head under the same split, and compare with simple baselines before unfreezing parameters.

## Independent build challenge

Build a future-latent predictor on synthetic telemetry. Evaluate reconstruction, future-state probes, rare-event retrieval and rollout value. Write a decision record comparing it with an RSSM objective.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
