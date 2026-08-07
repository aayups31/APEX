# APEX Research Edition

Run `apexsim research-catalog` and `apexsim research-demo --output artifacts/research_demo`. Read `../RESEARCH_SIMULATION_START_HERE.md` before promoting any paper-derived model into the production race kernel.

The research layer is under `src/apexsim/research/`; it includes strategy equations, tyre-energy forecasting protocols, latent degradation, a portable RL interface and the future game-evidence contract.

---

# APEX Complete Simulation Extension

Run `apexsim simulate-race --laps 6 --output artifacts/complete_sim_demo` after installation. Read `../COMPLETE_SIMULATION_START_HERE.md` and `docs/complete_sim/00_MASTER_SPEC.md` before extending the original world-model pipeline.

---

# Project APEX

## F1 Telemetry World-Simulation Engine

Project APEX is an educational but production-structured implementation of a telemetry world model for Formula 1-style simulation. It starts with FastF1/OpenF1-compatible historical data and an offline synthetic generator, then creates a stable path toward F1 25 UDP telemetry.

## What the system does

```text
source data
   ↓
source adapter
   ↓
canonical telemetry contract
   ↓
quality validation and session-level splits
   ↓
sequence windows and train-only normalization
   ↓
GRU / RSSM / SSM-style world model
   ↓
multi-step evaluation and feature ablations
   ↓
scenario interventions and imagined rollouts
   ↓
run registry, API and interactive UI
```

A user can select a telemetry window, alter throttle, braking, grip, rain and tyre-degradation assumptions, then compare the model’s imagined future with the recorded future.

## Verified reference results

The package includes successful reference runs for all three neural architectures. Exact values depend on the packaged random seed and training budget; see each `summary.json` for the full report.

| Model | Purpose | Reference speed MAE |
|---|---|---:|
| GRU | stable deterministic V1 | about 13.7 km/h over an 8-step autoregressive rollout |
| selective SSM-style model | persistent structured sequence state | about 13.7 km/h |
| RSSM | stochastic Dreamer-style latent imagination | about 28.9 km/h under the intentionally tiny fast-training budget |

The RSSM result is deliberately not hidden. Stochastic latent models can be harder to optimize and should be adopted because uncertainty or branching futures provide measured value, not because Dreamer is fashionable.

## Install and run

```bash
pip install -e .
pytest -q
apexsim run --config configs/fast.yaml --run-id reference_gru
apexsim ui --run-dir artifacts/runs/reference_gru --config configs/fast.yaml
```

For the REST inspection API:

```bash
apexsim api --artifacts-dir artifacts/runs
```

## Real historical data

FastF1 adapter:

```bash
pip install -e '.[real-data]'
apexsim ingest-fastf1 \
  --year 2025 \
  --event Monza \
  --session R \
  --driver VER \
  --output data/raw/monza_ver.csv
```

OpenF1 adapter:

```bash
apexsim ingest-openf1 \
  --session-key 9159 \
  --driver-number 55 \
  --output data/raw/openf1_9159_55.csv
```

The adapters translate different names, units and sampling schedules into the same contract. Historical endpoint availability and fields can change, so inspect and validate every ingestion run.

## Architecture choices

### Why start with a GRU?

The GRU is causal, compact, easy to debug and strong enough to reveal whether the data contract and evaluation design work. It is the best engineering baseline before a more complicated latent system.

### Why include an RSSM?

The recurrent state-space model separates deterministic memory from a stochastic latent variable. That enables probabilistic imagination and is the core modelling concept behind Dreamer. It also introduces KL balancing, posterior/prior mismatch and greater optimization sensitivity.

### Why include an SSM-style model?

State-space models provide a persistent hidden state and attractive scaling for long histories. The included selective cell teaches input-dependent retention and forgetting. It is not presented as a drop-in reproduction of the hardware-optimized Mamba implementation.

### Why use Gradio for V1?

The UI is deliberately a replaceable client. Gradio lets the entire simulator run with one Python command and no Node toolchain. The modelling and data layers do not import UI code, so a later React/Next.js client can consume the FastAPI service without changing the engine.

## Honest limitations

- Public historical telemetry does not expose all driver inputs and vehicle states available from the F1 25 game.
- Steering is approximated from track-heading change until real game control packets are available.
- The synthetic generator is a controlled educational dynamics system, not a high-fidelity tyre, aero or suspension solver.
- Counterfactual rollouts can leave the behaviour distribution seen in training; they must be treated as hypotheses, not guaranteed physical truth.
- A real race-engineering product would require much larger multi-track data, strict versioning, model calibration, uncertainty tests, human review and closed-loop validation.

## Feed real canonical data into the complete pipeline

The ingestion commands create the same source-independent CSV contract used by the offline generator. Run the complete training, evaluation, ablation and publication path with:

```bash
apexsim run-canonical \
  --input-path data/raw/monza_ver.csv \
  --config configs/fast.yaml \
  --run-id monza_ver_gru
```

`run-canonical` copies the exact validated input into the run directory before any split or normalization step. This makes the source file part of immutable run lineage and ensures that FastF1, OpenF1 and synthetic evidence all execute through the same downstream code.
