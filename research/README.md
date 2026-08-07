# APEX Research Layer

This folder is the evidence and replication layer for the simulator.

## Contents

- `user_provided_papers/`: the two papers supplied for this build.
- `paper_catalog.json`: machine-readable research map.
- `references.bib`: bibliography starter.
- `PAPER_TO_CODE.md`: why each paper matters and where it enters APEX.
- `REPLICATION_STANDARD.md`: what counts as a replication, adaptation or inspiration.
- `GAME_VALIDATION_LATER.md`: pre-registered plan for future game telemetry.
- `protocols/`: experiment plans by research family.
- `experiments/`: templates for individual runs.
- `scripts/`: optional source-fetch helpers; third-party papers are not silently redistributed.

## Status vocabulary

- `REFERENCE_ONLY`: read and use as a modelling reference.
- `PLANNED`: no code yet.
- `PROTOCOL_DEFINED`: implementation/evaluation plan exists.
- `ENGINE_CROSSWALK`: the existing engine covers part of the paper’s structure but is not a reproduction.
- `RUNNABLE_STARTER`: a minimal faithful mathematical starter runs.
- `RUNNABLE_SURROGATE`: the topology/equations run with public or synthetic parameters, not confidential paper maps/data.
- `INTERFACE_IMPLEMENTED`: compatible contracts exist; the full learning result has not been reproduced.
- `REPLICATED`: reserved for matched data/protocol/results within declared tolerance.

Do not promote a status because the output looks plausible.
