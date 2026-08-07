---
title: "Project APEX Ten-Project Instructor Ladder"
subtitle: "Progressive builds that culminate in the production simulation engine"
author: "OpenAI"
date: "August 2026"
toc: true
numbersections: true
---

# How the project ladder works

Each project is larger than a lab and smaller than the final system. Start from an empty file. Use the supplied implementation only after your acceptance tests run against your own attempt. A project is complete when you can explain its contracts, reproduce its results, inject its listed failure and compare at least one alternative.

Use one branch or directory per project. At the end, write an Architecture Decision Record with: context, options, evidence, decision, consequences and revisit condition.

# Project 1: One-Dimensional Car Integrator

## Mission

Create an explicit state/action transition and a deterministic rollout.

Do not begin with a framework. First draw the state, inputs, outputs and one transition. Write the acceptance test before the implementation.

## Build sequence

1. Create a minimal executable entry point.
2. Define input/output types, axes, units and invariants.
3. Implement the smallest correct path.
4. Add one deterministic example with a hand-computed answer.
5. Add structured diagnostics or plots that expose internal state.
6. Introduce the deliberate failure listed below.
7. Repair it and add a regression test.
8. Compare one simpler and one more complex implementation.
9. Write the decision record.
10. Connect the project artifact to the next project without copying hidden assumptions.

## Acceptance criteria

Position and velocity arrays match an analytical constant-acceleration case.

The criterion must be measurable. “It runs” is never sufficient. Save a report with configuration, seed, environment, output paths and limitations.

## Deliberate failure

Wrong time-step use and update order.

Before opening any debugging note, predict the symptom, the earliest failed contract and the misleading downstream symptom. Preserve the failing artifact so the repair can be proven.

## Implementation-choice review

Answer:

- What is the simplest implementation that can satisfy the acceptance test?
- What evidence would justify a more complex one?
- Which assumption is encoded in the data rather than the model?
- Which error is numerical, statistical, causal or operational?
- What result would cause you to abandon this design?

## Transfer into APEX

The simulation interface used by every later model.

Locate the corresponding production module and explain what extra responsibilities appear there: configuration, batching, validation, checkpointing, artifacts, API compatibility, monitoring or UI provenance.

## Repository

```text
projects/01_car_integrator/
```

Run the project, then rename or hide the solution and recreate its core from the README and tests. The second implementation is the real mastery check.


# Project 2: Telemetry Quality Laboratory

## Mission

Define a typed telemetry contract and reject corrupt units, ranges, timestamps and axes.

Do not begin with a framework. First draw the state, inputs, outputs and one transition. Write the acceptance test before the implementation.

## Build sequence

1. Create a minimal executable entry point.
2. Define input/output types, axes, units and invariants.
3. Implement the smallest correct path.
4. Add one deterministic example with a hand-computed answer.
5. Add structured diagnostics or plots that expose internal state.
6. Introduce the deliberate failure listed below.
7. Repair it and add a regression test.
8. Compare one simpler and one more complex implementation.
9. Write the decision record.
10. Connect the project artifact to the next project without copying hidden assumptions.

## Acceptance criteria

Every injected defect fails at the intended boundary with a useful message.

The criterion must be measurable. “It runs” is never sufficient. Save a report with configuration, seed, environment, output paths and limitations.

## Deliberate failure

Silent coercion and semantic swaps.

Before opening any debugging note, predict the symptom, the earliest failed contract and the misleading downstream symptom. Preserve the failing artifact so the repair can be proven.

## Implementation-choice review

Answer:

- What is the simplest implementation that can satisfy the acceptance test?
- What evidence would justify a more complex one?
- Which assumption is encoded in the data rather than the model?
- Which error is numerical, statistical, causal or operational?
- What result would cause you to abandon this design?

## Transfer into APEX

Canonical contract and ingestion quality gate.

Locate the corresponding production module and explain what extra responsibilities appear there: configuration, batching, validation, checkpointing, artifacts, API compatibility, monitoring or UI provenance.

## Repository

```text
projects/02_telemetry_quality/
```

Run the project, then rename or hide the solution and recreate its core from the README and tests. The second implementation is the real mastery check.


# Project 3: Lap Physics Sandbox

## Mission

Add track progress, curvature demand, grip, tyre degradation and weather to a causal toy environment.

Do not begin with a framework. First draw the state, inputs, outputs and one transition. Write the acceptance test before the implementation.

## Build sequence

