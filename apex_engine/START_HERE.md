# Project APEX — Start Here

Project APEX is a complete learning project for building an F1 telemetry world-simulation engine before you own F1 25.

## Fastest verified path

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
pytest -q
apexsim run --config configs/fast.yaml --run-id my_first_run
apexsim ui --run-dir artifacts/runs/my_first_run --config configs/fast.yaml
```

The first run uses the offline synthetic telemetry generator. No API key, game or network connection is required.

## Learning order

1. Read `Project_APEX_Ultimate_Textbook.pdf`.
2. Run the seven notebooks in numeric order.
3. Rebuild each pipeline phase using `docs/course/`.
4. Launch the UI and change scenario controls.
5. Run the feature ablations and explain each result.
6. Add a real FastF1 or OpenF1 session.
7. Train a general model, then fine-tune it on one held-out track.
8. When F1 25 is available, implement the UDP adapter described in the migration chapter.

## What V1 means

V1 predicts a compact telemetry state over a future horizon using observed history, driver-control signals and environmental context. It is not a complete rigid-body vehicle simulator and it is not yet an RL racing agent. It is the correct first substrate for both.

## Important files

- `src/apexsim/contracts.py` — source-independent data contract.
- `src/apexsim/data/` — synthetic, FastF1 and OpenF1 adapters.
- `src/apexsim/models/` — GRU, RSSM and SSM-style world models.
- `src/apexsim/training.py` — explicit training loop.
- `src/apexsim/evaluation.py` — horizon and physical-validity metrics.
- `src/apexsim/simulation.py` — controlled future interventions.
- `src/apexsim/pipeline/` — idempotent stages and local runner.
- `src/apexsim/ui.py` — interactive race-engineering interface.
- `dags/apexsim_dag.py` — Airflow wrapper around the same stages.
- `artifacts/runs/reference_*` — verified model runs.

## First real historical run

After an adapter has produced a canonical CSV, run the exact same downstream pipeline used by the offline reference:

```bash
apexsim ingest-fastf1 \
  --year 2025 --event Monza --session R --driver VER \
  --output data/raw/monza_ver.csv

apexsim run-canonical \
  --input-path data/raw/monza_ver.csv \
  --config configs/fast.yaml \
  --run-id monza_ver_gru
```

The source adapter stops at the canonical contract. Validation, independent splits, train-only scaling, model training, evaluation, ablations, publication and the UI remain source-independent.
