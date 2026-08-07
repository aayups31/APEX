# Project APEX — Research-Grounded Simulation Start Here

> **Read [`00_MASTER_BUILD_GUIDE.md`](00_MASTER_BUILD_GUIDE.md) first.** This file explains the research layer; the master guide is the binding authority for build order, acceptance gates and future AI planning sessions.

This edition turns the APEX simulator into a **paper-to-code research programme**. It preserves the original apprenticeship, telemetry world models and complete no-game race kernel, then adds reproducible implementations, protocols and acceptance gates derived from Formula 1 strategy, vehicle dynamics, tyre, optimal-control and world-model research.

The goal is not to paste equations into the repository. Every paper must follow this chain:

```text
paper claim
  → explicit assumptions and units
  → equation-level implementation
  → synthetic invariant tests
  → public-data calibration/replay
  → comparison against simple and optimization baselines
  → uncertainty and failure analysis
  → later game-telemetry experiment
  → only then promotion into the main simulator
```

## What is runnable now

The research layer already includes:

- a lap-wise strategy model matching the state/action topology of *Towards Learning-Based Formula 1 Race Strategies*;
- battery/fuel feasibility projection, tyre-wear dynamics, pit/inlap/outlap logic and race-time decomposition;
- a dependency-free strategy environment and a discrete beam-search oracle for small reproducible cases;
- a four-wheel tyre sliding-energy **proxy**, clearly separated from the proprietary measured target in the Mercedes/Imperial paper;
- event-safe tyre-energy forecasting windows, seen/unseen-event splits, linear/ridge and GRU protocols, RMSE/SMAPE and temporal perturbation explanations;
- an interpretable latent tyre-degradation state-space starter with fuel correction and pit resets;
- a portable race-strategy state/action/reward interface for later RL and multi-agent work;
- a future game-evidence contract and alignment/metric code so game data will test the papers rather than silently redefine the engine;
- a 22-paper registry, implementation matrix, replication standards and staged backlog.

## First run

```bash
cd apex_engine
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,real-data]'

pytest -q
apexsim research-catalog
apexsim research-demo --output artifacts/research_demo
apexsim simulate-race --laps 6 --output artifacts/complete_sim_demo
```

Research-demo outputs:

```text
artifacts/research_demo/
├── fieni_strategy_rollout.csv
├── latent_tyre_degradation.csv
├── paper_registry.csv
├── summary.json
├── synthetic_tyre_energy.csv
└── tyre_energy_predictions.csv
```

## Read in this order

1. `SIMULATOR_MATURITY_MODEL.md`
2. `research/PAPER_TO_CODE.md`
3. `research/REPLICATION_STANDARD.md`
4. `PAPER_IMPLEMENTATION_MATRIX.csv`
5. `RESEARCH_BACKLOG.csv`
6. `research/protocols/FIENI_2025.md`
7. `research/protocols/TODD_2025.md`
8. `research/protocols/HEILMEIER_MONTE_CARLO.md`
9. `research/protocols/VEHICLE_AND_TYRE_OPTIMAL_CONTROL.md`
10. `research/protocols/MULTI_AGENT_AND_RL_MPC.md`
11. `research/protocols/WORLD_MODELS.md`
12. `research/GAME_VALIDATION_LATER.md`

## The architecture direction

```text
                    ┌─────────────────────────────┐
public timing/GPS ─►│ calibrated evidence store   │◄─ future game UDP
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────────────────▼──────────────────────────┐
        │ transparent simulator                              │
        │ track + vehicle + tyre thermal/wear + fuel + ERS   │
        │ traffic + overtaking + pits + flags + weather      │
        └─────────────┬───────────────────────┬───────────────┘
                      │                       │
             learned residuals        probabilistic events
             and latent state          and uncertainty
                      │                       │
        ┌─────────────▼───────────────────────▼───────────────┐
        │ planning and strategy                              │
        │ exact small-case oracle / DP / MINLP / MPC / RL    │
        │ Monte Carlo / game theory / multi-agent self-play  │
        └──────────────────────────┬──────────────────────────┘
                                   │
                         replay + counterfactual UI
```

The final simulator should be **hybrid**, not purely neural and not purely hand-tuned. Physics and regulations provide constraints; statistical models estimate hidden states and uncertainty; learned residuals correct systematic model error; optimization provides auditable baselines; RL or world-model planning provides fast adaptive decisions.

## Promotion rule

A paper-derived component remains in `apexsim.research` until it passes all applicable gates:

1. Equation fidelity and units are documented.
2. Synthetic invariants pass.
3. It beats a simpler matched baseline.
4. Calibration and test sessions are disjoint.
5. Open-loop and closed-loop errors are both reported.
6. Failure is broken down by track section, stint, compound, weather and traffic regime.
7. Uncertainty is calibrated or the component is explicitly deterministic.
8. Counterfactual interventions stay within validated support or are flagged out-of-distribution.
9. Runtime meets its intended use.
10. A game test, when available, agrees in causal direction and bounded magnitude before the component influences the production planner.

## What “10/10 real-world simulator” means here

It does **not** mean matching a team’s confidential simulator. It means a rigorously validated public-data simulator that:

- produces physically and regulatorily feasible races;
- predicts held-out lap, stint and race outcomes better than honest baselines;
- reports calibrated uncertainty;
- responds correctly to interventions and disturbances;
- remains stable in closed loop;
- generalizes to unseen sessions and tracks with measured degradation;
- explains where its claims are strong, weak or unsupported;
- supports strategy decisions through multiple independent methods.

That is the direction enforced by the maturity gates in this kit.