1. Create a minimal executable entry point.
2. Define input/output types, axes, units and invariants.
3. Implement the smallest correct path.
4. Add one deterministic example with a hand-computed answer.
5. Add structured diagnostics or plots that expose internal state.
6. Introduce the deliberate failure listed below.
7. Repair it and add a regression test.
8. Compare one simpler and one more complex implementation.
9. Write the decision record.
10. Connect the project artifact to the next project without copying hidden assumptions.

## Acceptance criteria

Changing each scenario variable produces a directionally justified trajectory change.

The criterion must be measurable. “It runs” is never sufficient. Save a report with configuration, seed, environment, output paths and limitations.

## Deliberate failure

Impossible controls and discontinuous progress.

Before opening any debugging note, predict the symptom, the earliest failed contract and the misleading downstream symptom. Preserve the failing artifact so the repair can be proven.

## Implementation-choice review

Answer:

- What is the simplest implementation that can satisfy the acceptance test?
- What evidence would justify a more complex one?
- Which assumption is encoded in the data rather than the model?
- Which error is numerical, statistical, causal or operational?
- What result would cause you to abandon this design?

## Transfer into APEX

Offline data source and trusted evaluator for planner tests.

Locate the corresponding production module and explain what extra responsibilities appear there: configuration, batching, validation, checkpointing, artifacts, API compatibility, monitoring or UI provenance.

## Repository

```text
projects/03_lap_physics/
```

Run the project, then rename or hide the solution and recreate its core from the README and tests. The second implementation is the real mastery check.


# Project 4: Nonlinear Transition Model

## Mission

Train an MLP to predict next state and compare with persistence and linear controls.

Do not begin with a framework. First draw the state, inputs, outputs and one transition. Write the acceptance test before the implementation.

## Build sequence

1. Create a minimal executable entry point.
2. Define input/output types, axes, units and invariants.
3. Implement the smallest correct path.
4. Add one deterministic example with a hand-computed answer.
5. Add structured diagnostics or plots that expose internal state.
6. Introduce the deliberate failure listed below.
7. Repair it and add a regression test.
8. Compare one simpler and one more complex implementation.
9. Write the decision record.
10. Connect the project artifact to the next project without copying hidden assumptions.

## Acceptance criteria

Model improves matched test transitions and residual plots explain the gain.

The criterion must be measurable. “It runs” is never sufficient. Save a report with configuration, seed, environment, output paths and limitations.

## Deliberate failure

Target leakage and one-step-only conclusions.

Before opening any debugging note, predict the symptom, the earliest failed contract and the misleading downstream symptom. Preserve the failing artifact so the repair can be proven.

## Implementation-choice review

Answer:

- What is the simplest implementation that can satisfy the acceptance test?
- What evidence would justify a more complex one?
- Which assumption is encoded in the data rather than the model?
- Which error is numerical, statistical, causal or operational?
- What result would cause you to abandon this design?

## Transfer into APEX

First learned dynamics component.

Locate the corresponding production module and explain what extra responsibilities appear there: configuration, batching, validation, checkpointing, artifacts, API compatibility, monitoring or UI provenance.

## Repository

```text
projects/04_mlp_transition/
```

Run the project, then rename or hide the solution and recreate its core from the README and tests. The second implementation is the real mastery check.


# Project 5: Track Segment Encoder

## Mission

Represent cyclic progress and local geometry without discontinuity at start/finish.

Do not begin with a framework. First draw the state, inputs, outputs and one transition. Write the acceptance test before the implementation.

## Build sequence

1. Create a minimal executable entry point.
2. Define input/output types, axes, units and invariants.
3. Implement the smallest correct path.
4. Add one deterministic example with a hand-computed answer.
5. Add structured diagnostics or plots that expose internal state.
6. Introduce the deliberate failure listed below.
7. Repair it and add a regression test.
8. Compare one simpler and one more complex implementation.
9. Write the decision record.
10. Connect the project artifact to the next project without copying hidden assumptions.

## Acceptance criteria

Nearby physical positions have nearby representations across the wrap boundary.

The criterion must be measurable. “It runs” is never sufficient. Save a report with configuration, seed, environment, output paths and limitations.

## Deliberate failure

Treating progress as an ordinary unbounded scalar.

Before opening any debugging note, predict the symptom, the earliest failed contract and the misleading downstream symptom. Preserve the failing artifact so the repair can be proven.

## Implementation-choice review

Answer:

- What is the simplest implementation that can satisfy the acceptance test?
- What evidence would justify a more complex one?
- Which assumption is encoded in the data rather than the model?
- Which error is numerical, statistical, causal or operational?
- What result would cause you to abandon this design?

## Transfer into APEX

Geometry/context representation for unseen-track transfer.

