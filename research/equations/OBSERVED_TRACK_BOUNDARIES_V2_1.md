# Observed boundaries and rigid evaluation pose v2.1

This extends [observed support](OBSERVED_TRACK_SUPPORT_V2.md) under the separate
[frozen protocol](../protocols/TRACK_RECONSTRUCTION_V2_1.md). V1 and strict v2
source failures are retained. No public holdout geometry errors selected this
extension, its cohort, weights or thresholds.

Training and validation still require both supported timing anchors and raw
closure<=30m. For a test boundary, reconstruct an anchor only with a valid native
bracket<=.75s. Otherwise save UNKNOWN with its reason and omit that anchor.
Retain every interior native point and require>=98% observed lap-time span.
Save native row parents, supported-anchor count, unknown boundary status, missing
start/end durations and observed time fraction. Whole-lap raw closure is null
when either timing anchor is unknown. Observed endpoint separation is separately
labelled and never substituted for a complete-lap closure measurement.

## Proper rigid closest-curve pose

Let raw test points be X and the current registered points Z=XR+t. Project Z to
nearest points Y on the frozen training/validation-selected curve. With centered
Z/Y and `Z'Y=U Sigma V'`, compute

```
Q = U diag(1,det(UV')) V'
b = mean(Y)-mean(Z)Q
R_new = R Q
t_new = t Q+b
```

Use exactly eight steps after the512-correspondence Kabsch initialization, for
every complete or partial test lap. Record native nearest-curve RMS before and
after every step; allow at most1e-6m numerical increase. Scale remains1 and the
rotation determinant+1. No native point is rejected; no coefficient or candidate
is updated. Native XY, supported raw baseline and curvature proxy all share the
same final rigid coordinate gauge. The test-isolation checks require identical
coefficients and selection despite changes in held-out XY/missingness.

The reported error is CONDITIONAL REGISTERED-SHAPE error after optimizing the
three rigid nuisance pose degrees of freedom. It is not absolute georeferencing,
online localization, surveyed road accuracy or a held-out vehicle-control replay.
The fixed source plane, positive-left normal and signed curvature remain v1.

Code: `position_laps.extract_position_lap(... observed_boundaries=True)` is
permitted for test observations only; `supported_geometry.refine_rigid_pose`
implements the proper rigid steps. Independent tests omit a genuine timing anchor
without adding any vertex, reject insufficient duration/training relaxation, and
check monotone rigid alignment of a transformed partial ellipse without modifying
coefficients. SIMULATED v2.1 CLI controls include partial observations and cannot
claim real-source acceptance. Portable scientific replay preserves protocol/profile
identity, missing-data masks, all poses, all arrays and all frozen decisions.
