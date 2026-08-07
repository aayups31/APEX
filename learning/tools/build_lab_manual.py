from pathlib import Path
import subprocess, re
ROOT=Path('/mnt/data/Project_APEX_Engineering_Apprenticeship')
LAB=ROOT/'labs'; OUT=ROOT/'textbook'/'output'
META={
'01_units_and_shapes':('Units and tensor axes','A number without a unit and an array without axis names are both incomplete evidence.','Predict the converted speeds and the exact `[time, feature]` shape before running.','Transpose the array or skip km/h conversion. Add assertions for units, shape and feature order.','Add a typed telemetry batch carrying values, names, units and sample rate.','Canonical adapter and contract validation.'),
'02_vectorized_kinematics':('Differentiate and integrate a speed trace','Numerical derivatives magnify noise; numerical integration accumulates bias.','Predict whether reconstructing speed from a numerical gradient will be exact.','Change `dt` without changing time samples; compare errors and locate the contract mismatch.','Compare forward, central and smoothed derivatives.','Synthetic causal generator and physical sanity checks.'),
'03_force_model':('Longitudinal forces','Separating drive, brake and drag makes causal errors visible.','Calculate net force and acceleration for one chosen row by hand.','Feed km/h into a coefficient calibrated for m/s and add a property test.','Add grip-limited traction and show where more throttle stops helping.','Synthetic telemetry dynamics and residual modelling.'),
'04_sampling_aliasing':('Sampling and aliasing','The model cannot learn temporal information the sensor never captured.','Predict the apparent signal at 5, 12 and 40 Hz.','Choose a signal above Nyquist and show two different continuous signals sharing samples.','Build an anti-alias filter experiment.','Canonical frequency and F1 25 telemetry-rate decisions.'),
'05_regression_baseline':('Ridge transition baseline','A simple control tells you whether complexity earns its cost.','Predict coefficient signs for speed, throttle and brake.','Leak the target into features, observe near-perfect error, then prevent it with an allow-list.','Add polynomial speed features and inspect residuals.','Baseline-relative model evaluation.'),
'06_autograd_drag':('Learning a physical coefficient','Autograd is easiest to trust when the expected parameter is known.','Predict the sign of the drag-coefficient gradient from an under-estimate.','Omit `zero_grad` and increase learning rate until divergence.','Estimate two correlated force parameters and study identifiability.','Training-loop diagnostics and hybrid physics learning.'),
'07_pytorch_module':('A transition MLP','A module is a parameterized function with a precise shape contract.','Write input/output shapes for one batch before executing.','Swap batch and feature axes; block the bug with exact assertions.','Add a residual connection predicting state delta instead of absolute state.','Frame transition baseline and shape tracing.'),
'08_dataset_windows':('Causal history and target windows','Sequence slicing defines what the model is allowed to know.','List raw indices for the first and final example.','Put target state into future inputs and add a leakage test.','Add future controls as a separate tensor and session identifiers.','APEX WindowDataset and rollout contract.'),
'09_loss_comparison':('Loss functions under outliers','Loss determines which errors receive optimization pressure.','Rank MSE, MAE and Huber sensitivity to one extreme residual.','Scale one feature by 100 without normalization and observe domination.','Create a weighted multi-feature telemetry loss.','Model training versus operational metrics.'),
'10_training_loop':('Gradients and updates','Backward computes gradients; the optimizer changes parameters.','State what changes after each training-loop line.','Remove zeroing, omit eval mode and create broadcasting targets.','Write a JSON trace of gradients and update norms.','APEX training and checkpoint validation.'),
'11_rnn_from_scratch':('Recurrent state updates','A recurrent model is a transition over hidden memory.','Compute the first scalar hidden update by hand.','Reverse sequence order and reuse state across sequences.','Create a long-delay memory task.','Why APEX needs history encoding.'),
'12_gru_gates':('GRU memory gates','Gates learn how much old memory to retain or overwrite.','Predict whether repeating the same input yields identical hidden states.','Force update gates to saturation and inspect memory.','Compare GRU and matched RNN on delayed events.','Primary deterministic world model.'),
'13_linear_ssm':('Linear state-space memory','Eigenvalues determine decay, persistence, oscillation and explosion.','Predict the two hidden components after the first pulse.','Set spectral radius above one and create a stability test.','Design fast, medium and slow memory modes.','SSM challenger and hidden-norm monitoring.'),
'14_selective_ssm':('Input-dependent state-space memory','Selection lets current content alter retention and writing.','Predict how basis-vector order changes final memory.','Remove gate bounds and inspect explosion/frozen memory.','Log retention by braking/straight regimes.','Selective SSM challenger and Mamba preparation.'),
'15_autoencoder':('Latent compression','Reconstruction pressure does not guarantee predictive representations.','Predict latent and reconstruction shapes.','Add high-variance nuisance features and observe what latent preserves.','Add a future-state probe and predictive auxiliary loss.','Representation learning before RSSM/JEPA.'),
'16_vae_reparameterization':('Stochastic latent variables','Reparameterization separates noise from differentiable distribution parameters.','Compute standard deviations and KL by hand.','Set extreme log variance and inspect numerical behaviour.','Sample repeatedly and compare empirical moments.','RSSM posterior/prior distributions.'),
'17_rssm_step':('Prior and posterior belief','Training may use observation evidence; imagination may not.','Name the inputs to h, prior and posterior before running.','Leak observation into the prior and write a no-future-observation test.','Add sampling, KL and decoder loss for multiple steps.','Dreamer-style latent dynamics.'),
'18_cem_planning':('Cross-entropy planning','Planning repeatedly samples, imagines, keeps elites and refits.','Predict the direction of the first action mean.','Remove constraints and create a model loophole for the planner to exploit.','Add brake actions, uncertainty penalty and receding horizon.','Scenario planning and later control.'),
'19_time_alignment':('Causal asynchronous joins','Alignment policy determines whether future information leaks backward.','Manually match every car timestamp under backward tolerance.','Switch to nearest and add a future spike.','Persist source age and missingness masks.','FastF1/OpenF1 stream alignment.'),
'20_pipeline_contract':('Staged artifact workflow','Durable boundaries make retries, lineage and debugging possible.','Predict the exact output tree.','Overwrite one shared `latest` path and simulate failure halfway.','Add content hashes, atomic writes and resumable status.','Local runner, Airflow DAG and registry.'),
}