Locate the corresponding production module and explain what extra responsibilities appear there: configuration, batching, validation, checkpointing, artifacts, API compatibility, monitoring or UI provenance.

## Repository

```text
projects/05_track_encoder/
```

Run the project, then rename or hide the solution and recreate its core from the README and tests. The second implementation is the real mastery check.


# Project 6: GRU Telemetry Forecaster

## Mission

Encode history and generate an autoregressive future under supplied controls.

Do not begin with a framework. First draw the state, inputs, outputs and one transition. Write the acceptance test before the implementation.

## Build sequence

1. Create a minimal executable entry point.
2. Define input/output types, axes, units and invariants.
3. Implement the smallest correct path.
4. Add one deterministic example with a hand-computed answer.
5. Add structured diagnostics or plots that expose internal state.
6. Introduce the deliberate failure listed below.
7. Repair it and add a regression test.
8. Compare one simpler and one more complex implementation.
9. Write the decision record.
10. Connect the project artifact to the next project without copying hidden assumptions.

## Acceptance criteria

Free-running horizon curves beat controls within a defined trusted range.

The criterion must be measurable. “It runs” is never sufficient. Save a report with configuration, seed, environment, output paths and limitations.

## Deliberate failure

Hidden-state reuse and teacher forcing at test.

Before opening any debugging note, predict the symptom, the earliest failed contract and the misleading downstream symptom. Preserve the failing artifact so the repair can be proven.

## Implementation-choice review

Answer:

- What is the simplest implementation that can satisfy the acceptance test?
- What evidence would justify a more complex one?
- Which assumption is encoded in the data rather than the model?
- Which error is numerical, statistical, causal or operational?
- What result would cause you to abandon this design?

## Transfer into APEX

Primary deterministic APEX V1 model.

Locate the corresponding production module and explain what extra responsibilities appear there: configuration, batching, validation, checkpointing, artifacts, API compatibility, monitoring or UI provenance.

## Repository

```text
projects/06_gru_forecaster/
```

Run the project, then rename or hide the solution and recreate its core from the README and tests. The second implementation is the real mastery check.


# Project 7: Selective SSM Memory Laboratory

## Mission

Build stable input-dependent retention and compare with GRU on long/rare dependencies.

Do not begin with a framework. First draw the state, inputs, outputs and one transition. Write the acceptance test before the implementation.

## Build sequence

1. Create a minimal executable entry point.
2. Define input/output types, axes, units and invariants.
3. Implement the smallest correct path.
4. Add one deterministic example with a hand-computed answer.
5. Add structured diagnostics or plots that expose internal state.
6. Introduce the deliberate failure listed below.
7. Repair it and add a regression test.
8. Compare one simpler and one more complex implementation.
9. Write the decision record.
10. Connect the project artifact to the next project without copying hidden assumptions.

## Acceptance criteria

Selection provides measurable memory or latency value under matched budget.

The criterion must be measurable. “It runs” is never sufficient. Save a report with configuration, seed, environment, output paths and limitations.

## Deliberate failure

Exploding state and architecture-name overclaiming.

Before opening any debugging note, predict the symptom, the earliest failed contract and the misleading downstream symptom. Preserve the failing artifact so the repair can be proven.

## Implementation-choice review

Answer:

- What is the simplest implementation that can satisfy the acceptance test?
- What evidence would justify a more complex one?
- Which assumption is encoded in the data rather than the model?
- Which error is numerical, statistical, causal or operational?
- What result would cause you to abandon this design?

## Transfer into APEX

SSM challenger and Mamba preparation.

Locate the corresponding production module and explain what extra responsibilities appear there: configuration, batching, validation, checkpointing, artifacts, API compatibility, monitoring or UI provenance.

## Repository

```text
projects/07_selective_ssm/
```

Run the project, then rename or hide the solution and recreate its core from the README and tests. The second implementation is the real mastery check.


# Project 8: RSSM Imagination Laboratory

## Mission

Separate posterior evidence from prior imagination and train stochastic latent dynamics.

Do not begin with a framework. First draw the state, inputs, outputs and one transition. Write the acceptance test before the implementation.

## Build sequence

1. Create a minimal executable entry point.
2. Define input/output types, axes, units and invariants.
3. Implement the smallest correct path.
4. Add one deterministic example with a hand-computed answer.
5. Add structured diagnostics or plots that expose internal state.
6. Introduce the deliberate failure listed below.
7. Repair it and add a regression test.
8. Compare one simpler and one more complex implementation.
9. Write the decision record.
10. Connect the project artifact to the next project without copying hidden assumptions.

## Acceptance criteria

