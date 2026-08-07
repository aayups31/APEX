# APEX

**A research-driven motorsport simulation platform for physics-informed race modelling, strategy optimization, and learned world models.**

APEX is an evolving Formula 1 simulation engine built to explore a difficult question:

> Can a simulator combine vehicle dynamics, telemetry, race strategy, optimization, and machine learning to predict how a race evolves under different decisions?

The project currently includes a deterministic multi-car simulation prototype, public-telemetry pipelines, research-paper implementations, strategy environments, and experimental world-model components.

APEX is in active development. It is **not yet a high-fidelity representation of a current Formula 1 car**, but it has been structured from the beginning to progress toward a validated, real-world-oriented simulator.

---

## Current Stage

APEX is currently an **early research and simulation prototype**.

The present system is designed to establish:

- deterministic and testable simulation foundations;
- physically reasonable state transitions;
- repeatable telemetry generation;
- research-paper reproduction workflows;
- strong statistical and physical baselines;
- public-data calibration infrastructure;
- clear validation gates before advanced models are promoted.

The immediate objective is not to visually imitate a racing game. It is to build a simulator whose behaviour can be measured, challenged, calibrated, and improved.

---

## What APEX Currently Includes

### Race simulation

- Multi-car race execution
- Lap and sector progression
- Synthetic and reconstructed tracks
- Pit stops and compound changes
- Driver pace modes
- Traffic and simplified overtaking
- DRS eligibility
- Yellow flags, virtual safety cars, and safety cars
- Dry and changing-weather conditions
- Deterministic seeded simulations

### Vehicle and race-state modelling

- Semi-empirical longitudinal vehicle dynamics
- Curvature-dependent speed constraints
- Aerodynamic drag and downforce approximations
- Simplified friction-circle constraints
- Fuel mass and fuel consumption
- Simplified battery and ERS state
- Tyre age, temperature, health, and degradation
- Soft, medium, hard, intermediate, and wet compounds
- Inlap, pit-lane, and outlap behaviour

### Data and telemetry

- Synthetic telemetry generation
- FastF1 data adapter
- OpenF1 data adapter
- Canonical telemetry contracts
- Session-aware dataset splitting
- Train-only normalization
- Windowed time-series datasets
- Race, lap, stint, event, and telemetry exports
- Historical replay and calibration interfaces

### Machine learning and research

- Statistical and persistence baselines
- Ridge-regression experiments
- GRU transition models
- Selective state-space model experiments
- Recurrent state-space model experiments
- Tyre-energy forecasting protocols
- Reinforcement-learning strategy environment
- Counterfactual scenario interfaces
- Monte Carlo strategy evaluation
- Research-paper-to-code mappings
- Explainability and feature-ablation scaffolding

---

## What APEX Does Not Claim Yet

APEX does not currently claim to provide:

- an exact model of a modern Formula 1 car;
- proprietary team-level tyre behaviour;
- an accurate current power-unit model;
- validated aerodynamic wake interactions;
- reliable real-race finishing-order predictions;
- exact driver or team strategy replication;
- complete real-time race-engineering capability.

Several current models are transparent approximations or research proxies. They remain isolated and labelled until they can be calibrated against stronger evidence.

---

## System Architecture

```text
                         ┌─────────────────────┐
                         │  Public Telemetry   │
                         │ FastF1 / OpenF1     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Canonical Data      │
                         │ Contracts & Quality │
                         └──────────┬──────────┘
                                    │
                ┌───────────────────┴───────────────────┐
                │                                       │
                ▼                                       ▼
     ┌─────────────────────┐                ┌─────────────────────┐
     │ Physics-Informed    │                │ Learned Models      │
     │ Simulation Kernel   │                │ GRU / SSM / RSSM    │
     └──────────┬──────────┘                └──────────┬──────────┘
                │                                       │
                └───────────────────┬───────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Hybrid Transition   │
                         │ and Uncertainty     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Race Simulation     │
                         │ Traffic / Tyres /   │
                         │ Fuel / ERS / Flags  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Strategy Planning   │
                         │ Search / RL / MPC   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Evaluation          │
                         │ Replay / Ablation / │
                         │ Counterfactuals     │
                         └─────────────────────┘
```

---

## Core Engineering Principles

### 1. Build the simulator before trusting the neural network

Known physical relationships should remain explicit wherever practical. Learned components are used to estimate unknown behaviour or correct model residuals—not to hide every subsystem inside one black box.

### 2. Baselines are mandatory

A complex model must be compared against simpler alternatives such as:

