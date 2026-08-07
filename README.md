# Research-Grounded Complete Simulation Edition

> **Authoritative first read:** [`00_MASTER_BUILD_GUIDE.md`](00_MASTER_BUILD_GUIDE.md). It governs implementation order, evidence requirements, AI planning behaviour and promotion into the production simulator.

**Begin with [`RESEARCH_SIMULATION_START_HERE.md`](RESEARCH_SIMULATION_START_HERE.md).** This edition preserves the complete no-game simulator and adds a 22-paper paper-to-code programme, runnable equation-level starters, replication protocols, a future F1-game evidence contract, and a gated path toward a research-grade public-data simulator.

Verified in this edition: **24 tests pass**, the paper registry exports, and `apexsim research-demo` produces strategy, tyre-energy and latent-degradation artifacts.

---


# Project APEX Engineering Apprenticeship

This is the instructor-style, hands-on replacement for the earlier topic-list curriculum.

The package teaches concepts by creating the engineering problem first, building the smallest working implementation, inspecting its values and tensors, breaking it deliberately, diagnosing the earliest failed contract, repairing it with a regression test, comparing alternatives and transferring the idea into the production APEX engine.

## Main reading order

1. `Project_APEX_Apprenticeship_START_HERE.pdf`
2. `textbook/output/Project_APEX_Engineering_Apprenticeship_Teaching_Core.pdf`
3. `textbook/output/Project_APEX_Executable_Lab_Manual.pdf`
4. `textbook/output/Project_APEX_Tensor_Memory_and_Data_Flow_Visual_Atlas.pdf`
5. `textbook/output/Project_APEX_Ten_Project_Instructor_Ladder.pdf`
6. `textbook/output/Project_APEX_Production_Debugging_Casebook.pdf`
7. `research_reading/Project_APEX_Research_Reading_and_Design_Guide.pdf`
8. `field_workbook/Project_APEX_Field_Workbook.pdf`
9. `source_code_companion/Project_APEX_Annotated_Source_Code_Companion.pdf`
10. `apex_engine/Project_APEX_Ultimate_Textbook.pdf`

The same set is merged into `Project_APEX_Engineering_Apprenticeship_COMPLETE_524_Pages.pdf`.

## What is genuinely new

The 82-page Teaching Core contains 20 distinct instructor-led chapters. Each chapter includes:

- a real failure or need that earns the concept;
- a prediction prompt before explanation;
- plain-language and technical intuition;
- a hand-worked numerical example;
- a runnable lab and captured output;
- code explained as state transitions and contracts;
- tensor/state traces;
- a deliberate bug;
- diagnosis from the earliest failed boundary;
- repair and regression-test design;
- implementation-choice comparisons;
- exact APEX repository paths;
- research-paper connection;
- questions, reasoned solutions and an independent challenge.

## Runnable learning assets

- 20 executable labs.
- 10-project ladder, culminating in APEX.
- 15 production debugging cases.
- 20 original system diagrams and a 47-page visual atlas.
- Field Workbook for predictions, experiments and ADRs.
- Annotated source companion with line-by-line production-code notes.
- Working GRU, selective SSM-style and RSSM model implementations.
- Synthetic causal telemetry, FastF1/OpenF1 adapters, evaluation, ablations, pipeline, registry, FastAPI and Gradio UI.

## Quick start

```bash
cd apex_engine
python -m venv .venv
source .venv/bin/activate
pip install -e .
pytest -q
apexsim run --config configs/fast.yaml --run-id my_first_run
apexsim ui --run-dir artifacts/runs/my_first_run --config configs/fast.yaml
```

For the labs, place the repository root on `PYTHONPATH` when a lab imports `education.core`:

```bash
cd ..
PYTHONPATH=. python labs/03_force_model/solution.py
```

## Verified in the delivered build

- 20/20 lab solutions executed.
- Projects 1–9 executed.
- APEX test suite: 6 passed.
- Python source, tests and Airflow DAG compiled.
- Fresh end-to-end GRU run succeeded.
- UI `Blocks` application constructed from the fresh run.
- Complete PDF: 524 pages.
- No page in the combined PDF had empty/near-empty extractable content.

See `VERIFICATION_REPORT.md` for details and limitations.
