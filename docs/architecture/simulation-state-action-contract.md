# Simulation state and action contract

- Contract version: `apex-sim-state-action-v1`
- Backlog scope: P0-03
- Kernel step: `VehicleDynamics.step`
- Default integration interval: 0.20 s

This document defines the current deterministic fixture contract. “Simulated” means a
state produced by the kernel. “Latent proxy” means a useful internal state that has not
been established as a directly observed real-car quantity. No field in this contract is
presented as confidential or team-grade telemetry.

## Ownership flow

```text
TrackMap + EnvironmentState + CarState
                  |
                  v
       ReferenceDriverPolicy.act
                  |
              Control
                  |
                  v
         VehicleDynamics.step
             /           \
     next CarState   StepDiagnostics
             |
             v
 RaceSimulator ordering, pits, flags and termination
             |
             v
 telemetry + laps + stints + events + standings + manifest
```

## Actions

| Field | Units/range | Truth class | Owner | Meaning |
|---|---:|---|---|---|
| `throttle` | fraction [0, 1] | simulated command | driver policy | Requested positive drive effort. |
| `brake` | fraction [0, 1] | simulated command | driver policy | Requested braking effort. |
| `steering` | normalized [-1, 1] | simulated proxy command | driver policy | Curvature-following steering proxy; not steering-wheel angle. |
| `ers_deploy` | fraction [0, 1] | simulated proxy command | driver policy | Requested share of the configured deploy-power ceiling. |
| `drs` | boolean | simulated command | driver policy; authorized by race/track context | Requested DRS activation. |

Controls are clipped at the dynamics boundary. Simultaneous positive throttle and brake
is rejected by the quality contract even though custom policies can construct it.

## Dynamic car state

| Field | Units/range | Truth class | Owner |
|---|---:|---|---|
| `time_s` | s, monotone | simulated | race clock |
| `lap` | integer >= 1, monotone | simulated | vehicle integration |
| `s_m` | m, [0, track length) | simulated | vehicle integration |
| `total_distance_m` | m, monotone | simulated | vehicle integration |
| `speed_mps` | m/s, >= 0 | simulated | vehicle dynamics |
| `fuel_kg` | kg, [0, capacity] | latent proxy | fuel model |
| `battery_mj` | MJ, [0, capacity] | latent proxy | generic energy-store model |
| `tyre_compound` | enum | scenario input/simulated transition | strategy and pit system |
| `tyre_age_laps` | equivalent laps, >= 0 | latent proxy | tyre model |
| `tyre_health` | fraction [0, 1] | latent proxy | tyre model |
| `tyre_temp_c` | degrees C | latent proxy | tyre model |
| `damage` | fraction [0, 1] | latent proxy | race system |
| `in_pit` | boolean | simulated | pit system |
| `pit_timer_s` | s, >= 0 | simulated approximation | pit system |
| `retired`, `finished` | boolean | simulated terminal state | vehicle/race system |
| `position` | integer [1, field size] | derived simulated | race ordering |
| `gap_ahead_m` | m or null | derived simulated | race ordering |
| `gap_to_leader_s` | s or null | derived simulated | race ordering |

`car_id` and `driver_id` are scenario identifiers. `pending_compound`, lap timestamps,
and metadata are orchestration state rather than physical observations.

## Context

| Context | Units/range | Truth class | Owner |
|---|---:|---|---|
| track position, curvature, gradient | m, 1/m, rise/run | synthetic or reconstructed input | `TrackMap` |
| DRS allowance | boolean by track sample | scenario input | `TrackMap` |
| air and track temperature | degrees C | scenario input | weather schedule |
| rain intensity, standing water, surface grip | normalized [0, 1] | scenario proxy | weather schedule |
| wind speed/direction | m/s, rad | scenario input | weather schedule |
| flag | enum | scenario input | race-control schedule |
| gap and DRS eligibility | m, s, boolean | derived simulated | race simulator |
| car parameters | SI units documented in `CarParameters` | configurable generic prior | scenario configuration |
| driver parameters | normalized traits plus seconds/seed | configurable proxy | scenario configuration |

## Diagnostics

`StepDiagnostics` reports acceleration (m/s²), forces (N), lateral acceleration
(m/s²), tyre wear increment (fraction), fuel burn (kg), energy delta (MJ), speed
limit (m/s), effective grip (dimensionless), dirty-air factor (dimensionless), and DRS
state (boolean). These values are simulated explanations of a kernel step, not observed
ground truth.

## Required invariants

- time, lap index, and total race distance never move backward;
- speed, fuel, pit time, tyre age, and resource capacities remain non-negative;
- fuel and battery do not exceed configured capacities;
- tyre health and normalized controls remain within their declared ranges;
- a row cannot be both retired and finished;
- terminal and identity fields remain coherent per car;
- no duplicate `(car_id, time_s)` samples or invalid race positions are emitted;
- a failing invariant aborts artifact promotion with the earliest named diagnostic.

## Known boundary

The V0 kernel uses generic priors, simplified point-mass dynamics, proxy tyre and energy
states, and a combined pit-loss block. Calibration or real-world accuracy is outside this
contract and requires the later maturity gates.
