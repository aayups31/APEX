# Architecture

This directory describes how APEX is designed to evolve from a deterministic prototype into a research-grade motorsport simulator.

## Documents

- [Simulator maturity model](simulator-maturity-model.md)
- [No-game dependency](no-game-dependency.md)
- [Simulation state and action contract](simulation-state-action-contract.md)
- [ADR 0001: evidence platform boundary](adr-0001-evidence-platform.md)
- [Master Build Guide](../../00_MASTER_BUILD_GUIDE.md)

## Architectural direction

APEX follows a hybrid approach:

```text
Known physical dynamics
        +
Calibrated empirical models
        +
Probabilistic event models
        +
Learned residual corrections
        +
Strategy optimization
        +
Uncertainty estimation
