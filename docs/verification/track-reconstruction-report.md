# R029 reference geometry reconstruction and source-support failure

## A. Outcome and baseline

**R029 INCONCLUSIVE**, 2026-10-19. The numerical geometry implementation passes
its tests, but the public study fails its preregistered source-support gate:
**14 of 24 selected laps contain native position gaps above 0.75 seconds**.
The decision is **REJECT_FROZEN_SOURCE_SUPPORT**. No real reference curve was
fitted, no public shape/curvature accuracy is claimed, and R029 is not DONE.
Research inventory remains **26/73 DONE**, build **13/66 DONE**, scoped research
maturity R1 and production kernel R0. R030 remains dependent on accepted geometry.

Baseline d695e29: fresh **508 tests pass in 246.42s**. Preregistration f1415e4
precedes geometry fitting and source-gap outcome inspection. Implementation
2f85bd3 and native-evidence audit 984c9fa are pushed directly to main.
Pre-existing user `artifacts/`, `output/` and `tmp/` remain untouched.

## B. Frozen scope, inputs and boundaries

The [frozen protocol](../../research/protocols/TRACK_RECONSTRUCTION.md) specifies
two-dimensional reference RACING TRACES for Bahrain and Monza, rather than surveyed
centerlines. Per circuit, the first three eligible 2024 driver 4 laps train shape,
three driver 44 laps select among three fixed candidates, and three 2023 laps per
driver form the final DEVELOPMENT test. These are previously inspected development
events, not the untouched benchmark. Original R021/R026 clean-dry masks are sealed
and source-bound. There is no fastest-lap selection or post-inspection replacement.

The four existing native FastF1 archives verify unchanged. Their previously
completed offline reports each reproduce **46 tables**, with zero network attempts
and no mismatches; those reports are retained as prior evidence, not described as
new offline rebuilds in this pass. The nine permanent whole-event benchmarks remain
excluded before native payload access. No new telemetry was acquired.

FastF1 3.8.3's installed `core.Telemetry` documentation specifies decimetre X/Y/Z;
the geometry workflow converts XY to metres. Native `SessionTime`, `Source=pos`
and `Status=OnTrack` remain explicit. Only the two supported lap-timing anchors
may be interpolated. Complete source traces require at least 100 native positions,
maximum bracket/interior gap 0.75s, timing agreement 0.1s, raw closure 30m and
nondegenerate chord distance. Provider-parsed positions may themselves contain
upstream reconstruction; archive hashes establish local consistency, not origin
authentication or survey quality.

## C. Implementation delivered

`reference_geometry` supplies periodic Fourier ridge curves, analytic heading and
signed curvature, monotone integrated arc station with a PCHIP inverse, global
lookup plus local nearest projection, and a raw-polyline positional control.
Circle/ellipse fixtures independently check units, length, signs, curvature,
coordinate transforms, normals, station inversion and structural closure.
The [equation map](../../research/equations/REFERENCE_GEOMETRY_V1.md) records
the exact loss, symbols, units and code/test crosswalk.

The study fits coefficients on training laps only; validation chooses among
(48,.05), (96,.05), (96,.5) harmonic/penalty candidates. Held-out full-lap rigid
pose registration concerns shape after alignment; no scale, reflection or
nonrigid warp is allowed. This is not online localization or absolute geographic
accuracy. Coarse 25m turning-angle curvature is labelled a PROXY. Three
leave-one-training-lap fits quantify sensitivity, not calibrated confidence.
These operations execute on synthetic controls; the failed public source gate
prevents invoking them for the frozen real cohort.

The shared `GeometryProvider` contract exposes station/XY/heading/curvature for
legacy and research geometry. Existing race sampling behavior is unchanged.
Research ancillary requests fail explicitly: road width, validated elevation,
official DRS zones, surveyed centerline and full pit route are UNKNOWN. Timing
projections for start/finish, sectors and pit observations are implemented and
tested, but no public annotations are claimed from this rejected run.

The added source-audit command inspects **all 24 selected laps before fitting**,
retains accepted and rejected outcomes, native parent-row/time gap intervals,
raw closure and complete selected-driver native position streams. Its sealed
portable verifier rebuilds every lap check from those saved streams and timing
rows. Even a fully supported source audit cannot close geometry accuracy.

## D. Public source results

| Event | Train supported | Validation supported | Test supported | Largest native gap (s) |
| --- | --- | --- | --- | --- |
| Bahrain 2024 R01 | 1/3 | 2/3 | — | 1.300 |
| Monza 2024 R16 | 2/3 | 2/3 | — | 1.081 |
| Bahrain 2023 R01 | — | — | 0/6 | 1.320 |
| Monza 2023 R14 | — | — | 3/6 | 1.281 |

There are **33 lap-level interval instances above 0.75s across 14 rejected laps**,
representing 28 distinct event/time intervals. Failures occur in
training, validation and test roles at both circuits. The very first training
lap, Bahrain 2024 driver 4 lap 15, contains an 0.820s gap; the original reconstruction
command stops there before fitting. The audit then collects the whole cohort
without replacement. Five intervals occur at identical session timestamps for
both drivers, consistent with common feed gaps; this does not prove their cause.

