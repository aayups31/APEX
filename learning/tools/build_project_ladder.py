from pathlib import Path
ROOT=Path('/mnt/data/Project_APEX_Engineering_Apprenticeship'); OUT=ROOT/'textbook'/'output'
PROJECTS=[
('One-Dimensional Car Integrator','Create an explicit state/action transition and a deterministic rollout.','Position and velocity arrays match an analytical constant-acceleration case.','Wrong time-step use and update order.','The simulation interface used by every later model.'),
('Telemetry Quality Laboratory','Define a typed telemetry contract and reject corrupt units, ranges, timestamps and axes.','Every injected defect fails at the intended boundary with a useful message.','Silent coercion and semantic swaps.','Canonical contract and ingestion quality gate.'),
('Lap Physics Sandbox','Add track progress, curvature demand, grip, tyre degradation and weather to a causal toy environment.','Changing each scenario variable produces a directionally justified trajectory change.','Impossible controls and discontinuous progress.','Offline data source and trusted evaluator for planner tests.'),
('Nonlinear Transition Model','Train an MLP to predict next state and compare with persistence and linear controls.','Model improves matched test transitions and residual plots explain the gain.','Target leakage and one-step-only conclusions.','First learned dynamics component.'),
('Track Segment Encoder','Represent cyclic progress and local geometry without discontinuity at start/finish.','Nearby physical positions have nearby representations across the wrap boundary.','Treating progress as an ordinary unbounded scalar.','Geometry/context representation for unseen-track transfer.'),
('GRU Telemetry Forecaster','Encode history and generate an autoregressive future under supplied controls.','Free-running horizon curves beat controls within a defined trusted range.','Hidden-state reuse and teacher forcing at test.','Primary deterministic APEX V1 model.'),
('Selective SSM Memory Laboratory','Build stable input-dependent retention and compare with GRU on long/rare dependencies.','Selection provides measurable memory or latency value under matched budget.','Exploding state and architecture-name overclaiming.','SSM challenger and Mamba preparation.'),
('RSSM Imagination Laboratory','Separate posterior evidence from prior imagination and train stochastic latent dynamics.','Prior rollouts are useful and uncertainty diagnostics are calibrated on a stochastic task.','Posterior leakage and KL collapse.','Dreamer-style belief model challenger.'),
('Latent MPC Planner','Use CEM to optimize bounded action sequences through a learned model.','Selected actions improve trusted-environment outcome without OOD exploitation.','Reward loopholes and variance collapse.','Planning layer after dynamics certification.'),
('Project APEX Production Engine','Integrate ingestion, contracts, windows, models, evaluation, pipeline, registry, API and UI.','A fresh run is reproducible, tested, traceable and usable through the interface.','Artifact mismatch, UI false precision and source coupling.','The capstone and base for F1 25/research expansion.'),
]
parts=['''---
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
''']
for i,(title,mission,accept,fail,transfer) in enumerate(PROJECTS,1):
    folder=f'{i:02d}_'+['car_integrator','telemetry_quality','lap_physics','mlp_transition','track_encoder','gru_forecaster','selective_ssm','rssm_imagination','latent_mpc','project_apex'][i-1]
    parts.append(f'''# Project {i}: {title}

## Mission

{mission}

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

{accept}

The criterion must be measurable. “It runs” is never sufficient. Save a report with configuration, seed, environment, output paths and limitations.

## Deliberate failure

{fail}

Before opening any debugging note, predict the symptom, the earliest failed contract and the misleading downstream symptom. Preserve the failing artifact so the repair can be proven.

## Implementation-choice review

Answer:

- What is the simplest implementation that can satisfy the acceptance test?
- What evidence would justify a more complex one?
- Which assumption is encoded in the data rather than the model?
- Which error is numerical, statistical, causal or operational?
- What result would cause you to abandon this design?

## Transfer into APEX

{transfer}

Locate the corresponding production module and explain what extra responsibilities appear there: configuration, batching, validation, checkpointing, artifacts, API compatibility, monitoring or UI provenance.

## Repository

```text
projects/{folder}/
```

Run the project, then rename or hide the solution and recreate its core from the README and tests. The second implementation is the real mastery check.

''')
path=OUT/'Project_APEX_Ten_Project_Instructor_Ladder.md'; path.write_text('\n'.join(parts)); print(path,len(path.read_text().split()))
