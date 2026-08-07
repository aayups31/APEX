# APEX Research Edition — Verification Report

Generated: 2026-08-06

## Automated verification

- `pytest -q`: **24 passed**.
- Python source and tests compiled with `compileall`.
- `apexsim research-catalog`: exported **22 paper records**.
- `apexsim research-demo`: completed strategy, tyre-energy forecasting and latent-degradation demos.
- The research demo was run twice and all generated files were byte-identical.
- The existing complete race simulator completed a fresh six-car, three-lap race after the research integration.

## Delivered research code

- `fienia_strategy.py`: lap-wise resource, tyre and pit dynamics plus small-case oracle.
- `strategy_env.py`: paper-compatible finite-horizon environment.
- `tyre_energy.py`: four-wheel physics-informed proxy with provenance boundary.
- `tyre_forecasting.py`: event-safe forecasting protocol, baselines, GRU and explanation utilities.
- `state_space_tyre.py`: latent degradation and pit-reset starter.
- `unified_race.py`: portable strategy state/action/reward interface.
- `game_validation.py`: future game evidence validation, alignment and matched metrics.
- `registry.py`: machine-readable 22-paper implementation map.

Research code plus dedicated tests totals approximately **1,685 lines**.

## Delivered programme controls

- 10-level simulator maturity model, R0 through R10.
- 73-item research backlog; 11 foundation items marked complete.
- Paper-to-code crosswalk and replication standard.
- Seven protocol documents.
- Future game-validation campaign with fixed evidence schema.
- Paper catalogue in CSV and JSON plus bibliography starter.
- User-paper integrity manifest with SHA-256 hashes.

## Honest limitations

- The Fienia implementation uses transparent surrogate coefficients and a beam-search oracle; it is not the authors’ confidential lap maps or exact BONMIN result.
- The tyre-energy target in the Mercedes/Imperial paper is unavailable publicly. APEX provides a clearly labelled proxy and protocol, not a claimed reproduction.
- The state-space tyre implementation is a lightweight starter, not the complete Bayesian hierarchy/skewed-t model.
- The multi-agent, RL–MPC, thermodynamic tyre and minimum-lap-time optimal-control papers are represented by interfaces and protocols until their prerequisites are met.
- Game validation remains intentionally unexecuted until the game and its telemetry source are available.

These limitations are encoded in the registry status fields and promotion gates rather than hidden in presentation text.

## Master build guide addendum

The package now includes `00_MASTER_BUILD_GUIDE.md` as the binding first-read document for human and AI contributors. It defines authority order, maturity dependencies, subsystem completion criteria, research and data standards, the future game-validation boundary, the mandatory AI planning format, forbidden shortcuts and R10 release gates.

Post-update verification:

- all 24 packaged tests passed;
- the 22-paper research catalog executed;
- the research demo generated strategy, tyre-energy proxy and latent-degradation artifacts;
- the six-car simulation completed and produced its quality report and race artifacts;
- `README.md`, `START_HERE.md`, `RESEARCH_SIMULATION_START_HERE.md` and `COMPLETE_SIMULATION_START_HERE.md` now direct builders to the master guide first.