def run(p):
    r=subprocess.run(['python',str(p)],cwd=p.parent,text=True,capture_output=True,timeout=60)
    return (r.stdout+r.stderr).strip()

parts=['''---
title: "Project APEX Executable Lab Manual"
subtitle: "Twenty guided experiments from units to latent planning"
author: "OpenAI"
date: "August 2026"
toc: true
numbersections: true
---

# How to run a lab

For every lab, use the same discipline:

1. Read the goal and predict the output.
2. Copy the solution into a temporary file by hand or complete your own starter.
3. Run it once unchanged.
4. Explain every printed number and tensor axis.
5. Introduce the specified defect deliberately.
6. Find the earliest contract that fails.
7. Repair it and add a regression assertion.
8. Complete the extension without copying.
9. Record how the idea changes Project APEX.

The lab is complete only when you can alter it and still explain the result.
''']
for i,d in enumerate(sorted([p for p in LAB.iterdir() if p.is_dir()]),1):
    key=d.name; title,why,predict,brk,extend,apex=META[key]
    code=(d/'solution.py').read_text(); output=run(d/'solution.py')
    numbered='\n'.join(f'{n+1:>3}: {line}' for n,line in enumerate(code.splitlines()))
    parts.append(f'''# Lab {i}: {title}

## Why this lab exists

{why} The program is intentionally small enough that you can track every value. Do not add abstraction until the mechanism is obvious.

## Predict before running

{predict} Write the expected output, shapes, units and likely failure modes.

## Execute

```bash
cd labs/{key}
python solution.py
```

## Complete code with line numbers

```text
{numbered}
```

## Packaged reference output

```text
{output}
```

## Instructor trace

Read the program in this order:

1. Identify persistent state and trainable parameters, if any.
2. Identify the input evidence and its axes/units.
3. Identify the transformation performed by each statement.
4. Identify what is printed and what is hidden.
5. Recompute at least one printed value manually.
6. State which line would first reveal an invalid assumption.

Now add temporary prints after every meaningful assignment. For tensors, print `shape`, `dtype`, minimum, maximum and one row. For iterative systems, print state before and after the transition. For learned models, print loss, gradient and parameter values at least once.

## Break it deliberately

{brk}

Before fixing the defect, write:

- expected symptom;
- earliest failed contract;
- one misleading downstream symptom;
- one assertion that should catch it;
- why a model or optimizer change would not be the correct first response.

## Repair test

Turn your diagnosis into a small automated check. The repair should fail on the broken implementation and pass on the corrected one. Prefer a known numerical answer, invariant, exact shape/ordering check or deterministic causal relationship.

## Extension

{extend}

Do not copy from another lab. Write a short decision note comparing the original and extended implementation: what new capability was added, what complexity it introduced, and what evidence justifies keeping it.

## Where it enters APEX

{apex} Find the corresponding production file using the Code Atlas and compare the small mechanism with the production abstraction. Explain what production concerns were added: configuration, batching, validation, artifacts, logging, tests or serving.

## Exit questions

1. What assumption did this lab make deliberately simple?
2. What output would immediately make you distrust the result?
3. Which test protects the idea rather than this exact code?
4. When would you choose a different implementation?

''')
md='\n'.join(parts)
path=OUT/'Project_APEX_Executable_Lab_Manual.md'; path.write_text(md)
print(path, len(md.split()))
