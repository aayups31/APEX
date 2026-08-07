> **Research edition note:** this report documents the earlier subsystem verification. The current combined suite is documented in `RESEARCH_VERIFICATION_REPORT.md` and passes 24 tests.

# Project APEX Complete Simulation Kit — Verification Report

## Verification date

August 6, 2026.

## Preserved work

The package retains the original Project APEX apprenticeship materials, 524-page engineering apprenticeship PDF, field workbook, research guide, annotated source companion, executable notebooks, original telemetry world-model engine, GRU/RSSM/SSM models, source adapters, API/UI scaffolding, artifacts and tests.

## Added complete-simulation layer

The new edition adds approximately 1,880 lines of simulation-kernel Python across:

- typed car, driver, tyre, weather, flag and race contracts;
- track generation, reconstruction and sampling;
- semi-empirical longitudinal/lateral vehicle dynamics;
- tyre grip, temperature and degradation;
- fuel mass and consumption;
- a bounded generic energy-store proxy;
- reference driver policy and pace modes;
- multi-car race ordering, traffic, DRS and overtake attempts;
- pit strategy and compound changes;
- weather and race-control schedules;
- race telemetry, lap, stint, event and standings artifacts;
- physical/invariant validation;
- recorded-control replay;
- public-data parameter calibration;
- bounded learned-residual interface;
- Monte Carlo strategy-planning interface;
- CLI and runnable example.

It also adds more than 1,400 lines of complete-simulation architecture, data, modeling, evaluation, legal and build-plan documentation, plus a 66-task implementation backlog.

## Automated checks

Executed from `apex_engine/`:

```bash
python -m pytest -q
```

Result:

```text
12 passed
```

The new tests cover:

- track wrapping and sampling;
- vehicle acceleration and resource consumption;
- full race completion and artifact saving;
- strategy candidate ranking;
- longitudinal calibration;
- telemetry quality invariants.

The original six tests continue to pass.

## Compilation

Executed:

```bash
python -m compileall -q src scripts
```

Result: success.

## CLI verification

Executed:

```bash
PYTHONPATH=src python -m apexsim.cli simulate-race --laps 2 --output /tmp/apex_cli_demo
```

Result: six classified finishers and saved race artifacts.

## Full demo verification

Executed:

```bash
PYTHONPATH=src python -m apexsim.examples.complete_sim_demo \
  --output artifacts/complete_sim_demo --seed 42 --laps 6
```

Produced:

- 6,169 telemetry rows;
- 18 race events;
- six classified finishers;
- lap and stint tables;
- a passing quality report with zero duplicate car-times, negative speed/fuel, invalid tyre health, backward distance steps or invalid positions.

The demo winner was `CAR_01 / Apex` in 529.5 simulated seconds. These values verify execution only; they are not claims about real motorsport performance.

## Determinism verification

Two three-lap runs with seed 123 produced byte-identical standings and telemetry files.

## Known boundaries

The delivered simulator is a V0 engineering vertical slice, not a team-grade simulator. In particular:

- car/aero/tyre constants are generic priors, not identified real team parameters;
- tyre temperature and health are latent proxies;
- the energy store is a generic bounded proxy, not observed real deployment;
- pit loss is currently a combined time block rather than a full pit-lane path;
- overtaking and dirty air are explicit heuristics awaiting calibration;
- safety-car behavior is a speed-state placeholder, not a full queue/restart procedure;
- source adapters still require the real-data upgrade tasks in `BUILD_BACKLOG.csv` before serious historical conclusions;
- no bulk historical telemetry is included;
- legal/data/branding restrictions must be reviewed before public or commercial use.

## Start command

```bash
cd apex_engine
./scripts/bootstrap_complete_sim.sh
```

Or follow `COMPLETE_SIMULATION_START_HERE.md` manually.