All24 selected laps have raw timing-anchor closure below 30m (range approximately
0.161–10.220m) and 324–402 interior native samples. Good endpoint closure does not
repair missing interior support. The failed condition is source gaps, not a
demonstrated Fourier shape error. Consequently public XY/curvature residuals,
candidate rankings, sensitivity, fitted lengths and shape acceptance are
**NOT_EVALUATED**, rather than zero or passing. Synthetic periodic closure is
not evidence for missing real observations.

Independent NumPy auditing of the saved native streams uses integer-nanosecond
window boundaries and reproduces all 24 maximum gaps, all 33 rejected intervals,
the10/14 support counts and raw endpoint closure. It imports no geometry or
source-extraction implementation. Sealed evidence includes those records and
full archive manifests with query, identity, environment and source/terms notes.

## E. Verification, evidence and reproduction

- **12 geometry tests pass in 58.77s**: analytic controls, rigid frame invariance,
  invalid inputs, native lineage, unknowns, protected-source refusal, held-out
  shape isolation, portable refit, tamper detection and false promotion refusal.
- **3 source-audit tests pass in 17.04s** after the portability correction: exact gap localization, complete native
  snapshot replay, supported/rejected cases, immutable output and tamper refusal.
  Explicit synthetic fixtures stub archive verification only inside these tests.
- The geometry checkpoint passes **520 full tests in 345.39s**. The audit-inclusive
  suite passes **523 tests in 240.69s**, with two existing dependency deprecation
  warnings. Lint and diff checks pass. All six synthetic cars finish six laps,
  and every race quality check passes. The research preview also runs, retaining
  its existing synthetic-ridge conditioning warning.
- [Geometry implementation CI](https://github.com/aayups31/APEX/actions/runs/39357133885)
  passes Python3.11/3.12, including the new simulated geometry replay step.
  SIMULATED smoke cannot close public research acceptance.
- The public source-audit verifier passes from native snapshots without original
  source caches. An independent comparison confirms all snapshot columns against
  eight original position streams and the identity/timestamps of 24 native laps.
  No geometry fit or task/maturity promotion is recorded.

The first audit CI found a test-only pandas duration storage-unit mismatch
(`timedelta64[s]` versus `timedelta64[ns]`), with 522 other tests passing in each
matrix. Commit 371b638 corrects the assertion to require exact integer-nanosecond
snapshot values and identical replayed decisions, without requiring pandas'
inferred storage dtype. Scientific code and source acceptance are unchanged.
[Corrected implementation CI](https://github.com/aayups31/APEX/actions/runs/39358141650)
passes both Python 3.11/3.12 matrix jobs, including all tests and artifact steps.

Source-audit summary seal:
`f653df6113d34a947ebaaf7c20fd7bcc48a258c7e2a64a008e0bbef1dbc47598`.
Artifact manifest seal:
`7a06311c032af17700939f46160df27bfe6fcd5df6be288f63c774e67519ea4a`.
Bulk native snapshots remain ignored in `.cache/r029-source-audit-research-20261019`;
compact [evidence JSON](track-reconstruction-evidence.json), the report and
[model/data run card](../models/reference-geometry-v1.md) are version controlled.
The run card supplies exact fresh-output commands for the source audit,
reconstruction, scientific verifier and simulated smoke.

Rollback is a revert of the implementation/audit commits. Frozen prior studies
and the production simulator's existing numerical sampling are unchanged.

## F. Limits and engineering relevance

This pass delivers executable geometry mathematics and a reproducible negative
source result. It does not deliver an accepted public circuit, calibrated vehicle,
closed-loop real lap, validated world model or evidence of team interest.
Full Master Build Guide 9.2 track promotion remains open. Width, elevation,
official zones and full pit geometry require further evidence even after shape
support is resolved. Whole-lap pose alignment, small samples, development-data
reuse and proxy curvature further limit any eventual shape result.

The numerical implementation passing and the public source gate failing are
separate findings. No threshold was loosened, no missing segment was silently
filled, no failed lap was replaced and no permanent benchmark was inspected.

## G. Next dependency

**Continue R029 before R030.** Preserve this rejected v1 experiment. Design and
preregister a separate source-support-aware method that combines observed pieces
across training laps, represents unobserved segments and bounds interpolation
uncertainty explicitly. Assess source availability before freezing a new cohort;
retain the current cohort's negative result and disclose all development reuse.
Freeze new metrics/support rules before geometry outcomes, and evaluate on a
separate development holdout with all failures reported. Do not simply increase
the gap limit or swap the failed laps to make v1 pass.

Only accepted reference geometry can unblock R030 longitudinal calibration,
followed by lateral dynamics and recorded-control replay. R027 explanation
faithfulness and R028 feasible counterfactuals remain TODO P1 tasks. This pass
stops at the frozen source failure with its implementation and evidence retained.
