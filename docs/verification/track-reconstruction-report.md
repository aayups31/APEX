# R029 reference geometry reconstruction

## A. Baseline
2026-10-19,d695e29. Fresh508 tests pass246.42s. Scoped researchR1/kernelR0;
research26/73,build13/66 DONE. Existing user directories remain untouched.

## B. Scope
Two development circuits, training-only periodic reference traces, explicit
coordinate registration, held-out position/coarse-curvature checks and unknowns.

## C. Inputs
Verified2024/2023 Bahrain/Monza archives and sealed R021/R026 eligibility masks.
The [frozen protocol](../../research/protocols/TRACK_RECONSTRUCTION.md) defines
all selected laps, candidate settings and stopping gates before geometry fitting.

## D. Implementation
Periodic Fourier reference curves, monotone arc station, analytic curvature,
closest projection, registered source inputs and labelled static annotations.

## E. Stopping gate
Both public cases pass all frozen gates; immutable artifacts reproduce; shared
sampling contracts, numerical/source-boundary tests, regression and CI pass.
R029 remains IN_PROGRESS until those gates are satisfied.

## F. Limits
Reference racing trace rather than surveyed centerline; registered shape only;
coarse held-out curvature is a proxy; physical width/elevation/official DRS and
complete pit-lane geometry remain unknown. No production/R3 promotion.

## G. Next
Finish R029, then earliest P0 R030 longitudinal calibration. R027/R028 remain open.