Prior rollouts are useful and uncertainty diagnostics are calibrated on a stochastic task.

The criterion must be measurable. “It runs” is never sufficient. Save a report with configuration, seed, environment, output paths and limitations.

## Deliberate failure

Posterior leakage and KL collapse.

Before opening any debugging note, predict the symptom, the earliest failed contract and the misleading downstream symptom. Preserve the failing artifact so the repair can be proven.

## Implementation-choice review

Answer:

- What is the simplest implementation that can satisfy the acceptance test?
- What evidence would justify a more complex one?
- Which assumption is encoded in the data rather than the model?
- Which error is numerical, statistical, causal or operational?
- What result would cause you to abandon this design?

## Transfer into APEX

Dreamer-style belief model challenger.

Locate the corresponding production module and explain what extra responsibilities appear there: configuration, batching, validation, checkpointing, artifacts, API compatibility, monitoring or UI provenance.

## Repository

```text
projects/08_rssm_imagination/
```

Run the project, then rename or hide the solution and recreate its core from the README and tests. The second implementation is the real mastery check.


# Project 9: Latent MPC Planner

## Mission

Use CEM to optimize bounded action sequences through a learned model.

Do not begin with a framework. First draw the state, inputs, outputs and one transition. Write the acceptance test before the implementation.

## Build sequence

1. Create a minimal executable entry point.
2. Define input/output types, axes, units and invariants.
3. Implement the smallest correct path.
4. Add one deterministic example with a hand-computed answer.
5. Add structured diagnostics or plots that expose internal state.
6. Introduce the deliberate failure listed below.
7. Repair it and add a regression test.
8. Compare one simpler and one more complex implementation.
9. Write the decision record.
10. Connect the project artifact to the next project without copying hidden assumptions.

## Acceptance criteria

Selected actions improve trusted-environment outcome without OOD exploitation.

The criterion must be measurable. “It runs” is never sufficient. Save a report with configuration, seed, environment, output paths and limitations.

## Deliberate failure

Reward loopholes and variance collapse.

Before opening any debugging note, predict the symptom, the earliest failed contract and the misleading downstream symptom. Preserve the failing artifact so the repair can be proven.

## Implementation-choice review

Answer:

- What is the simplest implementation that can satisfy the acceptance test?
- What evidence would justify a more complex one?
- Which assumption is encoded in the data rather than the model?
- Which error is numerical, statistical, causal or operational?
- What result would cause you to abandon this design?

## Transfer into APEX

Planning layer after dynamics certification.

Locate the corresponding production module and explain what extra responsibilities appear there: configuration, batching, validation, checkpointing, artifacts, API compatibility, monitoring or UI provenance.

## Repository

```text
projects/09_latent_mpc/
```

Run the project, then rename or hide the solution and recreate its core from the README and tests. The second implementation is the real mastery check.


# Project 10: Project APEX Production Engine

## Mission

Integrate ingestion, contracts, windows, models, evaluation, pipeline, registry, API and UI.

Do not begin with a framework. First draw the state, inputs, outputs and one transition. Write the acceptance test before the implementation.

## Build sequence

1. Create a minimal executable entry point.
2. Define input/output types, axes, units and invariants.
3. Implement the smallest correct path.
4. Add one deterministic example with a hand-computed answer.
5. Add structured diagnostics or plots that expose internal state.
6. Introduce the deliberate failure listed below.
7. Repair it and add a regression test.
8. Compare one simpler and one more complex implementation.
9. Write the decision record.
10. Connect the project artifact to the next project without copying hidden assumptions.

## Acceptance criteria

A fresh run is reproducible, tested, traceable and usable through the interface.

The criterion must be measurable. “It runs” is never sufficient. Save a report with configuration, seed, environment, output paths and limitations.

## Deliberate failure

Artifact mismatch, UI false precision and source coupling.

Before opening any debugging note, predict the symptom, the earliest failed contract and the misleading downstream symptom. Preserve the failing artifact so the repair can be proven.

## Implementation-choice review

Answer:

- What is the simplest implementation that can satisfy the acceptance test?
- What evidence would justify a more complex one?
- Which assumption is encoded in the data rather than the model?
- Which error is numerical, statistical, causal or operational?
- What result would cause you to abandon this design?

## Transfer into APEX

The capstone and base for F1 25/research expansion.

Locate the corresponding production module and explain what extra responsibilities appear there: configuration, batching, validation, checkpointing, artifacts, API compatibility, monitoring or UI provenance.

## Repository

```text
projects/10_project_apex/
```

Run the project, then rename or hide the solution and recreate its core from the README and tests. The second implementation is the real mastery check.

