# 5. Canonical Contracts and Quality Gates

> **Instructor objective:** Build one source-independent telemetry contract and make invalid evidence fail before it reaches a model.

![5. Canonical Contracts and Quality Gates](../figures/05_contract.png)

## The problem that earns this chapter

FastF1, OpenF1, synthetic data and future F1 25 UDP packets do not share identical names, units, timing or missingness. If every model contains source-specific branches, the system becomes impossible to test. We need a narrow boundary that all sources must cross.

### Predict before reading

Imagine FastF1 supplies speed in km/h and a future UDP adapter supplies m/s. Both columns are called `speed`. Where should conversion happen: inside each model, inside the dataset, or inside the source adapter? Explain the consequences of each choice.

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

A canonical contract is not merely a dataframe schema. It specifies names, types, units, legal ranges, timing semantics, missingness, identifiers and invariants. Source adapters are translators: they may parse and convert, but they should not secretly perform model-specific feature engineering.

A quality gate separates admissible evidence from rejected or quarantined evidence. Some checks are hard errors—missing timestamp, impossible unit, duplicate key. Others are warnings—unusual prevalence or a short gap. The distinction should reflect whether downstream interpretation remains valid.

Contracts also enable replaceability. You can test the entire pipeline with synthetic data, then swap to FastF1 without changing the window builder or model. This is the central architectural move that lets APEX start before F1 25 is available.

## Vocabulary that now has a job

**Concept: Canonical contract**
- **Meaning in plain language:** One stable internal representation accepted by all downstream components.
- **Role inside APEX:** The source-independent telemetry frame.

**Concept: Adapter**
- **Meaning in plain language:** A boundary component translating one external source into the canonical representation.
- **Role inside APEX:** FastF1, OpenF1 and future UDP adapters.

**Concept: Quality gate**
- **Meaning in plain language:** Executable rules deciding whether evidence may proceed.
- **Role inside APEX:** Range, timing, duplicate, finite-value and schema checks.

**Concept: Quarantine**
- **Meaning in plain language:** Preserve questionable data separately instead of silently dropping or using it.
- **Role inside APEX:** Allows investigation and reprocessing after a fix.


## Worked example: calculate it by hand

Suppose the canonical speed unit is m/s and the legal range is 0–105 m/s. A source row says 320 km/h.

1. Adapter recognizes source unit km/h.
2. Convert: `320 / 3.6 = 88.89 m/s`.
3. Validate finite: yes.
4. Validate range: yes.
5. Store canonical value with source provenance.

If conversion were delayed until model code, validation would see 320 and reject a valid record—or the range would be widened and allow truly impossible m/s values. Therefore conversion belongs at the adapter boundary.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/20_pipeline_contract`

### What we are about to build

A miniature pipeline that writes one immutable artifact per stage. Although small, it teaches the idea that every stage has named input/output and observable status.

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

**Code: stages=['ingest','validate','window','train','evaluate','publish']**
- **What the line is doing:** Declare the lifecycle as distinct responsibilities.
- **What to inspect:** A stage name should correspond to one recoverable contract.

**Code: run/f'{i:02d}_{name}.json'**
- **What the line is doing:** Give each output a deterministic path within a run.
- **What to inspect:** Production artifacts also need version and content metadata.

**Code: {'stage':name,'status':'succeeded'}**
- **What the line is doing:** Persist machine-readable state instead of relying on console text.
- **What to inspect:** Real status should be written atomically after success.


### State and tensor trace

```text
external row
   ↓ adapter parses names and units
canonical row
   ↓ validator checks invariants
admitted row + quality report
   ↓ window builder
model-ready example
```

Each arrow is a contract boundary with tests. A failure should name the earliest boundary it violates.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Rename one source column, duplicate a timestamp, insert infinite speed, and swap throttle/brake. Notice that only some defects are detectable from shape and range.

### Diagnose from the earliest failed contract

Validate in layers: schema → types → units → temporal keys → ranges → cross-field relationships → distribution warnings. A semantic swap may require known examples or correlation checks.

### Repair and lock the repair with a test

Create fixtures for one valid row and one row for every failure class. Make adapters produce the same canonical column order and metadata. Record source, adapter version and conversion policy.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: Loose dataframe convention**
- **Choose it when:** Exploratory one-off analysis.
- **Do not choose it when:** Multiple sources, teams or production reuse.

**Implementation: Pydantic/dataclass contract**
- **Choose it when:** You need typed configuration and row/batch metadata validation.
- **Do not choose it when:** Per-element validation becomes a throughput bottleneck; validate batches at boundaries.

**Implementation: Schema registry**
- **Choose it when:** Many producers and consumers evolve independently.
- **Do not choose it when:** A small local project where the operational overhead exceeds value.

**Implementation: Silent coercion**
- **Choose it when:** Almost never; only for explicitly documented benign parsing.
- **Do not choose it when:** Any conversion that can change scientific meaning.


APEX adapters own source parsing and canonical conversion. Core training code imports only the canonical contract. Validation produces a report and blocks hard failures before sequence construction.

## Transfer the lesson into Project APEX

Read the contract and both adapters side by side. Confirm that training, evaluation and UI modules never call FastF1 or OpenF1 directly.

### Repository path to inspect

```text
apex_engine/src/apexsim/contracts.py
apex_engine/src/apexsim/data/validate.py
apex_engine/src/apexsim/data/fastf1_adapter.py
apex_engine/src/apexsim/data/openf1_adapter.py
```

## Connection to research

Research code often assumes a fixed benchmark tensor. Production world models need a stronger boundary because source evolution can alter semantics without changing array shape.

## Check your understanding before continuing

1. Why should source adapters avoid model-specific feature engineering?
2. Give an example of a warning rather than a hard error.
3. What metadata is needed to reproduce a canonical dataset?

## Solutions and reasoning

**1.** It couples data acquisition to one model and creates inconsistent versions across experiments; stable raw canonical features should precede reproducible transforms.
**2.** A session with unusually high rain or a slightly lower sample rate may be valid but deserves attention.
**3.** Source identifiers, retrieval time, adapter version, units, alignment policy, validation configuration, feature code version and dataset hash.

## Independent build challenge

Define a canonical telemetry schema in JSON Schema or Pydantic. Implement two toy adapters with different names and units, and prove with tests that they produce identical canonical rows.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
