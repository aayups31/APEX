# 6. FastF1 and OpenF1: Ingest Real Evidence Without Polluting the Core

> **Instructor objective:** Understand the complete data path from a public F1 source to canonical telemetry and learn to keep network concerns outside model code.

![6. FastF1 and OpenF1: Ingest Real Evidence Without Polluting the Core](../figures/05_contract.png)

## The problem that earns this chapter

APEX begins before you own F1 25, so historical evidence must come from public tooling. FastF1 is a Python library organized around events and sessions; OpenF1 exposes HTTP endpoints for telemetry, timing, position, weather and related records. Their access patterns differ. The engineering challenge is not “download a CSV”; it is to translate each source into evidence with the same meaning.

### Predict before reading

A FastF1 session and an OpenF1 endpoint both provide speed, throttle and timestamps, but one uses relative session time and the other UTC timestamps. What information must an adapter preserve so the two sources can later be compared or combined?

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

Network retrieval, caching, parsing, source-specific naming and canonical conversion are separate steps. Keeping them separate lets you replay raw responses when an adapter changes, test conversion without the network, and avoid rate-limit failures inside training.

The safest ingestion process lands raw evidence first. A second deterministic step creates canonical data. This gives you two forensic layers: “what did the source return?” and “how did our code interpret it?” A model run should point to both.

FastF1 and OpenF1 can overlap without being interchangeable. Differences in sampling, provenance and field definitions should be measured rather than assumed away. APEX treats each adapter as an independently tested producer of the canonical contract.

## Vocabulary that now has a job

**Concept: Landing zone**
- **Meaning in plain language:** Immutable storage of source-native responses before interpretation.
- **Role inside APEX:** Cached session/API data used for reproducible adapter tests.

**Concept: Provenance**
- **Meaning in plain language:** Information describing where, when and how a record was obtained.
- **Role inside APEX:** Source, event/session identifiers, driver, retrieval time and adapter version.

**Concept: Idempotent ingestion**
- **Meaning in plain language:** Repeating the same request does not create conflicting outputs.
- **Role inside APEX:** Deterministic paths and hashes for source snapshots.

**Concept: Rate limit / cache**
- **Meaning in plain language:** External service constraints and local reuse strategy.
- **Role inside APEX:** Prevents training from repeatedly hitting public services.


## Worked example: calculate it by hand

Suppose OpenF1 returns UTC timestamps `12:00:00.100`, `12:00:00.300`, and FastF1 returns session-relative seconds `5.2`, `5.4`. To combine them, you need a session start reference or a shared event clock. If session start is `11:59:54.900`, the UTC records map to `5.2` and `5.4` seconds.

The adapter should preserve:

1. Source timestamp exactly as received.
2. Parsed canonical timestamp.
3. Session and driver identifiers.
4. Source field names/units or adapter version.
5. Missingness and interpolation flags.

Without those fields, an apparent 0.2-second alignment error cannot be traced.

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/19_time_alignment`

### What we are about to build

Use the alignment lab as an offline stand-in for real streams, then inspect the production FastF1 and OpenF1 adapters. The important skill is tracing a field from raw response to canonical column.

### Runnable implementation

```python
import pandas as pd

car=pd.DataFrame({'t':[0.0,0.2,0.4,0.6],'speed':[10,12,14,16]})
weather=pd.DataFrame({'t':[0.05,0.55],'rain':[0.0,0.3]})
aligned=pd.merge_asof(car.sort_values('t'),weather.sort_values('t'),on='t',direction='backward',tolerance=0.3)
print(aligned)

```

### Observed output from the packaged solution

```text
t  speed  rain
0  0.0     10   NaN
1  0.2     12   0.0
2  0.4     14   NaN
3  0.6     16   0.3
```

### Read the important lines like English

**Code: pd.merge_asof(...)**
- **What the line is doing:** Join asynchronous records after each source has been parsed into a common time representation.
- **What to inspect:** Alignment belongs after timestamp normalization.

**Code: direction="backward"**
- **What the line is doing:** Preserve online causal availability.
- **What to inspect:** Offline retrospective analysis may choose another policy, but must label it.

**Code: tolerance=...**
- **What the line is doing:** Prevent arbitrarily stale context from being treated as current.
- **What to inspect:** Record unmatched rows rather than silently filling all gaps.


### State and tensor trace

```text
network request
   ↓ raw JSON / library objects (cache this)
source parser
   ↓ typed source table
unit and timestamp conversion
   ↓ canonical columns
quality gate
   ↓ admitted canonical session + report
```

Training begins only after the last step. It should be possible to run everything after ingestion with no network.

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

Mock a source response where one field changes name, one timestamp is timezone-naive, and one speed column changes unit. Run the adapter tests and identify which change is detected.

### Diagnose from the earliest failed contract

Compare the raw snapshot with the canonical output. If the raw source is correct but canonical data is wrong, the adapter is the earliest failed boundary. If the raw response itself changed, update the source fixture and conversion policy deliberately.

### Repair and lock the repair with a test

Store representative source fixtures in tests. Assert exact canonical names, units, timestamp monotonicity and a few known values. Version adapter outputs whenever semantics change.

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

**Implementation: FastF1**
- **Choose it when:** Python-centric historical session analysis with convenient session abstractions and cached telemetry.
- **Do not choose it when:** You require an HTTP-only integration or fields outside its supported representation.

**Implementation: OpenF1**
- **Choose it when:** Service-style access to historical/live endpoint data and independent stream retrieval.
- **Do not choose it when:** You assume every endpoint is synchronized or identical to FastF1.

**Implementation: Both as separate datasets**
- **Choose it when:** You want cross-source validation or broader coverage.
- **Do not choose it when:** You have not measured semantic and temporal differences.

**Implementation: Merge sources into one row**
- **Choose it when:** There is a justified key, timing policy and conflict-resolution rule.
- **Do not choose it when:** Matching is based only on similar column names.


APEX V1 supports both adapters but does not require both for one run. Each produces the canonical contract; downstream code stays source-agnostic. Synthetic data remains the offline integration-test source.

## Transfer the lesson into Project APEX

Run an adapter command when network access is available, save canonical output, validate it, then call the same `run-canonical` pipeline used for any source.

### Repository path to inspect

```text
apex_engine/src/apexsim/data/fastf1_adapter.py
apex_engine/src/apexsim/data/openf1_adapter.py
apex_engine/src/apexsim/cli.py
apex_engine/README.md
```

## Connection to research

Public datasets are observations, not the world itself. A world model trained on one source can inherit its sampling, filtering and missingness as if those were physical laws. Cross-source tests reveal some of these artifacts.

## Check your understanding before continuing

1. Why should raw source snapshots be immutable?
2. What should happen when an external field disappears?
3. Why is network retrieval inside a PyTorch Dataset a bad default?

## Solutions and reasoning

**1.** They allow exact replay, adapter debugging and proof of what the source returned at run time.
**2.** The adapter should fail clearly or mark the field unavailable according to a versioned policy; silently substituting another field can change meaning.
**3.** It makes samples nondeterministic, slow, rate-limit dependent and difficult to retry or reproduce.

## Independent build challenge

Create a recorded fixture for one mocked FastF1-like table and one OpenF1-like JSON response. Write adapters that produce byte-for-byte identical canonical CSV rows.

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
