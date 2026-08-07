# Architecture

## Bounded contexts

### Data plane

Owns downloads, manifests, raw cache, adapters, time alignment, schemas, quality checks and immutable processed datasets.

### Simulation kernel

Owns track coordinates, vehicle transition, tyre state, fuel/energy, environment, race rules and event ordering. It must be deterministic for a fixed seed.

### Learning plane

Owns baselines, residual models, latent world models, driver imitation, uncertainty and experiment tracking. It must not write directly into race state without passing constraints.

### Planning plane

Owns candidate generation, rollout budgets, objectives, risk measures and recommendation traces.

### Product plane

Owns API, UI, saved investigations and visual evidence. It consumes versioned simulation outputs; it does not contain simulation logic.

## Recommended repository evolution

```text
src/apexsim/
├── data/
│   ├── adapters/
│   ├── alignment/
│   ├── contracts/
│   ├── quality/
│   └── tracks/
├── sim_core/                 # delivered vertical slice
├── models/
│   ├── baselines/
│   ├── residual/
│   ├── world_model/
│   ├── driver_policy/
│   └── uncertainty/
├── planning/
│   ├── strategy/
│   ├── mpc/
│   └── objectives/
├── evaluation/
│   ├── replay/
│   ├── rollout/
│   ├── physical/
│   └── race/
├── pipeline/
├── serving/
└── ui/
```

Do not perform this directory migration before M1. The delivered `sim_core` package is intentionally compact so the first vertical slice remains understandable.

## Runtime architecture

### Offline training/replay

```text
Downloader → raw object store → transformation job → canonical Parquet
     → track build → calibration → training → evaluation → registry
```

### Interactive scenario

```text
API request
  → validate intervention and support
  → load immutable model/simulator bundle
  → run ensemble rollouts
  → aggregate outcomes and uncertainty
  → persist result ID
  → return evidence summary
```

### Future live mode

Historical replay should be complete before live mode. A live system needs stream buffering, event-time ordering, late-data handling, checkpointed state and a strict separation between received observations and inferred hidden state.

## Reproducibility contract

A run ID is invalid unless it records:

- Git commit or source archive hash;
- Python and package versions;
- config snapshot;
- raw/processed dataset hashes;
- split manifest;
- random seeds;
- model checkpoint hash;
- simulator parameter hash;
- evaluation code version.

## Performance budget

Initial targets on a laptop:

- single-car replay: at least 100× faster than real time;
- 20-car deterministic race: at least 10× faster than real time;
- 100 strategy rollouts: under a few minutes after vectorization;
- API preview: first result under two seconds using reduced fidelity;
- full analysis: asynchronous job only after a proper job runner exists.

Do not optimize before profiling. The first bottlenecks will likely be Python object loops, repeated track interpolation and dataframe creation. Keep kernel state in arrays once correctness is frozen.

## Failure isolation

Every layer should fail loudly:

- adapter: schema or source mismatch;
- alignment: impossible timestamp gap;
- track build: non-closed path or excessive jitter;
- calibration: insufficient excitation or poor fit;
- simulator: invariant violation;
- model: unsupported intervention or out-of-distribution state;
- planner: insufficient rollout budget or unstable ranking;
- UI: unavailable evidence, never fabricated evidence.
