# ADR 0001: Build the platform first as an evidence consumer

- Status: accepted
- Date: 2026-08-28
- Backlog scope: P0-04, P0-05; preparatory surface for P9-01 and P9-04

## Context

The APEX roadmap places the finished replay and strategy product in P9, after the
simulation and planning gates. The project also needs a usable API and a high-quality
interface during development. Building an interface that implies mature predictive
capability would violate the maturity model and could hide weak evidence behind polish.

## Decision

The first platform release is an R0 evidence consumer and deterministic-preview runner.
It may:

- queue bounded synthetic V0 race previews;
- replay completed artifacts through a versioned read API;
- display track, telemetry, standings, quality checks, and provenance;
- identify every visible output by its immutable run ID;
- label proxy and simulated quantities explicitly.

It may not claim historical calibration, real-world predictive accuracy, strategy
optimality, durable distributed execution, or P9 completion. Its in-process background
task runner is a local-development boundary, not the production execution architecture.

## Consequences

The interface becomes useful immediately for inspecting evidence and catching broken
artifact contracts. Later model, planner, uncertainty, authentication, durable queue,
and deployment capabilities can be added behind the `/api/v1` contract only after their
own gates pass. The platform must continue to expose limitations rather than smoothing
them away.

## Rollback

The platform is isolated in `apexsim.serving` and packaged static assets. Removing the
API command and web package does not change the simulation kernel or its artifacts.
