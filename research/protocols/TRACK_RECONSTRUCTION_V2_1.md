# R029 v2.1: observed holdout boundaries and rigid shape registration

Preregistered2026-10-19 after b9a187e, BEFORE inspecting any public holdout geometry
metrics. V2 completed Bahrain internally, then stopped extracting Monza; its
all-case artifact was not emitted and no test XY/curvature outcomes were inspected.
Source-only auditing identifies two unsupported anchors: Monza2023 driver4 lap10
end and lap11 start. The other22 test laps pass strict v2 source extraction.
V1 and strict v2 failures remain visible; neither is retroactively passed.

This extension retains the EXACT64-lap v2 cohort, six candidates, training and
validation data, all positional/curvature/coverage/sensitivity gates and numerical
tolerances. No lap is replaced, no native gap limit is increased, no source field
is imputed. Development-selected weights/configurations must equal those already
sealed in the v2 development artifact. No test-dependent smoothing or selection.

## Boundary observation rule

Training and validation retain the original two supported <=.75s timing anchors,
raw closure<=30m and all other source rules. Thus the complete training shape and
closure are supported independently of partial test observations.

For TEST laps only, attempt each timing anchor under the same.75s bracket rule.
If unsupported, save its status/reason as UNKNOWN and OMIT the reconstructed
anchor, retaining EVERY actual interior native vertex. No extrapolation and no
linear fill across an unsupported bracket. Require the retained observation time
span to cover>=98% of the native lap duration, >=100 actual native rows, finite
strictly increasing time/XY, pos/OnTrack status, original mask identity/clean-dry
rules and nondegenerate chords. Record unobserved start/end durations and the
supported-anchor count. All interior intervals>.75s remain unsupported.

Raw timing-anchor closure is measured only when both anchors are supported;
otherwise it is null UNKNOWN. Save the observed endpoint gap separately; do not
call that a complete-lap closure error. The model's full-loop source coverage,
training raw closure, analytic closure and numerical convergence gates remain
unchanged. All retained native positions enter test errors. Coarse stencils still
require fully supported intervals and the original>=75%/100-target rule.

## Rigid evaluation gauge for complete and partial test traces

The original512-point chord-phase Kabsch initialization is retained. Partial
observations do not span an identical normalized full lap, so refine EVERY test
pose with exactly EIGHT rigid closest-curve correspondence steps after freezing
the training/validation-selected curve. Each step projects native points to the
fixed curve, solves a proper 2D Kabsch rotation/translation against those closest
points, composes the pose and records nearest-curve RMS. No scale, reflection,
deformation, point rejection or coefficient update. Require monotone squared
distance up to1e-6m RMS numerical tolerance. Save initialization/final transforms,
all eight RMS values and residual definitions. Training/validation alignment and
selection are unchanged. Source/shape fitting never uses test observations.

All reported test errors are CONDITIONAL REGISTERED-SHAPE errors after optimizing
the three rigid nuisance pose degrees of freedom. This is not absolute geographic
accuracy, online localization, or a measured physical road/curvature validation.
The supported raw baseline uses exactly the same registered test coordinates.

## Required additional verification and acceptance

Test a genuinely missing timing anchor without adding a fake vertex; reject
partial boundaries in training/validation, insufficient time coverage, invalid
native status and nonfinite input. Test proper rigid transforms and monotone
closest-curve RMS without changing coefficients. Exercise partial observations in
SIMULATED CLI/replay controls. Preserve explicit profile/protocol identity so
strict v2 remains reproducible. All v2 real-case gates, scientific replay, full
regression, independent saved-array audit and Python3.11/3.12 CI still apply.

R029 can close only on the separate passing v2.1 public study, without changing
thresholds after test metric inspection. Ancillary UNKNOWN fields, prior-data
reuse, source authenticity limits and absence of production/R3 promotion remain
exactly those documented for v2. This is a new declared observation method, not
evidence that either failed source assumption was correct.
