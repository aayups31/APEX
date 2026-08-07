---
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

# Case 1: Unit mismatch

## Incident report

**Primary symptom:** Speed is converted twice and rollout acceleration is wrong.

**Secondary evidence:** A speed distribution has a plausible shape but is centred near 7 m/s instead of 90 m/s; drag and progress become inconsistent.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Print one raw value, source unit, canonical value and expected hand conversion at the adapter boundary.

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

Conversion is performed both by the source adapter and a downstream feature transform.

## Correct repair

Choose one canonical unit, convert once in the adapter, store unit metadata, and delete downstream implicit conversion.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

A fixture containing 360 km/h must become exactly 100 m/s and remain 100 m/s through window construction.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

Changing model coefficients or clipping speed masks the defect and corrupts every downstream interpretation.

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


# Case 2: Axis swap

## Incident report

**Primary symptom:** A `[batch,time,feature]` tensor is passed as `[time,batch,feature]`.

**Secondary evidence:** Training runs because dimensions are numerically compatible, but hidden state mixes examples and sequence length changes with batch size.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Use unequal dimensions such as batch=3, time=7, features=5; print named shape at model entry.

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

The dataset/collate output and model configuration disagree about `batch_first`.

## Correct repair

Standardize one axis convention, assert it at the boundary, and transpose only in one named adapter when required.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

A batch processed together must match each example processed separately with zero initial state.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

Increasing hidden size or training longer cannot repair wrong semantic axes.

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


# Case 3: Target leakage

## Incident report

**Primary symptom:** Future speed accidentally appears in model inputs.

**Secondary evidence:** Validation error collapses unrealistically and remains strong even when controls are shuffled.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Print feature names and source frame indices for one window; train a linear model and inspect suspicious coefficient on future speed.

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

Window feature allow-list includes a target column at the same or later timestamp.

## Correct repair

Separate state, future-control and target schemas; construct tensors from explicit allow-lists.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

Assert no target feature/timestamp appears in history or future-input tensors and run a shuffled-target sanity test.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

Celebrating the score or adding regularization preserves the invalid experiment.

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


# Case 4: Random window split

## Incident report

**Primary symptom:** Overlapping windows from one session enter every split.

**Secondary evidence:** Test performance is extremely stable and much better than unseen-session performance.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Report unique session IDs and raw frame IDs in each split; calculate overlap and nearest temporal distance.

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

Windows are generated first and then randomly assigned.

## Correct repair

Assign sessions/events before windowing; persist deterministic split mapping.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

No session ID or raw frame identifier may appear in more than one split.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

Reducing window overlap does not solve the generalization-claim mismatch.

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


# Case 5: Stale as-of join

## Incident report

**Primary symptom:** Weather is forward-filled across a long outage.

**Secondary evidence:** Rain appears constant for minutes despite missing source records, and the model becomes overconfident.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Store matched source timestamp and compute age for every joined row; plot age distribution.

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

Forward fill or backward join has no tolerance and missingness is erased.

## Correct repair

Use causal join with domain tolerance, carry age/missing masks, quarantine long gaps.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

Every matched context timestamp must be ≤ frame time and age ≤ configured tolerance.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

Blind interpolation creates fabricated certainty rather than recovering evidence.

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


# Case 6: Normalizer leak

## Incident report

**Primary symptom:** Standardization is fitted on all data.

**Secondary evidence:** Held-out features have suspiciously centred distributions and deployment transformation cannot be recreated from training artifacts.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Recompute normalizer hash from training rows only and compare; inspect fitted row identifiers.

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

Preprocessing is applied before split or fit is called on concatenated partitions.

## Correct repair

Split first, fit on train, serialize statistics, transform validation/test without refit.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

Changing validation/test values must not change stored normalizer statistics.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

The score inflation may be small, but the protocol and reproducibility are invalid.

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


# Case 7: Hidden-state reuse

## Incident report

**Primary symptom:** Hidden state leaks between unrelated sessions.

**Secondary evidence:** Predictions depend on dataloader order and the first frames of a session contain information from a previous driver.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Run the same sessions in reversed batch order and compare outputs; print hidden norm at boundaries.

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

Stateful recurrence is used without entity/session reset policy.

## Correct repair

Zero/reset hidden state at independent boundaries; make streaming state keyed and explicit.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

Separate processing and batched processing with zero state must agree.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

Randomizing order can hide the symptom without defining correct state lifetime.

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


# Case 8: Missing eval mode

## Incident report

**Primary symptom:** Dropout remains active during evaluation.

**Secondary evidence:** Repeated inference for identical input produces different predictions and reported metrics vary.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Call the model twice with fixed input/seed; inspect `model.training`.

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

Evaluation uses `no_grad` but never calls `model.eval()`.

## Correct repair

Switch to eval before validation/inference and restore train mode when resuming optimization.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

Two deterministic eval calls must match for deterministic models; validation helper must assert mode.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

Averaging many stochastic passes is not a repair unless MC dropout is an intentional uncertainty method.

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


