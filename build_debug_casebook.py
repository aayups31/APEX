from pathlib import Path
ROOT=Path('/mnt/data/Project_APEX_Engineering_Apprenticeship')
OUT=ROOT/'textbook'/'output'
CASES=[
('Unit mismatch','Speed is converted twice and rollout acceleration is wrong.','A speed distribution has a plausible shape but is centred near 7 m/s instead of 90 m/s; drag and progress become inconsistent.','Print one raw value, source unit, canonical value and expected hand conversion at the adapter boundary.','Conversion is performed both by the source adapter and a downstream feature transform.','Choose one canonical unit, convert once in the adapter, store unit metadata, and delete downstream implicit conversion.','A fixture containing 360 km/h must become exactly 100 m/s and remain 100 m/s through window construction.','Changing model coefficients or clipping speed masks the defect and corrupts every downstream interpretation.'),
('Axis swap','A `[batch,time,feature]` tensor is passed as `[time,batch,feature]`.','Training runs because dimensions are numerically compatible, but hidden state mixes examples and sequence length changes with batch size.','Use unequal dimensions such as batch=3, time=7, features=5; print named shape at model entry.','The dataset/collate output and model configuration disagree about `batch_first`.','Standardize one axis convention, assert it at the boundary, and transpose only in one named adapter when required.','A batch processed together must match each example processed separately with zero initial state.','Increasing hidden size or training longer cannot repair wrong semantic axes.'),
('Target leakage','Future speed accidentally appears in model inputs.','Validation error collapses unrealistically and remains strong even when controls are shuffled.','Print feature names and source frame indices for one window; train a linear model and inspect suspicious coefficient on future speed.','Window feature allow-list includes a target column at the same or later timestamp.','Separate state, future-control and target schemas; construct tensors from explicit allow-lists.','Assert no target feature/timestamp appears in history or future-input tensors and run a shuffled-target sanity test.','Celebrating the score or adding regularization preserves the invalid experiment.'),
('Random window split','Overlapping windows from one session enter every split.','Test performance is extremely stable and much better than unseen-session performance.','Report unique session IDs and raw frame IDs in each split; calculate overlap and nearest temporal distance.','Windows are generated first and then randomly assigned.','Assign sessions/events before windowing; persist deterministic split mapping.','No session ID or raw frame identifier may appear in more than one split.','Reducing window overlap does not solve the generalization-claim mismatch.'),
('Stale as-of join','Weather is forward-filled across a long outage.','Rain appears constant for minutes despite missing source records, and the model becomes overconfident.','Store matched source timestamp and compute age for every joined row; plot age distribution.','Forward fill or backward join has no tolerance and missingness is erased.','Use causal join with domain tolerance, carry age/missing masks, quarantine long gaps.','Every matched context timestamp must be ≤ frame time and age ≤ configured tolerance.','Blind interpolation creates fabricated certainty rather than recovering evidence.'),
('Normalizer leak','Standardization is fitted on all data.','Held-out features have suspiciously centred distributions and deployment transformation cannot be recreated from training artifacts.','Recompute normalizer hash from training rows only and compare; inspect fitted row identifiers.','Preprocessing is applied before split or fit is called on concatenated partitions.','Split first, fit on train, serialize statistics, transform validation/test without refit.','Changing validation/test values must not change stored normalizer statistics.','The score inflation may be small, but the protocol and reproducibility are invalid.'),
('Hidden-state reuse','Hidden state leaks between unrelated sessions.','Predictions depend on dataloader order and the first frames of a session contain information from a previous driver.','Run the same sessions in reversed batch order and compare outputs; print hidden norm at boundaries.','Stateful recurrence is used without entity/session reset policy.','Zero/reset hidden state at independent boundaries; make streaming state keyed and explicit.','Separate processing and batched processing with zero state must agree.','Randomizing order can hide the symptom without defining correct state lifetime.'),
('Missing eval mode','Dropout remains active during evaluation.','Repeated inference for identical input produces different predictions and reported metrics vary.','Call the model twice with fixed input/seed; inspect `model.training`.','Evaluation uses `no_grad` but never calls `model.eval()`.','Switch to eval before validation/inference and restore train mode when resuming optimization.','Two deterministic eval calls must match for deterministic models; validation helper must assert mode.','Averaging many stochastic passes is not a repair unless MC dropout is an intentional uncertainty method.'),
('Gradient accumulation','Gradients are never cleared.','Update magnitude grows across batches, loss oscillates and gradient norms depend on batch position.','Print one parameter gradient before backward each iteration.','`zero_grad` is omitted while optimizer steps every batch.','Clear gradients at the intended accumulation boundary and document accumulation factor.','Two identical independent batches should produce identical gradients when starting from same parameters.','Lowering learning rate may reduce symptoms but leaves unintended history in every update.'),
('Exploding SSM','Unconstrained recurrent decay exceeds one.','Hidden norm grows exponentially during zero-input rollout, then outputs become inf/NaN.','Plot hidden norm over 200 zero-input steps and inspect transition eigenvalues/gates.','State propagation permits amplification greater than one without stabilizing design.','Use stable parameterization/bounds, initialization and horizon stress tests; clip only as secondary protection.','Bounded input must produce finite bounded hidden state over the certified horizon.','Output clipping conceals unstable internal memory and gradients.'),
('KL collapse','RSSM posterior ignores stochastic state.','KL is nearly zero, posterior and prior are identical, and decoder predictions barely change when latent is resampled.','Report KL per latent dimension, latent variance and decoder sensitivity to z.','KL pressure/decoder capacity lets deterministic path solve loss while stochastic latent carries no information.','Tune balance with warm-up/free-nats/capacity changes after diagnostics; force evaluation of prior and latent probes.','Changing z while holding h fixed should alter decoded predictions on a task designed to require uncertainty.','Simply increasing stochastic dimension adds unused variables and can worsen optimization.'),
('Planner exploitation','CEM finds actions outside training support.','Imagined reward is excellent but actions saturate at boundaries and fail in trusted simulator/replay.','Measure action-distribution distance, uncertainty and violations for elite candidates.','Reward/model lacks constraints and planner searches OOD regions where dynamics are inaccurate.','Enforce bounds, OOD/uncertainty penalties, trusted-model validation and receding-horizon replanning.','A hidden loophole fixture must be rejected or penalized despite high predicted reward.','Reducing CEM iterations may hide exploitation but does not repair model/reward validity.'),
('Artifact overwrite','Two runs write the same model path.','Metrics refer to one config while checkpoint silently belongs to another; rollback is impossible.','Compare checkpoint hash, config hash and timestamps in registry/run directory.','Mutable `latest/model.pt` is used as both identity and storage.','Use immutable run IDs/content hashes; make `latest` a pointer, not the sole artifact.','Concurrent runs must produce distinct immutable paths and provenance must resolve exactly.','Adding timestamps to filenames without registry metadata still weakens lineage.'),
('Airflow payload','Large arrays are passed through XCom.','Scheduler metadata grows, serialization fails and workers spend time moving data through the control plane.','Inspect XCom sizes and task logs; trace where durable files already exist.','Task interfaces return in-memory arrays instead of artifact references.','Persist arrays in object/file storage and pass small path/ID/hash messages.','Task output metadata must remain below a chosen size and downstream task must reload/validate artifact.','Raising database limits turns an architectural problem into a larger operational problem.'),
('UI false precision','The UI reports more precision than the model supports.','A scenario displays speed to 0.001 km/h beyond the measured error and shows untrusted horizons as equally certain.','Compare displayed digits/horizon with calibration and held-out metrics; reproduce one point outside UI.','Presentation is designed independently of model uncertainty, provenance and trusted range.','Round to meaningful resolution, label trusted horizon, show run/model identity and exploratory regions.','Snapshot/UI test verifies provenance, units, rounding and horizon labels for a known run.','A beautiful chart can increase harm when it makes uncertain outputs look authoritative.'),
]
parts=['''---
title: "Project APEX Production Debugging Casebook"
subtitle: "Fifteen failures investigated from symptom to regression test"
author: "OpenAI"
date: "August 2026"
toc: true
numbersections: true
---

# Debugging protocol

Do not begin by changing the model. Reproduce the failure, state the violated invariant, and find the earliest boundary where observed evidence diverges from expected evidence.

For every case, complete this investigation before reading the diagnosis:

1. Exact symptom and smallest reproducer.
2. Expected invariant.
3. First probe and why it is high-information.
4. Earliest failed contract.
5. Root cause.
6. Minimal repair.
7. Regression test.
8. Misleading repair that must be rejected.
9. Monitoring signal that would catch recurrence.

The casebook intentionally spans data, tensors, optimization, latent dynamics, planning, pipelines and UI. A production world model is only as strong as its weakest boundary.
''']
for i,(name,symptom,secondary,probe,root,repair,test,wrong) in enumerate(CASES,1):
    parts.append(f'''# Case {i}: {name}

## Incident report

**Primary symptom:** {symptom}

**Secondary evidence:** {secondary}

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

{probe}

This probe is valuable because it inspects the contract closest to the suspected transformation. A good probe is small, deterministic and interpretable; a full retraining run is a poor first probe.

## Investigation ladder

1. Reproduce with the smallest data/model configuration.
2. Freeze randomness and preserve the failing artifact.
3. Inspect identifiers, timestamps, units, shapes and feature names.
4. Compare one value by hand with expected transformation.
5. Move one boundary earlier until evidence becomes correct.
6. The defect lies between the last correct and first incorrect boundary.
7. Repair the cause and rerun the minimal reproducer.
8. Run the full relevant test set and compare unaffected behaviour.

## Root cause

{root}

## Correct repair

{repair}

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

{test}

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

{wrong}

This matters because production incidents are often prolonged by symptom-level fixes that make evidence less visible.

## APEX tracing exercise

Locate the corresponding path in the production repository. Draw the call path from CLI/UI input to the failed value. Mark every place that can transform it. Add one structured log or artifact field at the earliest useful boundary.

## Operational prevention

Define:

- a precondition checked before the stage;
- a postcondition checked after the stage;
- a metric or alert for recurrence;
- provenance needed for forensic replay;
- a rollback or quarantine action.

## Interview-level explanation

Explain the incident in four sentences: impact, root cause, repair, and prevention. Then explain why the most obvious model-level change would have been wrong.

''')
path=OUT/'Project_APEX_Production_Debugging_Casebook.md'; path.write_text('\n'.join(parts)); print(path,len(path.read_text().split()))
