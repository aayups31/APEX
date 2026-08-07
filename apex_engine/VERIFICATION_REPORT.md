# Verification Report

## Automated checks

- Six Pytest tests pass, including a complete run from a source-adapter-style canonical CSV.
- All Python source and the Airflow DAG compile.
- Seven guided notebooks execute from a clean project working directory without error cells.
- A fresh GRU end-to-end run completes ingestion, validation, splitting, scaling, training, evaluation, ablations, publication and run registration.
- Separate SSM and RSSM reference runs complete successfully.
- The Gradio application constructs successfully against the packaged GRU artifacts.
- The final DOCX was rendered to 62 pages and every page was visually inspected.
- The final PDF was independently rendered and checked for page-count and layout consistency.

## Reference GRU run

- 8,400 canonical telemetry frames.
- 8 independent sessions, split at the session level.
- 16 model input channels and 5 predicted state channels.
- 1,200 held-out test windows.
- Zero negative- or extreme-speed predictions in the reference evaluation.
- Full artifacts recorded under `artifacts/runs/reference_gru/`.

## Real-data handoff

FastF1 and OpenF1 adapters emit the same canonical contract as the offline generator. `apexsim run-canonical` copies an adapter output into the immutable run directory and executes the identical validation, splitting, train-only normalization, training, evaluation, ablation and publication path.

## Boundaries of verification

- FastF1 and OpenF1 network calls were not executed in the offline build environment; their adapters use defensive validation and the downstream canonical handoff is covered by an end-to-end test.
- The Airflow service itself was not launched; the DAG compiles and imports safely when Airflow is absent.
- The F1 25 UDP adapter is a documented migration target because the game is not present in this environment.
- The synthetic generator is a controlled educational dynamics environment, not a high-fidelity tyre, aerodynamics or suspension solver.