# Case 9: Gradient accumulation

## Incident report

**Primary symptom:** Gradients are never cleared.

**Secondary evidence:** Update magnitude grows across batches, loss oscillates and gradient norms depend on batch position.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Print one parameter gradient before backward each iteration.

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

`zero_grad` is omitted while optimizer steps every batch.

## Correct repair

Clear gradients at the intended accumulation boundary and document accumulation factor.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

Two identical independent batches should produce identical gradients when starting from same parameters.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

Lowering learning rate may reduce symptoms but leaves unintended history in every update.

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


# Case 10: Exploding SSM

## Incident report

**Primary symptom:** Unconstrained recurrent decay exceeds one.

**Secondary evidence:** Hidden norm grows exponentially during zero-input rollout, then outputs become inf/NaN.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Plot hidden norm over 200 zero-input steps and inspect transition eigenvalues/gates.

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

State propagation permits amplification greater than one without stabilizing design.

## Correct repair

Use stable parameterization/bounds, initialization and horizon stress tests; clip only as secondary protection.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

Bounded input must produce finite bounded hidden state over the certified horizon.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

Output clipping conceals unstable internal memory and gradients.

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


# Case 11: KL collapse

## Incident report

**Primary symptom:** RSSM posterior ignores stochastic state.

**Secondary evidence:** KL is nearly zero, posterior and prior are identical, and decoder predictions barely change when latent is resampled.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Report KL per latent dimension, latent variance and decoder sensitivity to z.

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

KL pressure/decoder capacity lets deterministic path solve loss while stochastic latent carries no information.

## Correct repair

Tune balance with warm-up/free-nats/capacity changes after diagnostics; force evaluation of prior and latent probes.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

Changing z while holding h fixed should alter decoded predictions on a task designed to require uncertainty.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

Simply increasing stochastic dimension adds unused variables and can worsen optimization.

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


# Case 12: Planner exploitation

## Incident report

**Primary symptom:** CEM finds actions outside training support.

**Secondary evidence:** Imagined reward is excellent but actions saturate at boundaries and fail in trusted simulator/replay.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Measure action-distribution distance, uncertainty and violations for elite candidates.

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

Reward/model lacks constraints and planner searches OOD regions where dynamics are inaccurate.

## Correct repair

Enforce bounds, OOD/uncertainty penalties, trusted-model validation and receding-horizon replanning.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

A hidden loophole fixture must be rejected or penalized despite high predicted reward.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

Reducing CEM iterations may hide exploitation but does not repair model/reward validity.

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


# Case 13: Artifact overwrite

## Incident report

**Primary symptom:** Two runs write the same model path.

**Secondary evidence:** Metrics refer to one config while checkpoint silently belongs to another; rollback is impossible.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Compare checkpoint hash, config hash and timestamps in registry/run directory.

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

Mutable `latest/model.pt` is used as both identity and storage.

## Correct repair

Use immutable run IDs/content hashes; make `latest` a pointer, not the sole artifact.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

Concurrent runs must produce distinct immutable paths and provenance must resolve exactly.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

Adding timestamps to filenames without registry metadata still weakens lineage.

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


# Case 14: Airflow payload

## Incident report

**Primary symptom:** Large arrays are passed through XCom.

**Secondary evidence:** Scheduler metadata grows, serialization fails and workers spend time moving data through the control plane.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Inspect XCom sizes and task logs; trace where durable files already exist.

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

Task interfaces return in-memory arrays instead of artifact references.

## Correct repair

Persist arrays in object/file storage and pass small path/ID/hash messages.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

Task output metadata must remain below a chosen size and downstream task must reload/validate artifact.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

Raising database limits turns an architectural problem into a larger operational problem.

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


# Case 15: UI false precision

## Incident report

**Primary symptom:** The UI reports more precision than the model supports.

**Secondary evidence:** A scenario displays speed to 0.001 km/h beyond the measured error and shows untrusted horizons as equally certain.

Assume the symptom was first noticed in a model or UI output. Your task is to resist debugging at the last visible layer.

## Pause and predict

Write the invariant that should hold. List three plausible causes from different layers. Rank them by how early they occur in the data-to-product flow. Choose one probe that can eliminate the largest number of hypotheses.

## High-information first probe

Compare displayed digits/horizon with calibration and held-out metrics; reproduce one point outside UI.

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

Presentation is designed independently of model uncertainty, provenance and trusted range.

## Correct repair

Round to meaningful resolution, label trusted horizon, show run/model identity and exploratory regions.

A repair should reduce ambiguity. It should not merely make the current metric look normal.

## Regression test

Snapshot/UI test verifies provenance, units, rounding and horizon labels for a known run.

Write the test before deleting the broken version. Prove that it fails on the defect and passes after repair. Then decide whether the same invariant belongs in runtime validation or monitoring.

## The tempting wrong repair

A beautiful chart can increase harm when it makes uncertain outputs look authoritative.

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

