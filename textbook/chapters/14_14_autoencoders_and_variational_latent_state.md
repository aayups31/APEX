# 14. Autoencoders and Variational Latent State

> **Instructor objective:** Learn representation compression by building it, then add probabilistic latent variables without confusing reconstruction with useful world modelling.

![14. Autoencoders and Variational Latent State](../figures/13_latent.png)

## The problem that earns this chapter

Raw observations can contain redundant or noisy dimensions. A world model may benefit from a compact latent state, but compression can discard precisely the small variable needed for future prediction. A good reconstruction is not automatically a good predictive representation.

### Predict before reading

A telemetry vector has 12 features, but only speed, curvature and tyre age determine the next state. If an autoencoder compresses to three dimensions, will those three necessarily correspond to the three causal variables? Why or why not?

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

An autoencoder learns an encoder `z=f(x)` and decoder `x̂=g(z)` by minimizing reconstruction error. The bottleneck pressures the latent to preserve common information. Nothing requires each dimension to align with a human variable, and high-variance nuisance features may dominate.

A variational autoencoder predicts a distribution—usually mean and log variance—rather than one code. Sampling uses `z = μ + σ⊙ε`, which keeps the path differentiable with respect to `μ` and `σ`. A KL term regularizes the posterior toward a prior, enabling sampling but creating a tradeoff: too weak and the latent is irregular; too strong and it can ignore observations.

For world models, the latent should preserve information useful for dynamics and reward, not only instantaneous reconstruction. Temporal prediction losses or task probes test this.

## Vocabulary that now has a job

**Concept: Encoder**
- **Meaning in plain language:** Maps a high-dimensional observation into a compact representation.
- **Role inside APEX:** Compresses telemetry/history into latent state.

**Concept: Decoder**
- **Meaning in plain language:** Reconstructs or predicts observable state from latent representation.
- **Role inside APEX:** Produces interpretable future telemetry.

**Concept: Reparameterization**
- **Meaning in plain language:** Express stochastic sampling as differentiable transformation of parameter-free noise.
- **Role inside APEX:** Allows RSSM/VAE posterior training.

**Concept: KL divergence**
- **Meaning in plain language:** Penalty measuring difference between posterior and prior distributions.
- **Role inside APEX:** Regularizes stochastic latent state and aligns imagination with inference.


## Worked example: calculate it by hand

For one latent dimension with `μ=0.2`, `log variance=-1`:

1. Variance: `exp(-1)=0.3679`.
2. Standard deviation: `exp(-0.5)=0.6065`.
3. If sampled noise `ε=1.0`, then `z=0.2+0.6065=0.8065`.
4. KL to standard normal is `−0.5(1 + logvar − μ² − exp(logvar))`.
5. Substitute: `−0.5(1−1−0.04−0.3679)=0.20395`.

The KL is zero only when posterior mean is zero and variance is one. Driving every posterior to that point would erase observation information.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/16_vae_reparameterization`

### What we are about to build

Compute posterior standard deviation, sample with reparameterization, and calculate KL for a tiny batch. Pair it with the autoencoder lab to compare deterministic and stochastic codes.

### Runnable implementation

```python
import torch

mu=torch.tensor([[0.2,-0.4]]); logvar=torch.tensor([[-1.0,0.5]])
std=torch.exp(0.5*logvar); eps=torch.randn_like(std); z=mu+std*eps
kl=-0.5*torch.sum(1+logvar-mu.pow(2)-logvar.exp(),dim=1)
print("mu",mu,"std",std,"sample",z,"KL",kl)

```

### Observed output from the packaged solution

```text
mu tensor([[ 0.2000, -0.4000]]) std tensor([[0.6065, 1.2840]]) sample tensor([[-0.1015,  0.6276]]) KL tensor([0.3583])
```

### Read the important lines like English

**Code: std=torch.exp(0.5*logvar)**
- **What the line is doing:** Convert log variance into standard deviation.
- **What to inspect:** The factor 0.5 appears because std is square root of variance.

**Code: eps=torch.randn_like(std)**
- **What the line is doing:** Sample parameter-free standard normal noise.
- **What to inspect:** Random seed affects the sampled latent, not posterior parameters.

**Code: z=mu+std*eps**
- **What the line is doing:** Create a stochastic sample with gradients flowing through μ and std.
- **What to inspect:** Inspect multiple samples to see uncertainty.

**Code: kl=...**
- **What the line is doing:** Measure posterior departure from the unit Gaussian prior.
- **What to inspect:** Monitor KL by dimension for collapse or overuse.


### State and tensor trace

```text
observation x
   ↓ encoder
μ(x), logσ²(x)
   ↓ sample ε ~ N(0,I)
z = μ + σ ε
   ↓ decoder
reconstruction x̂

loss = reconstruction error + β × KL
```

Print latent means, standard deviations and KL—not only total loss.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Set KL weight extremely high and inspect whether reconstructions become generic. Then set it to zero and sample from the prior at inference.

### Diagnose from the earliest failed contract

High KL with poor reconstruction suggests excessive regularization. Near-zero KL in every dimension plus decoder independence from `z` suggests posterior collapse. Good reconstruction with nonsensical prior samples suggests an unstructured latent.

### Repair and lock the repair with a test

Use KL warm-up/free-nats or capacity control only after measuring the failure. Add latent probes for future speed, curvature and tyre state, and compare reconstruction versus predictive usefulness.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Deterministic autoencoder**
- **Choose it when:** Compression and reconstruction matter; uncertainty is not required.
- **Do not choose it when:** You need coherent sampling or probabilistic belief.

**Implementation: VAE**
- **Choose it when:** A smooth sampleable latent distribution is useful.
- **Do not choose it when:** KL tradeoffs add complexity without serving the downstream task.

**Implementation: Predictive encoder**
- **Choose it when:** Future-relevant structure matters more than reconstructing every input detail.
- **Do not choose it when:** You still require high-fidelity observation generation.

**Implementation: No bottleneck**
- **Choose it when:** State is already small and semantically meaningful.
- **Do not choose it when:** High-dimensional noisy observations overwhelm dynamics learning.


APEX telemetry is already compact, so V1 can predict state directly. The RSSM uses stochastic latent state to study uncertainty and imagination, not because compression is automatically necessary.

## Transfer the lesson into Project APEX

Run autoencoder and VAE labs, then inspect RSSM posterior statistics. Create a probe predicting future speed from latent state and compare it with reconstruction loss.

### Repository path to inspect

```text
labs/15_autoencoder/solution.py
labs/16_vae_reparameterization/solution.py
apex_engine/src/apexsim/models/rssm.py
debugging_cases/11_kl_collapse
```

## Connection to research

JEPA-style approaches challenge the need to reconstruct raw observations, arguing that useful representations can be learned by predicting abstract target embeddings. This is especially relevant when raw detail is unpredictable or irrelevant.

## Check your understanding before continuing

1. Why can low reconstruction error coexist with poor future prediction?
2. What is the purpose of the KL term?
3. Why does reparameterization enable gradients?

## Solutions and reasoning

**1.** The encoder may preserve visually/statistically dominant current detail while discarding small causal variables needed later.
**2.** It regularizes the posterior toward the prior so latent space can support coherent prior sampling/imagination.
**3.** The random variable is expressed as a deterministic differentiable function of parameters and independent noise, so gradients pass through μ and σ.

## Independent build challenge

Train an autoencoder on synthetic telemetry with nuisance noise. Compare latent probes for future speed under reconstruction-only and reconstruction-plus-future-prediction objectives.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
