# 18. Planning With MPC and the Cross-Entropy Method

> **Instructor objective:** Use a world model to compare action sequences, understand CEM search, and learn why planners exploit model and reward defects.

![18. Planning With MPC and the Cross-Entropy Method](../figures/18_cem.png)

## The problem that earns this chapter

Prediction answers “what happens if we do this?” Planning asks “what should we do?” A planner proposes action sequences, imagines outcomes through the world model, scores them, and improves its proposal. This creates a powerful adversary: it actively searches for unrealistic trajectories that maximize the score.

### Predict before reading

A reward gives +1 for speed and no penalty for leaving the track or braking instability. What action sequence will a planner prefer? Why is this not primarily a planner bug?

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

Model predictive control repeatedly plans over a finite horizon, executes only the first action, observes the new state, and replans. This feedback limits drift compared with committing to a long open-loop sequence.

The cross-entropy method maintains a distribution over action sequences. It samples candidates, rolls them through the model, keeps an elite fraction, and refits mean/variance toward those elites. Repetition concentrates search around high-scoring actions.

Planner quality is bounded by world-model validity and reward completeness. Optimization pressure finds loopholes humans do not notice in average evaluation. Therefore planning tests should include adversarial actions, uncertainty penalties, constraints and real-environment verification before control is trusted.

## Vocabulary that now has a job

**Concept: Model predictive control**
- **Meaning in plain language:** Plan over a horizon, execute a short prefix, observe, and replan.
- **Role inside APEX:** Future scenario/strategy layer after dynamics validation.

**Concept: CEM**
- **Meaning in plain language:** Sampling optimizer that iteratively refits an action distribution to elite candidates.
- **Role inside APEX:** Simple derivative-free planner through imagined telemetry.

**Concept: Reward model**
- **Meaning in plain language:** Function scoring predicted trajectories for the decision objective.
- **Role inside APEX:** Could combine progress, stability, tyre use and constraint penalties.

**Concept: Model exploitation**
- **Meaning in plain language:** Planner finds actions that score well because the learned model is wrong.
- **Role inside APEX:** A major risk under unusual controls.


## Worked example: calculate it by hand

Suppose CEM samples 500 six-step throttle sequences. It scores final-speed error to a target plus smoothness. It keeps 50 elites (top 10%). New mean and standard deviation are the elite sample statistics.

If initial mean is 0.5 and standard deviation 0.3, one iteration may shift the early-step means toward 0.8 where acceleration helps. After several iterations variance shrinks. Too-rapid variance collapse can trap search; a minimum standard deviation preserves exploration.

MPC then applies only the first action, receives new evidence and replans. The remaining five actions are proposals, not a fixed command commitment.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/18_cem_planning`

### What we are about to build

Run CEM against a tiny differentiable-free speed simulator. Watch mean action sequence and best score improve over five iterations.

### Runnable implementation

```python
import numpy as np

rng=np.random.default_rng(0); horizon=6; mean=np.full(horizon,0.5); std=np.full(horizon,0.3)
for it in range(5):
    actions=np.clip(rng.normal(mean,std,(500,horizon)),0,1)
    speed=40+np.cumsum(2*actions-0.4,axis=1)
    score=-(speed[:,-1]-48)**2-0.1*np.sum(np.diff(actions,axis=1)**2,axis=1)
    elite=actions[np.argsort(score)[-50:]]
    mean,std=elite.mean(0),elite.std(0)+1e-3
    print(it,mean.round(2),score.max().round(3))

```

### Observed output from the packaged solution

```text
0 [0.71 0.68 0.7  0.62 0.67 0.71] -1.123
1 [0.84 0.8  0.82 0.82 0.83 0.82] -0.019
2 [0.86 0.84 0.86 0.88 0.87 0.9 ] -0.005
3 [0.87 0.85 0.85 0.87 0.89 0.87] -0.001
4 [0.86 0.84 0.85 0.88 0.89 0.87] -0.001
```

### Read the important lines like English

**Code: actions=np.clip(rng.normal(mean,std,(500,horizon)),0,1)**
- **What the line is doing:** Sample bounded candidate action sequences from the current proposal.
- **What to inspect:** Clipping changes the distribution near limits.

**Code: score=...**
- **What the line is doing:** Evaluate imagined outcome and smoothness under the toy world model.
- **What to inspect:** Every omitted constraint becomes a possible exploit.

**Code: elite=actions[np.argsort(score)[-50:]]**
- **What the line is doing:** Select the highest-scoring candidate sequences.
- **What to inspect:** Elite fraction controls search pressure.

**Code: mean,std=elite.mean(0),elite.std(0)+1e-3**
- **What the line is doing:** Refit proposal distribution and preserve minimum exploration.
- **What to inspect:** Monitor premature variance collapse.


### State and tensor trace

```text
proposal distribution over action sequences
      ↓ sample N candidates
world model rollout for each candidate
      ↓ reward + constraints
select top K elites
      ↓ fit new mean/std
repeat → execute first action → observe → replan
```

Log the best candidate, elite diversity, uncertainty and physical violations each iteration.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Remove the smoothness term and allow throttle beyond one. Add a model region where extreme throttle incorrectly increases speed without penalty. Watch CEM discover it.

### Diagnose from the earliest failed contract

Replay planned trajectories under a trusted simulator or held-out real transitions. Compare planner actions with the training action distribution. Large OOD actions and low predicted uncertainty are red flags.

### Repair and lock the repair with a test

Enforce hard action bounds, add physically justified constraints, penalize uncertainty/OOD distance, and use receding-horizon verification. Create adversarial planner tests as part of model evaluation.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Grid search**
- **Choose it when:** Action space and horizon are tiny.
- **Do not choose it when:** Combinatorial sequences.

**Implementation: CEM**
- **Choose it when:** Continuous bounded actions, no gradients required and batch rollout is cheap.
- **Do not choose it when:** Model evaluations are extremely expensive or multi-modal search collapses.

**Implementation: Gradient planning**
- **Choose it when:** World model/reward are differentiable and smooth.
- **Do not choose it when:** Discrete actions, poor local optima or unstable gradients.

**Implementation: Actor network**
- **Choose it when:** Fast repeated decisions justify amortizing planning through policy learning.
- **Do not choose it when:** World model/reward is not validated or policy can exploit it unseen.


APEX V1 exposes manual counterfactual controls and includes a latent MPC project, but does not claim autonomous race control. Planning becomes a later stage after dynamics and reward validation.

## Transfer the lesson into Project APEX

Connect CEM to the scenario rollout interface using bounded throttle/brake actions. Evaluate planned sequences against the synthetic ground-truth environment before any live integration.

### Repository path to inspect

```text
labs/18_cem_planning/solution.py
projects/09_latent_mpc/main.py
apex_engine/src/apexsim/simulation.py
debugging_cases/12_planner_exploitation
```

## Connection to research

Dreamer replaces repeated online search with an actor and critic trained from imagined trajectories, but the exploitation problem remains. Better optimization can make model defects more dangerous, not less.

## Check your understanding before continuing

1. Why does MPC execute only the first planned action?
2. What does elite variance tell you?
3. How can uncertainty be used in planning?

## Solutions and reasoning

**1.** New observations correct model drift and changing conditions before the next action.
**2.** How concentrated high-scoring candidates are; rapid collapse can indicate convergence or premature loss of exploration.
**3.** Penalize uncertain trajectories, constrain planning to trusted regions, or trigger abstention/human review.

## Independent build challenge

Add braking and curvature constraints to the CEM lab. Create a hidden model defect, show the planner exploit it, then design an evaluation that catches the exploit before deployment.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
