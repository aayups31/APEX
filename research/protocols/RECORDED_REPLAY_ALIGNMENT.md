# R033 recorded controls and observed engine-state alignment

Frozen 2026-10-31 before computing alignment coverage or selecting replay origins.
Public parsed-source **ADAPTATION**; no new vehicle calibration or promotion.

## A. Current state

Base 4927926005b663526b7fe9600557f44b205e68d0; 634 tests and main CI verified at
the previous checkpoint; the fresh baseline also passes634 tests in610.78s,
with two existing dependency deprecations before implementation.
R029 reference geometry, R030 native source cohort and R031 force/stability gate
are complete. R032 is developed first in this run. Foundation R1/kernel R0.

## B. Scope

Complete R033's causal alignment/coverage gate for recorded native throttle,
boolean brake and DRS, observed speed/RPM/gear and backward-associated position
over **all 88 previously frozen laps**. Keep every source row and exclusion.
Expose optional frozen offline reference geometry as conditioning, not online
location or measured heading. Produce typed inputs for the existing 150 R030
sections with independent control/state matching. No fitting, outcome-based
selection, new benchmark acquisition, full-car replay score (R034), driver or UI.

The public schema audit confirms **no measured steering angle, body lateral
velocity, yaw rate, tyre force, fuel or battery state**. These fields stay nullable
UNKNOWN. Brake is observed on/off, never fabricated pedal pressure or force.
Report full bicycle-state/control readiness separately: missing required fields
must prevent a complete observed bicycle initialization. R033's scoped
observational alignment gate cannot certify unavailable physical states.

## C. Immutable inputs and source semantics

Use accepted R030 source dataset seal
`2559478bf6a00a40f1850222035a86bf0046e14b857d1c81973513e209b3b9ab`, with accepted
R029 geometry seal `e22c1c6e0bf35a195120e47e6198c02d38549af4d51d38ef9f400c125d4ba684`.
All four original archives and native position tables are source-hash bound:
2023 Bahrain R01/Monza R14; 2024 Bahrain R01/Monza R16; drivers4/44.
Use R030 whole-event roles: train2023, validation2024 Bahrain, test2024 Monza.
These are reused development events, not permanently untouched evaluation.
Guard every source event identity before any Parquet/NPZ payload read.

Copy portable R030 dataset unchanged and exact original native position exports
from matching archive manifests; no cache unpickling or network needed. Each lap
uses its frozen native lap row and original start/end bounds. No lap substitution.
Source schema audit was performed before this protocol; no alignment coverage
was examined. [FastF1 source](https://github.com/theOehrly/Fast-F1/blob/main/fastf1/_api.py)
and [time reference](https://github.com/theOehrly/Fast-F1/blob/main/docs/data_reference/time_explanation.rst)
(read2026-10-31) document asynchronous car/position streams and source-time limits.

## D. Contract and algorithms

1. Verify source seals, reserved-event guards, native table hashes and frozen
   lap identity. Keep exact native car/position row IDs. Use half-open lap
   `[lap_start,lap_end)` membership so a boundary sample is never in two laps.
2. SessionTime must be finite/strictly increasing and agree with Date increments
   to1e-6s in each source stream; never use inaccurate `Time` as telemetry clock.
   This checks parser clock consistency, not absolute sensor timing accuracy.
3. Retain all native car rows within each frozen lap. Normalize Speed/3.6,
   Throttle/100; native Brake must be boolean; retain raw DRS/RPM/nGear.
   Known DRS {0,1,8} closed, {10,12,14} open, others UNKNOWN. Validate observed
   speed[0,120]m/s, throttle[0,1], RPM integer[0,30000], gear integer[0,8].
4. At each car timestamp choose latest native position in the **same lap**, never
   a future sample. Require Source=pos, OnTrack, finite XY, age<=.35s,
   preceding native position also within that lap and gap<=.75s. Do not cross
   gaps, drivers, events or laps. Convert XY from decimeters to meters.
5. Optional R029 distance/curvature reference at the exact native-position parent
   row is labelled `FROZEN_OFFLINE_REGISTERED_REFERENCE`. It is supplied offline
   conditioning, not measured chassis yaw/steering or causal online localization.
6. Joint observed readiness = valid source control + speed + RPM/gear + supported
   backward position. Separately report controls-only, engine-only and position
   coverage and missing model-state inventory. Every rejected row retains reasons.
7. Report covered interval duration using only adjacent native car rows <=.5s
   apart with ready left endpoint and valid next speed. Denominator is the full
   frozen lap duration, including missing prefix/tail. No bridging or filling.
8. Typed longitudinal input adapter uses only observed initial speed and the
   section's held throttle/DRS/time sequence. Speed after initialization stays a
   separate evaluation target, not an input or reset. Require original R030
   section identity/control provenance and all native rows ready; never convert
   boolean brake to calibrated force or invent steering for a bicycle adapter.

## E. Frozen acceptance gate

- Exactly88 frozen laps, four events, two tracks, two drivers; all native car rows
  accounted for. Controls-only and RPM/gear valid fractions **>99%** overall.
- Joint observed row coverage **>90%** overall and in each of eight event/driver
  groups; each lap **>85%**. Joint interval-duration coverage **>90%** overall.
  Denominators are all source car rows/full lap times, not prefiltered successes.
- Zero future-position matches, zero cross-lap matches, maximum accepted age
  <=.35s and previous gap<=.75s; report each violated/unknown field explicitly.
- All150 frozen R030 section input bundles match native source IDs/controls and
  initial speeds; supported fraction **>99%**, no replacement sections. Full
  bicycle measured-state readiness is reported independently and must never be
  promoted from missing fields, even when the observed coverage gate passes.
- Independent scalar backward-pointer audit reconstructs row associations,
  unit conversions, completeness masks and interval coverage. Exact source row
  matches and gate decisions; numeric values atol1e-9 for native conversions.
- Test synthetic async clocks, future perturbations, missing/unknown fields,
  duplicates/gaps/boundaries, native row lineage, protected events before payload,
  relocation, source tampering, resealed false summaries and adapter target
  independence. Scientific replay verifies fresh outputs and compact evidence.
- Public native result required for DONE. Smoke alone is execution evidence;
  fake public profile cannot bypass frozen source provenance or close R033.

Publish all per-lap/group failures and abstentions. A threshold failure yields
INCONCLUSIVE/REJECT, not a revised denominator or lower threshold. Full bicycle
readiness can be0% because missing steering/body states remain UNKNOWN; this
must be visible beside scoped observed coverage in the report and next-task handoff.

## F. Risks

FastF1 parsed channels may be reconstructed upstream. Date/SessionTime checks
cannot identify true physical latency or actuator delay. Offline geometry uses
full-lap registration. Source-age limits trade coverage for stale-position risk.
Observed RPM/gear do not identify torque, hybrid deployment or power-unit state.
No alignment result establishes predictive accuracy, intervention validity,
full-lap initialization or autonomous control. Reserved benchmarks remain untouched.

## G. Execution order

Commit protocol; verify R032 dependency; implement typed causal row alignment and
unit tests; push; immutable portable input/replay CLI and independent audit;
push; evaluate frozen public cohort; inspect all coverage; publish report and
evidence; full regression/CI; close only the declared R033 observational gate.
