# 1. Build a Simulator Before You Build a Neural Network

> **Instructor objective:** Understand simulation as repeated state transition, then build and inspect the smallest causal driving world.

![1. Build a Simulator Before You Build a Neural Network](../figures/01_simulation_loop.png)

## The problem that earns this chapter

You want a model that can imagine an F1 car several seconds into the future. It is tempting to open PyTorch immediately. That would hide the central question: **what does it mean for the world to move forward by one step?** Before learning anything from data, we need a transparent transition rule whose mistakes we can see.

### Predict before reading

A car is moving at 20 m/s. During the next 0.2 seconds, its acceleration is 3 m/s². Predict the next velocity and the distance travelled if we use the simplest Euler update. Then decide which quantity should be updated first.

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

A simulator stores a description of the world, receives an intervention, applies a transition, and returns a new description. In our first world, the state is only velocity and position. The action is a throttle value. The transition is an equation. Repeating the equation produces a rollout.

This hand-written simulator is already a world model in the broad engineering sense: it predicts a future state from a present state and an action. It is not a *learned* world model. That difference matters. A learned model replaces part of the transition rule with parameters estimated from evidence. The interface should remain stable: state in, action in, next state out.

Starting here gives us an oracle for later debugging. If a neural network predicts that stronger braking increases velocity, we can compare it with the toy causal rule and ask whether the data contract, target alignment, or learned relationship is broken.

## Vocabulary that now has a job

**Concept: State**
- **Meaning in plain language:** The minimum information carried from one step to the next.
- **Role inside APEX:** Speed, progress, tyre state and other dynamic variables.

**Concept: Action**
- **Meaning in plain language:** A controllable input applied during a transition.
- **Role inside APEX:** Throttle, brake, steering and gear choices.

**Concept: Transition**
- **Meaning in plain language:** The rule that maps current state and action to next state.
- **Role inside APEX:** Hand-written physics, a GRU, an SSM or an RSSM.

**Concept: Rollout**
- **Meaning in plain language:** Repeatedly applying the transition to create a future trajectory.
- **Role inside APEX:** Imagining several seconds of future telemetry.


## Worked example: calculate it by hand

Euler integration uses

\[v_{t+1}=v_t+a_t\Delta t\]

and

\[x_{t+1}=x_t+v_t\Delta t.\]

With \(v_t=20\), \(a_t=3\), and \(\Delta t=0.2\):

1. Velocity change: \(3	imes0.2=0.6\) m/s.
2. Next velocity: \(20+0.6=20.6\) m/s.
3. Distance using the current velocity: \(20	imes0.2=4.0\) m.
4. Next position, if starting at zero: 4.0 m.

A semi-implicit variant updates velocity first and then position, producing \(20.6	imes0.2=4.12\) m. Neither is universally “the answer”; the numerical method is an implementation choice whose error shrinks with smaller time steps.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/02_vectorized_kinematics`

### What we are about to build

A tiny vectorized integrator that converts an acceleration sequence into velocity and position. You will see that a rollout is just a loop with state carried between iterations.

### Runnable implementation

```python
import numpy as np

dt = 0.2
time = np.arange(0, 5, dt)
speed = 20 + 4*np.sin(time)
accel = np.gradient(speed, dt)
reconstructed = speed[0] + np.cumsum(accel)*dt
print("first accelerations:", accel[:5].round(3))
print("max reconstruction error:", float(np.max(np.abs(reconstructed-speed))))

```

### Observed output from the packaged solution

```text
first accelerations: [3.973 3.894 3.66  3.279 2.768]
max reconstruction error: 0.7946773231802453
```

### Read the important lines like English

**Code: dt = 0.1**
- **What the line is doing:** Define how much simulated time one transition represents.
- **What to inspect:** Changing dt changes both numerical error and sequence length.

**Code: velocity[i] = velocity[i-1] + acceleration[i-1] * dt**
- **What the line is doing:** Apply one causal state transition.
- **What to inspect:** The action at step i−1 affects state i, not state i−1.

**Code: position[i] = position[i-1] + velocity[i-1] * dt**
- **What the line is doing:** Integrate velocity into position.
- **What to inspect:** This implementation uses explicit Euler.


### State and tensor trace

Trace one step with `velocity[0]=10`, `acceleration[0]=2`, and `dt=0.1`:

```text
before:  velocity = 10.0 m/s, position = 0.0 m
action:  acceleration = 2.0 m/s²
change:  Δv = 2.0 × 0.1 = 0.2 m/s
after:   velocity = 10.2 m/s
position change = 10.0 × 0.1 = 1.0 m
after:   position = 1.0 m
```

The array is merely a stored history of repeated state updates.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Change `dt` from 0.1 to 1.0 without changing the acceleration profile. Compare the trajectory. Then update position with the newly computed velocity and compare again.

### Diagnose from the earliest failed contract

If the two trajectories disagree, the code is not necessarily broken. The earliest changed contract is the numerical integration scheme and time resolution. Ask whether your result converges as `dt` becomes smaller.

### Repair and lock the repair with a test

Add a test that simulates constant acceleration for one second at several time steps. Assert that final velocity approaches the analytical value `v0 + a*t`. Document the position integrator you chose.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Explicit Euler**
- **Choose it when:** You need the simplest transparent baseline and small time steps.
- **Do not choose it when:** Long unstable rollouts or stiff dynamics.

**Implementation: Semi-implicit Euler**
- **Choose it when:** Velocity drives position and you want slightly better stability at similar cost.
- **Do not choose it when:** You need high-order accuracy.

**Implementation: Runge–Kutta**
- **Choose it when:** The hand-written dynamics are smooth and numerical accuracy matters.
- **Do not choose it when:** The transition is learned from discrete telemetry where solver precision is not the main bottleneck.

**Implementation: Learned transition**
- **Choose it when:** Important dynamics are unknown but repeated observations are available.
- **Do not choose it when:** You have not defined state, action, timing or evaluation.


For APEX, the toy simulator uses simple integration because its purpose is causal education and synthetic data generation. The learned model then predicts transitions on a fixed telemetry grid. We do not pretend the neural network is a high-fidelity rigid-body solver.

## Transfer the lesson into Project APEX

The production engine keeps the same conceptual interface: a history encodes the current world, future controls supply actions, and the model emits future states. The complexity grows, but the causal contract learned here should remain visible.

### Repository path to inspect

```text
projects/01_car_integrator/main.py
apex_engine/src/apexsim/data/synthetic.py
apex_engine/src/apexsim/simulation.py
```

## Connection to research

Dreamer-style systems are sophisticated because they learn transition dynamics in a latent state, but they still depend on this repeated transition idea. If you cannot explain the toy rollout, an RSSM will only hide confusion behind distributions.

## Check your understanding before continuing

1. Why is a one-step transition different from a rollout?
2. What changes when `dt` is halved?
3. Why should actions at time t usually predict state at time t+1 rather than state at time t?

## Solutions and reasoning

**1.** A one-step transition consumes one state/action pair; a rollout feeds predictions back repeatedly, so errors change later inputs.
**2.** There are twice as many transitions for the same physical duration, usually reducing integration error but increasing compute and sequence length.
**3.** The state at time t was observed before or at the moment the action is applied; using the same-time target can leak the answer or teach no causal delay.

## Independent build challenge

Implement both explicit and semi-implicit Euler. Plot their position error against the analytical solution for five time steps. Write an ADR choosing one for the synthetic APEX generator.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
