# 20. Build Project APEX V1 End to End—and Then Outgrow It

> **Instructor objective:** Assemble the complete system, run a verified world-model simulation, use the UI responsibly, and define the research path toward F1 25 and an original architecture.

![20. Build Project APEX V1 End to End—and Then Outgrow It](../figures/20_apex.png)

## The problem that earns this chapter

The final challenge is integration. Correct individual pieces can still form a wrong system: adapters may disagree with windows, normalizers may differ between training and UI, scenario controls may overwrite state, or a beautiful interface may present false precision. We now build one traceable path from evidence to an imagined future.

### Predict before reading

Before running anything, list the artifacts that must exist for a UI scenario to be reproducible: data, split, normalizer, model, evaluation, scenario inputs and software identity. Which of these should the UI be allowed to modify?

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

APEX V1 is a historical telemetry world-simulation engine. It does not claim complete car physics or autonomous strategy. It answers a narrower, testable question: given recent canonical telemetry and an explicit sequence of future controls/context, can a learned transition model generate plausible short-horizon future state?

The system begins with synthetic data so every causal rule is inspectable and offline tests always run. It accepts FastF1/OpenF1 canonical data when available. A deterministic GRU is primary; an SSM-style model and RSSM are challengers. Evaluation determines the trusted horizon. The scenario engine modifies only designated future controls/context. The UI displays recorded and imagined trajectories with model/run identity and limitations.

The next stages are research, not feature accumulation: improve state observability, calibrate uncertainty, add track/generalization splits, ingest F1 25 UDP, learn richer latent dynamics, and validate planning. An original architecture should be proposed only after a measured failure cannot be fixed by data, objective or simpler model choices.

## Vocabulary that now has a job

**Concept: Scenario contract**
- **Meaning in plain language:** Exactly which future controls/context may be changed and how.
- **Role inside APEX:** Throttle, brake, rain/grip and tyre assumptions under bounded transformations.

**Concept: Trusted horizon**
- **Meaning in plain language:** Maximum forecast duration meeting error and guardrail criteria.
- **Role inside APEX:** Displayed with every scenario rather than claiming unlimited simulation.

**Concept: Product provenance**
- **Meaning in plain language:** User-visible link from prediction to run/model/data/config.
- **Role inside APEX:** Prevents anonymous, irreproducible UI output.

**Concept: Research hypothesis**
- **Meaning in plain language:** A falsifiable explanation for a measured failure and proposed change.
- **Role inside APEX:** The basis for new world-model architecture work.


## Worked example: calculate it by hand

A UI scenario uses history length 32 at 5 Hz (6.4 seconds) and predicts 8 frames (1.6 seconds). Suppose speed MAE by horizon is `[1.0,1.3,1.8,2.5,3.4,4.6,6.2,8.5] km/h`, with a guardrail of MAE ≤5 km/h and zero physical violations. The trusted horizon is step 6, or 1.2 seconds, even though the model emits 1.6 seconds.

This is not failure. The system should shade or label steps 7–8 as exploratory, refuse high-stakes conclusions, and direct research toward the compounding error observed after step 6.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/20_pipeline_contract`

### What we are about to build

Run the production APEX fast configuration, inspect every artifact, launch the UI, modify one scenario control, and trace the resulting prediction back through normalizer, model and run metadata.

### Runnable implementation

```python
from pathlib import Path
import json

run=Path('artifacts/education_pipeline'); run.mkdir(parents=True,exist_ok=True)
stages=['ingest','validate','window','train','evaluate','publish']
for i,name in enumerate(stages):
    path=run/f'{i:02d}_{name}.json'; path.write_text(json.dumps({'stage':name,'status':'succeeded'}))
    print(path)

