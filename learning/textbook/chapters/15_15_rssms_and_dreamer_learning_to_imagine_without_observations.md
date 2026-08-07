# 15. RSSMs and Dreamer: Learning to Imagine Without Observations

> **Instructor objective:** Implement the logic of a recurrent state-space model, distinguish posterior training from prior imagination, and understand Dreamer as a system rather than a buzzword.

![15. RSSMs and Dreamer: Learning to Imagine Without Observations](../figures/14_rssm.png)

## The problem that earns this chapter

A deterministic recurrent model predicts one future. Real driving contains unobserved factors, noisy evidence and multiple plausible outcomes. An RSSM maintains deterministic memory plus a stochastic latent belief. The hardest requirement is that imagination must continue when future observations are absent.

### Predict before reading

During training you know the next observation; during planning you do not. Which distribution may use the observation: the prior, posterior, both or neither? What would happen if imagination secretly used posterior information?

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

An RSSM commonly has deterministic state `h_t` and stochastic state `z_t`. The transition updates `h_t` from previous latent/action. The prior predicts a distribution over `z_t` from `h_t`. During training, an encoder provides observation evidence and a posterior refines that distribution. The decoder predicts observation/state from `h_t,z_t`.

The KL term teaches the prior to resemble the posterior enough that prior-only imagination remains useful. Reconstruction or prediction terms teach the latent to represent evidence. These objectives can conflict. Posterior collapse, overconfident priors and compounding uncertainty are practical failures, not footnotes.

Dreamer adds reward/continuation models and learns actor/critic behaviour from trajectories imagined by the world model. Before trusting control, APEX must establish that interventions produce realistic, calibrated rollouts.

## Vocabulary that now has a job

**Concept: Deterministic state h**
- **Meaning in plain language:** Recurrent memory summarizing past latent/action sequence.
- **Role inside APEX:** Carries stable temporal context.

**Concept: Prior**
- **Meaning in plain language:** Latent distribution predicted without current observation.
- **Role inside APEX:** Used during imagination and planning.

**Concept: Posterior**
- **Meaning in plain language:** Latent distribution conditioned on current observation evidence.
- **Role inside APEX:** Used during training/state inference.

**Concept: Imagination**
- **Meaning in plain language:** Rollout using learned prior dynamics without future observations.
- **Role inside APEX:** Generates counterfactual telemetry trajectories.


## Worked example: calculate it by hand

Suppose posterior is `N(μ_q=1, σ_q=0.5)` and prior is `N(μ_p=0, σ_p=1)`. The one-dimensional Gaussian KL `KL(q||p)` is

\[\log(\sigma_p/\sigma_q)+rac{\sigma_q^2+(\mu_q-\mu_p)^2}{2\sigma_p^2}-rac12.\]

Substitute:

- `log(1/0.5)=0.693`
- numerator `0.25 + 1 = 1.25`
- divide by 2 gives `0.625`
- subtract 0.5
- total `0.818`

The gap signals that the prior cannot yet reproduce the posterior belief. Reducing it by making both distributions uninformative would also be bad; reconstruction/prediction must remain strong.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/17_rssm_step`

### What we are about to build

Construct one RSSM step: update deterministic memory, compute prior statistics, then compute posterior statistics using observation embedding. Inspect all shapes.

### Runnable implementation

```python
import torch
from torch import nn

cell=nn.GRUCell(5,8); prior=nn.Linear(8,4); posterior=nn.Linear(8+3,4)
h=torch.zeros(2,8); prev_z=torch.zeros(2,2); action=torch.randn(2,3); obs_embed=torch.randn(2,3)
h=cell(torch.cat([prev_z,action],-1),h)
prior_stats=prior(h); post_stats=posterior(torch.cat([h,obs_embed],-1))
print("h",h.shape,"prior",prior_stats.shape,"posterior",post_stats.shape)