- persistence;
- constant acceleration;
- analytical dynamics;
- linear regression;
- tree-based models;
- deterministic strategy heuristics.

A neural model is not considered useful merely because it trains successfully.

### 3. One-step accuracy is not enough

APEX evaluates closed-loop and multi-step behaviour. A model that produces good immediate predictions but unstable rollouts cannot be trusted by a planner.

### 4. Data domains remain separate

The project distinguishes between:

- synthetic simulator data;
- public historical telemetry;
- research-derived approximations;
- future game telemetry;
- unavailable proprietary measurements.

Proxy values are never presented as measured Formula 1 ground truth.

### 5. Every promotion requires evidence

A model or subsystem only enters the main simulator after it passes:

- unit and dimensional checks;
- physical invariants;
- deterministic regression tests;
- baseline comparisons;
- unseen-session evaluation;
- counterfactual sanity tests;
- rollout stability tests.

---

## Research Foundation

APEX uses published research as an engineering input rather than only as background reading.

Two initial foundation papers are:

### Towards Learning-Based Formula 1 Race Strategies

This work motivates the lap-level strategy model used by APEX, including:

- fuel-energy allocation;
- battery-energy allocation;
- tyre wear;
- compound selection;
- pit-stop timing;
- race-time optimization;
- mixed discrete and continuous decisions;
- reinforcement learning benchmarked against mathematical optimization.

### Explainable Time Series Prediction of Tyre Energy in Formula One Race Strategy

This work informs the tyre-energy forecasting pipeline, including:

- four-wheel target modelling;
- telemetry-based time-series windows;
- track-state encoding;
- seen-track and unseen-track evaluation;
- recurrent and transformer forecasting models;
- XGBoost and linear baselines;
- temporal feature importance;
- counterfactual explanations.

The original paper uses private team telemetry and measured tyre-energy targets. APEX therefore uses clearly labelled proxy targets until equivalent measurements become available.

Additional work covering race simulation, Monte Carlo methods, tyre dynamics, optimal control, hybrid energy management, reinforcement learning, world models, and multi-agent strategy is catalogued in:

```text
PAPER_IMPLEMENTATION_MATRIX.csv
RESEARCH_BACKLOG.csv
research/
```

---

## Repository Structure

```text
APEX/
├── 00_MASTER_BUILD_GUIDE.md
├── README.md
│
├── apex_engine/
│   ├── src/
│   ├── tests/
│   ├── configs/
│   ├── artifacts/
│   └── pyproject.toml
│
├── research/
│   ├── paper implementations
│   ├── experiment protocols
│   └── research notes
│
├── learning/
│   ├── textbook/
│   ├── labs/
│   ├── projects/
│   ├── debugging_cases/
│   ├── field_workbook/
│   └── source_code_companion/
│
├── BUILD_BACKLOG.csv
├── RESEARCH_BACKLOG.csv
├── PAPER_IMPLEMENTATION_MATRIX.csv
├── SIMULATOR_MATURITY_MODEL.md
├── COMPLETE_SIMULATION_START_HERE.md
└── RESEARCH_SIMULATION_START_HERE.md
```

### `apex_engine/`

The runnable simulator, data pipeline, models, tests, command-line interface, and experiment infrastructure.

### `research/`

Paper-derived implementations and experiments that have not necessarily been promoted into the production simulation kernel.

### `learning/`

The optional engineering apprenticeship created alongside APEX. It contains textbooks, executable labs, debugging cases, smaller projects, and annotated source-code material.

The simulator does not depend on the learning material.

### `00_MASTER_BUILD_GUIDE.md`

The governing engineering document for APEX. It defines implementation order, validation requirements, research rules, subsystem definitions of done, and restrictions against prematurely introducing advanced models.

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/aayups31/APEX.git
cd APEX/apex_engine
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\activate
```

### 3. Install APEX

```bash
python -m pip install --upgrade pip
python -m pip install -e '.[dev,real-data]'
```

### 4. Run the tests

```bash
pytest -q
```

### 5. Run a sample race simulation

```bash
apexsim simulate-race \
  --laps 6 \
  --output artifacts/demo_race
```

The run produces structured artifacts such as:

```text
artifacts/demo_race/
├── telemetry.csv
├── laps.csv
├── stints.csv
├── events.csv
├── standings.csv
├── track.csv
├── summary.json
└── quality_report.json
```

---

## Research Commands

Display the paper implementation catalog:

```bash
apexsim research-catalog
```

Run the research demonstration:

```bash
apexsim research-demo \
  --output artifacts/research_demo
