> **Authoritative first read:** [`00_MASTER_BUILD_GUIDE.md`](00_MASTER_BUILD_GUIDE.md).

> **Research edition:** after this file, continue with [`RESEARCH_SIMULATION_START_HERE.md`](RESEARCH_SIMULATION_START_HERE.md) for the paper-derived models, replication gates and future game-validation plan.

# Project APEX — Complete Simulation Start Here

This edition keeps the original APEX apprenticeship, telemetry contract, GRU/RSSM/SSM work, pipeline, tests, UI, and verified artifacts. It adds the missing layer required to begin a complete racing simulation **without owning or reading telemetry from the F1 25 game**.

## The actual product definition

APEX is a hybrid race-simulation and decision system:

1. reconstruct tracks and race states from permitted public/historical sources;
2. run a transparent semi-empirical vehicle, tyre, fuel, weather and race model;
3. calibrate that model against recorded telemetry and lap/stint outcomes;
4. train learned residual/world models only on the errors the physics model cannot explain;
5. simulate multiple drivers, traffic, DRS, pits, flags and changing weather;
6. evaluate alternative actions and strategies with uncertainty;
7. expose replay, counterfactual and planning results through an API and interface.

It is **not** a claim to reproduce a confidential team simulator. Public broadcast telemetry cannot identify every hidden car parameter, setup choice, tyre quantity, aerodynamic map, energy-management policy or driver intention. APEX must report uncertainty and keep every assumption visible.

## Run the complete-simulation vertical slice

```bash
cd apex_engine
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,real-data]'
pytest -q
apexsim simulate-race --laps 6 --output artifacts/complete_sim_demo
```

Expected outputs:

```text
artifacts/complete_sim_demo/
├── events.csv
├── standings.csv
├── laps.csv
├── quality_report.json
├── stints.csv
├── summary.json
├── telemetry.csv
└── track.csv
```

The research-grounded delivered build was verified with **24 passing tests** and a six-car, six-lap demo that produces complete telemetry, pit events and final standings.

## Read in this order

1. `docs/complete_sim/00_MASTER_SPEC.md`
2. `docs/complete_sim/01_ARCHITECTURE.md`
3. `docs/complete_sim/02_DATA_PLAN_WITHOUT_F1_25.md`
4. `docs/complete_sim/03_PHYSICS_AND_HYBRID_MODEL.md`
5. `docs/complete_sim/04_RACE_SYSTEMS.md`
6. `docs/complete_sim/05_WORLD_MODEL_AND_PLANNING.md`
7. `docs/complete_sim/06_EVALUATION_AND_ACCEPTANCE_GATES.md`
8. `docs/complete_sim/07_BUILD_PLAN.md`
9. `BUILD_BACKLOG.csv`
10. `docs/complete_sim/10_LEGAL_DATA_AND_BRANDING.md`

## The first four implementation milestones

### M0 — Reproducible baseline

Run the delivered demo unchanged. Inspect every telemetry column. Change one parameter at a time and confirm the expected causal response.

### M1 — Public-data replay

Download one practice or qualifying session, build a canonical lap, reconstruct its track, and run recorded controls through `replay_controls`. Do not proceed until units, time alignment and lap boundaries are correct.

### M2 — Calibrated single-car simulator

Fit longitudinal coefficients, tyre degradation and track-specific grip. Beat persistence and constant-acceleration baselines on matched multi-step replay metrics.

### M3 — Closed-loop lap simulation

Replace recorded future controls with the transparent driver policy, then with imitation learning. Complete full laps without impossible speeds, negative fuel, teleportation or unstable error growth.

## Non-negotiable rules

- Never split random frames from the same lap across train and test.
- Never call a scenario result causal unless the intervention is inside a validated support region.
- Never compare one-step and multi-step metrics as if they were equivalent.
- Never hide corrections in magic constants without an assumption entry and test.
- Never use official Formula 1 logos, fonts, visual assets or branding for APEX.
- Do not redistribute a scraped historical dataset inside the repository.
- Keep raw-source downloads outside Git; store manifests, hashes and derived schemas instead.
- Treat public telemetry as limited, noisy broadcast data—not team-grade ground truth.

## Where the new code lives

```text
apex_engine/src/apexsim/sim_core/
├── calibration.py     # interpretable parameter fitting
├── driver.py          # transparent baseline driver policy
├── hybrid.py          # bounded learned-residual interface
├── race.py            # multi-car orchestrator
├── replay.py          # recorded-control validation
├── strategy.py        # Monte Carlo strategy evaluation
├── track.py           # synthetic/public-data track reconstruction
├── tyres.py           # compound, temperature, wear and wetness
├── types.py           # typed simulation state and contracts
├── vehicle.py         # semi-empirical point-mass dynamics
└── weather.py         # interpolated weather and flag schedules
```

The original neural world-model package remains intact. The intended end state is **physics prior + learned residual + driver policy + race orchestration + planner**, not “replace everything with a giant neural network.”