```

### Observed output from the packaged solution

```text
artifacts/education_pipeline/00_ingest.json
artifacts/education_pipeline/01_validate.json
artifacts/education_pipeline/02_window.json
artifacts/education_pipeline/03_train.json
artifacts/education_pipeline/04_evaluate.json
artifacts/education_pipeline/05_publish.json
```

### Read the important lines like English

**Code: apexsim run --config configs/fast.yaml --run-id ...**
- **What the line is doing:** Execute the complete source-independent pipeline.
- **What to inspect:** Use a new immutable run ID and inspect stage logs.

**Code: apexsim ui --run-dir ...**
- **What the line is doing:** Launch the race-engineering interface from verified artifacts.
- **What to inspect:** The UI must load the same normalizer/model/config used in evaluation.

**Code: apexsim run-canonical --input-path ...**
- **What the line is doing:** Feed adapter-produced canonical data through the identical pipeline.
- **What to inspect:** Validate source and split semantics before comparing runs.


### State and tensor trace

```text
FastF1 / OpenF1 / synthetic / future UDP
           ↓ canonical contract + quality report
session split → windows → train-only normalizer
           ↓
GRU / SSM / RSSM checkpoint
           ↓ matched evaluation + trusted horizon
scenario controls → autoregressive rollout
           ↓
artifact bundle → registry → API/UI
```

For one UI point, record: source frame indices, normalized input, scenario transform, model output, inverse transform, plotted value and run ID.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Load a checkpoint with the wrong normalizer, let the UI modify future target speed directly, hide the model identity, or display more decimal precision than validation supports.

### Diagnose from the earliest failed contract

Reproduce the scenario outside the UI using the same artifact paths. Compare canonical input, normalized tensor and raw model output. If CLI and UI differ, the serving boundary is broken; if both fail, move earlier.

### Repair and lock the repair with a test

Bundle model, normalizer, feature order and config; validate hashes on load. Make scenario fields allow-listed. Display uncertainty/trusted horizon and provenance. Add end-to-end tests comparing UI callback output with direct simulation.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Gradio UI**
- **Choose it when:** Rapid educational interactive scenarios with Python integration.
- **Do not choose it when:** You require a highly customized production frontend at scale.

**Implementation: FastAPI + web frontend**
- **Choose it when:** Stable service contracts, multiple clients and custom UX.
- **Do not choose it when:** The API/model contract is still changing daily.

**Implementation: Synthetic-first**
- **Choose it when:** Offline causality, testing and controlled failure injection.
- **Do not choose it when:** You confuse synthetic accuracy with real F1 fidelity.

**Implementation: F1 25 UDP migration**
- **Choose it when:** Game packets are available and canonical mapping/latency tests are ready.
- **Do not choose it when:** You let packet-specific fields leak through the entire core architecture.


The delivered V1 is a complete learning and research platform, not the final Dreamer-for-F1 system. Its value is that every future architecture competes inside a tested data, rollout, evaluation and product framework.

## Transfer the lesson into Project APEX

Follow `START_HERE.md`, run tests, execute a fast reference, launch the UI, complete Projects 1–9, then rebuild one core module without reading the solution. Use the source companion only after your own attempt.

### Repository path to inspect

```text
apex_engine/START_HERE.md
apex_engine/src/apexsim/
apex_engine/notebooks/
apex_engine/tests/
projects/10_project_apex/
source_code_companion/
```

## Connection to research

The path toward a Dreamer-like F1 system is staged: validated dynamics → probabilistic belief/calibration → reward/continuation model → planning under constraints → actor/critic imagination → F1 25 online data → cross-domain fine-tuning. Each arrow needs evidence.

## Check your understanding before continuing

1. Why must the UI use the training normalizer?
2. What should determine the displayed simulation horizon?
3. When is a new architecture justified?

## Solutions and reasoning

**1.** The model learned parameters in that transformed feature space; a different transform changes the meaning of every input/output.
**2.** Matched held-out horizon error, physical guardrails, uncertainty and operational tolerance—not the configured output length.
**3.** When a specific measured failure survives data/contract fixes, objective improvements and simpler baselines, and the proposed mechanism directly targets that failure.

## Independent build challenge

Rebuild APEX from an empty repository using only the canonical contract, acceptance tests and architecture diagram. Then propose one original model change with a falsifiable hypothesis, matched ablation and rollback condition.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