```

Individual research modules should be treated as experiments until their corresponding validation gates are satisfied.

---

## Development Roadmap

APEX follows an evidence-gated maturity model.

### R0 — Deterministic foundation

- Reproducible synthetic fixtures
- Simulation contracts
- Physical invariants
- Regression tests
- Structured artifacts

### R1 — Research implementation

- Paper equations translated into isolated modules
- Baseline reproduction
- Strategy environment
- Tyre-energy forecasting protocol
- Paper-to-code traceability

### R2 — Public-data calibration

- FastF1 and OpenF1 ingestion
- Historical-session reconstruction
- Track and telemetry alignment
- Fuel and tyre parameter estimation
- Seen-session and unseen-session evaluation

### R3 — Calibrated single-car simulation

- Stable closed-loop laps
- Sector and lap-time validation
- Compound-dependent behaviour
- Fuel and energy consistency
- Uncertainty estimates

### R4 — Hybrid world model

- Physics-informed transition model
- Learned residual dynamics
- Multi-step rollout evaluation
- Out-of-distribution detection
- Planner-exploitation tests

### R5 — Race-state simulation

- Stochastic pit stops
- Weather evolution
- Race-control events
- Traffic and aerodynamic interaction
- Probabilistic reliability models

### R6 — Full-field strategy simulation

- Complete race grids
- Driver and car variation
- Multi-car interactions
- Monte Carlo race distributions
- Historical strategy replay

### R7 — Adaptive strategy optimization

- Counterfactual race evaluation
- Dynamic programming
- Reinforcement learning
- Model predictive control
- Mixed discrete-continuous planning

### R8 — Multi-agent strategy

- Competitor-aware policies
- Teammate interactions
- Strategic self-play
- Adversarial scenario evaluation

### R9 — Additional validation domains

When game telemetry becomes available, it will be used as an additional controlled validation domain for:

- throttle and braking response;
- tyre and fuel experiments;
- ERS deployment;
- compound crossover;
- pit-loss analysis;
- controlled counterfactual testing.

Game telemetry will not be treated as direct real-world ground truth.

### R10 — Research-grade simulator

The long-term goal is a simulator that is:

- calibrated;
- probabilistic;
- uncertainty-aware;
- reproducible;
- interpretable;
- robust across circuits;
- useful for counterfactual strategy analysis;
- honest about its remaining limitations.

---

## Current Development Priorities

The current priority is to strengthen the foundations before expanding the interface or adding larger models.

The next major areas are:

1. Historical public-telemetry replay
2. Track reconstruction and alignment
3. Single-car calibration
4. Strong matched-horizon baselines
5. Closed-loop rollout evaluation
6. Tyre degradation identification
7. Fuel and energy calibration
8. Unseen-track testing
9. Uncertainty modelling
10. Full-field stochastic validation

---

## Evaluation Philosophy

APEX is evaluated using more than a single aggregate error.

Relevant measurements include:

- speed MAE and RMSE;
- sector-time error;
- lap-time error;
- trajectory and progress error;
- rollout error by prediction horizon;
- fuel and battery constraint violations;
- tyre-state violations;
- collision and ordering consistency;
- calibration error;
- unseen-track performance;
- strategy regret against an optimization oracle;
- stability under disturbances;
- deterministic reproducibility.

Each result should state:

- the data source;
- the evaluation horizon;
- the baseline;
- the train and test separation;
- the assumptions involved;
- the known failure modes.

---

## Why Build APEX?

Race simulation sits at the intersection of several areas I want to understand deeply:

- vehicle dynamics;
- numerical simulation;
- control systems;
- time-series modelling;
- reinforcement learning;
- world models;
- optimization;
- probabilistic systems;
- production machine-learning infrastructure.

APEX is intended to be more than a one-off model or dashboard. It is a long-term engineering project for learning how these systems interact, how they fail, and how they can be validated.

---

## Project Status

```text
Status: Active development
Current focus: Simulation foundations and public-data calibration
Primary language: Python
Game dependency: None
Public-data support: FastF1 and OpenF1 adapters
Intended use: Research, education, and engineering experimentation
```

---

## Disclaimer

APEX is an independent, unofficial research project.

It is not affiliated with, endorsed by, or connected to Formula 1, the FIA, any Formula 1 team, any game publisher, or any telemetry provider.

Formula 1 and related marks belong to their respective owners. No official game assets, team assets, logos, fonts, or proprietary telemetry are included in this repository.