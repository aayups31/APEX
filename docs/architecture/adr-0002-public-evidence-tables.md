# ADR 0002: Separate public evidence tables from model feature CSVs

- Status: accepted
- Date: 2026-09-07
- Scope: P1-01, P1-08

## Context

The existing canonical CSV is a dense model-input contract. Its public adapters
still use placeholders and independently sampled data. Requiring the same dense
representation for raw evidence would force unsupported observations into constants
before the alignment and placeholder-removal gates are complete.

## Decision

Add a separate versioned Arrow/Parquet evidence boundary with explicit nullable
fields, field units, UTC timestamps and per-value truth labels. Require immutable
source-linked bundles and validate table relationships before publishing their
completion manifest. Keep Parquet support in an optional data-contracts extra.

Freeze explicit event-grouped session assignments against exact dataset hashes.
Allow the training pipeline to opt into them through paired dataset/split paths,
requiring complete telemetry session coverage before fitting the train-only scaler.
Retain the legacy CSV/synthetic path for existing experiments. No simulation kernel,
physical parameter or learned component is promoted by this work.

## Consequences and rollback

Public evidence can represent missing observations honestly before P1-06/P1-07.
Provider-to-table adapters and a real frozen corpus remain future gates. Contract
validation is distinct from source completeness or predictive validity. Any field
or unit change requires a new schema version and migration.

The new data modules, commands and optional config fields can be removed together
without changing sim_core. The branch parent retains the foundation/platform milestone.
