# 19. Production Pipelines, Airflow, Registry and Monitoring

> **Instructor objective:** Refactor experimental code into idempotent stages with observable lineage, then understand when orchestration becomes necessary.

![19. Production Pipelines, Airflow, Registry and Monitoring](../figures/19_pipeline.png)

## The problem that earns this chapter

A notebook can ingest, train and plot once. A production system must retry failed downloads, validate versions, reproduce models, backfill sessions, avoid overwriting artifacts, and tell operators which stage failed. Orchestration should coordinate trustworthy functions, not rescue tangled code.

### Predict before reading

A pipeline fails after training but before publication. On retry, should it retrain from scratch, reuse the checkpoint, or overwrite the run directory? What information is needed to choose safely?

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

A stage has explicit inputs, outputs, configuration, failure modes and idempotency policy. Ingestion writes canonical data; validation writes a report; training writes a checkpoint; evaluation writes metrics; publication writes UI/API products. Each artifact is immutable within a run and linked by identifiers/hashes.

Airflow schedules and tracks task dependencies, retries and backfills. Business logic should remain in ordinary tested Python functions so the same stage runs locally, in tests and under orchestration. Passing large arrays through orchestration metadata is a smell; pass durable artifact references.

A registry records runs, configurations, dataset versions, metrics and status. Monitoring then covers pipeline health, data drift, model behaviour and product delivery. Logging without stable run IDs and structured fields is not lineage.

## Vocabulary that now has a job

**Concept: Idempotency**
- **Meaning in plain language:** Repeating a stage with the same inputs yields the same result or safely reuses it.
- **Role inside APEX:** Enables retries and backfills.

**Concept: Artifact lineage**
- **Meaning in plain language:** Trace which data, code and configuration produced an output.
- **Role inside APEX:** Every UI prediction links to model run and dataset.

**Concept: Orchestrator**
- **Meaning in plain language:** Coordinates when stages run and how failures/retries are managed.
- **Role inside APEX:** Airflow DAG wraps tested stage functions.

**Concept: Registry**
- **Meaning in plain language:** Queryable record of runs, statuses, metrics and artifact locations.
- **Role inside APEX:** SQLite V1, expandable to a service/database.


## Worked example: calculate it by hand

Assume training checkpoint hash `abc123` exists and evaluation failed because disk was temporarily full.

A safe retry checks:

1. Same run ID and immutable configuration hash.
2. Same dataset/normalizer hashes.
3. Checkpoint exists, is complete and matches metadata.
4. Training stage status is succeeded.
5. Evaluation output is absent or marked failed.

Then retry evaluation only. If configuration changed, create a new run rather than silently reusing the checkpoint. If checkpoint integrity is uncertain, retrain in a new or repaired stage path.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/20_pipeline_contract`

### What we are about to build

Use the miniature stage artifact writer to learn explicit stage boundaries, then trace the production APEX runner and Airflow DAG that call the same business functions.

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

**Code: run.mkdir(parents=True,exist_ok=True)**
- **What the line is doing:** Create a stable run namespace for artifacts.
- **What to inspect:** A production run directory should not mix different configuration hashes.

**Code: path.write_text(json.dumps(...))**
- **What the line is doing:** Persist machine-readable stage evidence.
- **What to inspect:** Use atomic temporary-file replacement for critical artifacts.

**Code: stages=[...]**
- **What the line is doing:** Make dependencies visible and independently testable.
- **What to inspect:** Do not create one giant “do everything” task.


### State and tensor trace

```text
CLI / Airflow / test
        ↓
ordinary Python stage function
        ↓
durable artifact + metadata
        ↓
registry status transition
        ↓
next stage receives artifact path
```

A retry should start from the last valid durable boundary.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Write every run to `latest/`, pass a large tensor through Airflow XCom, and combine ingestion/training/publication in one task. Simulate a publication failure.

### Diagnose from the earliest failed contract

Look for overwritten evidence, ambiguous status and work that must repeat unnecessarily. The earliest failed design is usually the artifact/stage contract, not the scheduler.

### Repair and lock the repair with a test

Use immutable run IDs, atomic writes, explicit stage manifests and small task messages containing paths/IDs. Add pipeline tests that run twice and assert safe reuse or deterministic replacement.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Local Python runner**
- **Choose it when:** Development, CI and small reproducible workflows.
- **Do not choose it when:** Complex schedules, backfills and multi-worker operations.

**Implementation: Airflow**
- **Choose it when:** Batch dependencies, retries, schedules and historical backfills matter.
- **Do not choose it when:** You need low-latency event streaming or have only one trivial script.

**Implementation: Experiment tracker**
- **Choose it when:** Comparing many model runs and artifacts.
- **Do not choose it when:** You assume it replaces data/version contracts and orchestration.

**Implementation: Model registry**
- **Choose it when:** Promotion, rollback and serving require a governed model identity.
- **Do not choose it when:** A notebook checkpoint with no deployment lifecycle.


APEX implements a local runner as the source of truth, a thin Airflow DAG, a run registry and immutable run artifacts. The full Airflow service is an optional deployment layer, not required for learning core models.

## Transfer the lesson into Project APEX

Run the same configuration twice under different IDs. Compare manifests, then deliberately fail publication and resume from the last successful stage. Inspect API/UI links back to the run directory.

### Repository path to inspect

```text
apex_engine/src/apexsim/pipeline/stages.py
apex_engine/src/apexsim/pipeline/runner.py
apex_engine/src/apexsim/registry.py
apex_engine/dags/apexsim_dag.py
debugging_cases/13_artifact_overwrite
debugging_cases/14_airflow_payload
```

## Connection to research

Reproducible world-model research depends on production habits: immutable datasets, exact split policies, seeds, configuration, checkpoints and evaluation code. Without them, architecture comparisons are anecdotes.

## Check your understanding before continuing

1. Why should Airflow tasks pass paths instead of arrays?
2. What makes a stage idempotent?
3. What four layers should monitoring cover?

## Solutions and reasoning

**1.** Durable storage survives retries/workers, avoids metadata-size limits and preserves lineage.
**2.** Same logical inputs/config produce the same content or a safely detected reusable artifact without duplicating side effects.
**3.** Pipeline execution, input data/contract, model behaviour/drift and delivered product/API/UI health.

## Independent build challenge

Create a two-run backfill that ingests two sessions, trains one model per session and publishes reports. Kill the process mid-run, restart it, and prove no successful work is corrupted or needlessly repeated.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
