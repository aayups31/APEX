# Observed public fields verification

- Validation date: 2026-10-08 (America/Toronto)
- Branch: `main` (direct commits authorized by the user)
- Parent: `6e48ab6353d1c4b12a37bf9b03b62ed4706e6198`
- Scope: P1-07, replacing fabricated public observations
- Maturity before/after: R0; model promotion gates remain open
- [Usage and field mapping](../data/observed-tables.md)
- [ADR 0003](../architecture/adr-0003-observed-public-fields.md)

## A. Current state and baseline

The tracked baseline is the completed P1-06 implementation. The earlier P1-07
draft contained only an unconnected mapper and an ADR; it had no completion evidence.
The reference demo was rerun under `.cache/observed-fields-baseline-20261008`:
all five typed public tables and event-grouped splits passed and were inspected.
Dataset SHA-256 is `2a69a7b1e095df0af05dbe7f7ccb0991db9f8e095f79c9760e5524f05db694ab`;
split SHA-256 is `166fb5ba4eadf079bce178e9320dc1c30881578acf05eba6e3c77696c7dddd15`.
The pre-existing untracked `artifacts/` directory remains untouched.

The default local pytest temporary directory cannot be created inside the current
Windows sandbox. A focused failure reproduced the setup error, and a native archive
case passed with `--basetemp` inside the workspace. Windows async API tests also
hang while creating a local loopback socket in the sandbox; a traceback isolated
the wait to asyncio socketpair setup. With local socket access and workspace
temporary files, the unchanged baseline passed **212 tests** (4 existing warnings,
77.57 seconds). Local full-suite commands use new ignored `.cache` directories
and the required local socket permission; no application workaround was introduced.

## B. Scope and dependencies

P1-06 is DONE and supplies explicit provider linkage and the timestamp audit.
P1-01 supplies typed nullable tables and P1-02 through P1-05 provide frozen archives.
This milestone connects native source fields to those table contracts and retires
the public dense CSV path that invented observed context. It does not calibrate
physics, resolve all provider semantics, create a multi-event benchmark or train a
world model. Research equation-fidelity/oracle gates R012–R014 remain open.

## C. Source-of-truth inputs

The master guide's truth labels, data contract, artifact immutability and completion
requirements; public-tables-v1; source-manifest-v1; the three archive verifiers;
the explicit British 2024 qualifying link; and P1-06's lap-start disagreement evidence
govern the conversion. Field semantics were checked against installed FastF1 3.8.3
documentation and the [official OpenF1 fields](https://openf1.org/docs/).

## D. Implementation and execution order

1. Recheck all frozen archives and the explicit session mapping.
2. Map native lap/weather/race-control observations to canonical units and nullable
   fields, retaining source-order references and per-field truth labels.
3. Derive FastF1 observed stint extents and reject compound conflicts; quarantine
   incompatible OpenF1 stint ranges and preserve ambiguous lap context as unknown.
4. Build separate source-linked provider bundles with conversion reports and hashes.
5. Retire unsafe public CSV converters and reject their saved inputs before training;
   verify synthetic input still runs through the existing pipeline.
6. Verify adversarial fixtures, offline real-data conversion, artifact readback,
   regression checks and GitHub checks before marking the milestone complete.

## E. Stopping gate

Both real provider bundles must load through the existing dataset reader and pass
schema, source-lineage, unit, truth-label and cross-table checks. Source hashes must
remain unchanged and the offline run must attempt no network access. Missing weather,
unsupported compounds, incomplete pit boundaries and disputed stint associations
must remain explicit. Known observations must retain source values after declared
unit conversions. Legacy ingestion and old public dense inputs must fail before
being used for training. Relevant tests, the full suite and lint must pass.

## F. Risks and limits

The acceptance case is one qualifying session. Provider field values may themselves
be reconstructed; schema validation does not establish physical accuracy or online
availability. Different lap clocks and start definitions remain visible. The canonical
inclusive stint contract is incompatible with overlapping native ranges; quarantining
them reduces usable coverage and requires a future semantic investigation. Missing
pit times do not prove non-pit behavior. Neither a dense feature builder nor a new
pit-occupancy model is introduced. Retiring the legacy ingestion path is an intentional
API change documented in ADR 0003; old artifacts remain untouched.

## G. Acceptance evidence and next work

Implementation checkpoint: 37 integrated mapping, migration and pipeline tests passed
(75.06 seconds), including synthetic end-to-end training. Ruff and Airflow wrapper
compilation passed. Both real provider bundles have been read and inspected:
368 laps and 85 weather records per provider; FastF1 has 101 stints and 46 messages,
OpenF1 has 1 accepted stint and 54 messages. No field is labelled IMPUTED.

The enclosing conversion completion check, full regression suite and GitHub checks
are still pending. P1-07 remains IN_PROGRESS until that evidence is recorded.
