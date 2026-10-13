# Engineering target for APEX

The intended outcome is a research simulator that a motorsport engineering team
can evaluate against a concrete decision problem. Team interest is an aspiration,
not an established result or a guarantee. The current production kernel remains
R0, with a separately reviewed scoped R1 research foundation.

## What must earn trust

- Recorded-control replay: reproduce held-out sections, laps and stints with
  explicit physical/resource constraints and errors against strong simple baselines.
- Useful uncertainty: evaluate coverage under track/regime shifts, expose missing
  inputs, detect unsupported conditions and provide tested fallback behavior.
- Decision value: compare strategy counterfactuals and policies against independent
  optimization references, reporting regret, runtime and constraint violations.
- Stable imagined dynamics: validate complete closed-loop rollouts, recovery and
  planner exploitation before learned components influence race strategy.
- Reproducibility: preserve immutable inputs, truth labels, parameter origins,
  model weights, versions, split boundaries and executable verification.

The question for each component is: which engineering decision does it improve,
on what held-out evidence, and where does it fail? Completing a backlog row or
training a larger neural model cannot answer that alone.

## Public-data limits

Public timing and telemetry can support reproducible descriptive studies and
historical replay. They do not identify proprietary tyre forces, slip, measured
wheel energy, detailed aero maps or every driver/car effect. APEX keeps measured,
reconstructed, proxy, prior and unknown quantities separate. Agreement with an
internally computed proxy cannot establish agreement with an unavailable sensor.

Future authorized engineering data can strengthen calibration within the same
contracts. No confidential access, team partnership, live race deployment or
proprietary-model equivalence is implied by the current repository.

## Reviewable proof package

A credible evaluation should contain a reproducible run, input rights/provenance,
frozen development and untouched benchmark boundaries, mathematical/model cards,
per-regime errors and uncertainty, baseline comparisons, replayed inference
artifacts, compute/runtime requirements and an honest failure analysis. An
independent reviewer should be able to reproduce the claims and reject weak ones.

## Current dependency order

R026 tests transfer to seen and unseen circuits with frozen forecasters. R029
track reconstruction is the next dependency-ready P0 for vehicle calibration.
R027/R028 remain pending P1 explanation and counterfactual research. Historical
replay and closed-loop stability follow their existing backlog dependencies.
Tyre/fuel/ERS validation, stochastic full-field behavior,
strategy regret and world-model planning require their later evidence gates.

The [live maturity status](maturity-status.json),
[research backlog](../research/research-backlog.csv) and
[Master Build Guide](../../00_MASTER_BUILD_GUIDE.md) remain authoritative.