```

### Observed output from the packaged solution

```text
h torch.Size([2, 8]) prior torch.Size([2, 4]) posterior torch.Size([2, 4])
```

### Read the important lines like English

**Code: h=cell(torch.cat([prev_z,action],-1),h)**
- **What the line is doing:** Advance deterministic memory using previous latent and current action.
- **What to inspect:** Current observation is intentionally absent from this transition.

**Code: prior_stats=prior(h)**
- **What the line is doing:** Predict latent distribution using only imagined memory.
- **What to inspect:** This path must work at inference with no future observation.

**Code: post_stats=posterior(torch.cat([h,obs_embed],-1))**
- **What the line is doing:** Refine latent belief using current evidence during training.
- **What to inspect:** Posterior information must not leak into prior-only evaluation.


### State and tensor trace

```text
training step:
prev z + action → h_t → prior p(z_t|h_t)
                         + observation embedding → posterior q(z_t|h_t,o_t)
posterior sample + h_t → decode target

imagination step:
prev z + action → h_t → prior sample → decode prediction
(no observation branch)
```

Evaluate both posterior reconstruction and prior rollout. They answer different questions.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Use posterior samples during test rollout. Then set KL weight to zero and compare prior imagination with posterior reconstruction.

### Diagnose from the earliest failed contract

If posterior metrics are good but prior rollout is poor, inspect prior–posterior KL by horizon and latent dimension. If KL is near zero but outputs ignore observations, inspect collapse.

### Repair and lock the repair with a test

Separate evaluation functions for posterior reconstruction and prior imagination. Add a test that imagination accepts no future observation tensor. Tune KL with explicit diagnostics, not only total loss.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Deterministic GRU world model**
- **Choose it when:** One likely future and stable V1 forecasting are sufficient.
- **Do not choose it when:** Uncertainty/multi-modal futures are central.

**Implementation: RSSM**
- **Choose it when:** You need a learned belief state and prior imagination.
- **Do not choose it when:** Data/budget cannot support stable latent training or benefits are unmeasured.

**Implementation: Ensemble deterministic models**
- **Choose it when:** You want practical epistemic uncertainty with simple training.
- **Do not choose it when:** Compute or storage prevents multiple models.

**Implementation: Full Dreamer actor-critic**
- **Choose it when:** Dynamics, reward and continuation models are validated and control is the target.
- **Do not choose it when:** The world model can still be exploited or interventions are poorly represented.


APEX includes a compact RSSM challenger and preserves its weaker short-budget result as a debugging lesson. The deterministic GRU remains V1 primary until stochastic imagination demonstrates decision value and calibration.

## Transfer the lesson into Project APEX

Train GRU and RSSM under the same session split. Compare posterior reconstruction, prior horizon error, KL, physical violations and scenario sensitivity—not just total training loss.

### Repository path to inspect

```text
projects/08_rssm_imagination/main.py
apex_engine/src/apexsim/models/rssm.py
apex_engine/configs/rssm_fast.yaml
debugging_cases/11_kl_collapse
```

## Connection to research

DreamerV3 is an integrated agent: world model, imagined trajectories, reward/continuation prediction and actor-critic learning. Copying an RSSM cell is not equivalent to reproducing Dreamer’s training system or robustness.

## Check your understanding before continuing

1. Why must the prior exclude current observation evidence?
2. What does good posterior reconstruction but poor prior rollout mean?
3. Why might a deterministic model outperform an RSSM on APEX V1?

## Solutions and reasoning

**1.** The future observation is unavailable during imagination; including it leaks the answer and invalidates the simulator.
**2.** The latent encoder can explain observed frames, but learned dynamics cannot predict the corresponding latent beliefs without evidence.
**3.** Small data, short training, near-deterministic telemetry, KL optimization difficulty and evaluation focused on mean trajectory can all favour the simpler model.

## Independent build challenge

Implement a two-dimensional RSSM on a stochastic toy car. Plot posterior and prior distributions over time, then show a case where uncertainty widens under an unseen control sequence.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
