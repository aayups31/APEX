> **Research edition note:** this report documents the earlier subsystem verification. The current combined suite is documented in `RESEARCH_VERIFICATION_REPORT.md` and passes 24 tests.

# Project APEX Engineering Apprenticeship — Verification Report

**Build date:** 2026-08-01

## Artifact inventory and page count

| Component | Pages |
|---|---:|
| START HERE | 6 |
| Instructor-led Teaching Core | 82 |
| Executable Lab Manual | 36 |
| Tensor, Memory and Data-Flow Visual Atlas | 47 |
| Ten-Project Instructor Ladder | 13 |
| Production Debugging Casebook | 25 |
| Research Reading and Design Guide | 10 |
| Field Workbook | 87 |
| Annotated Source Code Companion | 156 |
| APEX implementation textbook/capstone reference | 62 |
| **Combined total** | **524** |

The final merged PDF was independently re-opened with `pypdf`; it contains 524 pages. A text-content scan found no empty or near-empty pages.

## Code verification

### Educational labs

All 20 `labs/*/solution.py` programs executed successfully with the repository root supplied on `PYTHONPATH` where required.

### Progressive projects

Projects 1–9 executed successfully:

- car integrator;
- telemetry quality;
- lap physics;
- MLP transition;
- track encoder;
- GRU forecaster;
- selective SSM;
- RSSM imagination;
- latent MPC.

### Production APEX engine

`pytest -q` result:

```text
......                                                                   [100%]
6 passed
```

The source tree, tests and DAG passed Python compilation. `dags/apexsim_dag.py` passed `py_compile`.

### Fresh end-to-end run

Run ID: `apprenticeship_verified`

Status: succeeded.

Key evidence:

- canonical rows: 8,400;
- sessions: 8;
- validation passed with no null cells, duplicate frames or out-of-range cells;
- model: deterministic GRU;
- epochs completed: 4;
- test samples: 1,200;
- negative-speed rate: 0;
- extreme-speed rate: 0;
- run artifacts published under `apex_engine/artifacts/runs/apprenticeship_verified`.

The exact metrics are stored in the run summary rather than treated as universal performance claims; the data are synthetic and the configuration is deliberately fast.

### UI verification

`apexsim.ui.create_app` constructed a Gradio `Blocks` application using the fresh run’s model, normalizer, canonical data, metrics and ablations. The server was not exposed publicly during artifact generation.

## Document verification

- All newly created DOCX files were rendered to PDF through the document rendering workflow.
- Representative full-resolution pages were visually inspected for headings, diagrams, equations, code and margins.
- The teaching core was revised after initial review to remove wide tables that rendered poorly; those sections now use readable teaching cards.
- Headers were replaced with the new Engineering Apprenticeship identity rather than inherited volume labels.
- The visual atlas was regenerated after repairing TeX escape control characters.
- The final combined PDF has no pages with fewer than 30 extracted text characters.

## Scope and limitations

- Live FastF1/OpenF1 network retrieval was not executed in the offline build environment. Their adapters and canonical handoff remain in the repository and are covered conceptually and structurally.
- The complete Airflow service stack was not launched. The DAG compiles and wraps the same tested stage functions used locally.
- F1 25 was unavailable. The UDP migration remains an architecture and implementation milestone based on the official data-output specification.
- The synthetic generator is a controlled causal teaching environment, not a full tyre, aerodynamics, suspension or rigid-body simulation.
- The included selective SSM is an educational input-dependent recurrent/state-space challenger, not a claim of full Mamba reproduction.
- The RSSM is a compact Dreamer-style world-model component. It is not the complete DreamerV3 actor-critic system.
