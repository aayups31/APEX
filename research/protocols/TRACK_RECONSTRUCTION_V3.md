# R029 v3: source-coherent curvature targets and additional confirmation laps

Preregistered2026-10-19 after9edf0e8. V2.1 completed all64 laps and is REJECTED:
23/24 test laps pass; Bahrain2023 driver44 lap9 has coarse curvature MAE
.003052/m above the frozen.003/m limit. Its XY/geometry/coverage/sensitivity and
all other test gates pass. That failed result and the exact thresholds remain
unchanged. This protocol is a separate declared target-quality experiment.

Source-only diagnosis finds two nearly180-degree chronological reversals around
native position rows17582–17584: about19.2m backwards then18.7m forwards. All
points lie close to the reference trace, but the chronological turning proxy has
two spikes around.166–.168/m on that portion of the trace. The cause is UNKNOWN;
even if real vehicle motion, such a cusp/reversal is not forward road/reference
curvature. Native XY positions are NEVER removed from positional evaluation.

## Frozen estimator and original evidence

Retain EXACT v2/v2.1 training/validation laps, all six candidates, selected weights,
source archive/mask bindings, proper rigid evaluation gauge, all.75s time/bracket
limits, partial-test>=98% time rule, raw training closure, geometric gates,
position errors, curvature error thresholds, support fractions/counts, donor
coverage and descriptive sensitivity limits. No smoothing/weight/gate retuning.
Coefficients and selected candidates must equal the already sealed development
artifact. Prior v1, strict v2 and v2.1 failures stay visible and reproducible.

## Source-only derivative support

For consecutive native/timing-anchor displacement vectors d_i, compute
`c_i=dot(d_(i-1),d_i)/(norm(d_(i-1))*norm(d_i))`. An angle of at least90 degrees
(`c_i<=0`) makes BOTH adjacent intervals unsuitable for a forward curvature
stencil. This is a declared conservative regular-forward-trace assumption, not
a measured physical limit or an inference from model residuals. Combine that
mask with existing native time support. Exclude any +/-25m curvature stencil
crossing either kind of unsupported interval. Keep the fixed>=75%/100-target
requirements, with the denominator still ALL candidate centers. Do not screen
by predicted curvature, residual magnitude, driver identity or lap outcome.

Retain every native position for XY/max/backward metrics. Retain time-only mask,
native turning cosines, derivative support mask, the unfiltered chronological
proxy as a DIAGNOSTIC (not an accepted target), and the accepted/UNKNOWN target
mask. Unsupported targets/model matches remain NaN UNKNOWN. Coverage of fitted
shape still counts observed positive supported station intervals across ten
training laps. Data rows are not relabelled bad merely for model disagreement.

## Confirmation cohort and decision

Retain ALL24 v2.1 test laps as retrospective tests. Add the next SIX eligible
laps per driver/event (mask positions[9:15]), whose geometry metrics have not
been inspected. Frozen test selection becomes original-mask positions[3:15].

| Event | driver4 test laps | driver44 test laps |
| --- | --- | --- |
| Bahrain2023R01 | 7,8,9,19,20,21,22,23,24,25,26,27 | 6,7,8,9,10,11,14,15,16,17,18,19 |
| Monza2023R14 | 9–20 | 5–16 |

Total88 laps:20 training,20 validation,24 retrospective test,24 additional
confirmation test. Report both test strata separately and every lap individually.
Do not replace any test lap. ALL48 test laps must pass ALL original v2.1 numerical
gates under the new source-only derivative support, including unchanged.003/m
MAE/.015/m p95 proxy tolerances and>=75%/100-target coverage. Both circuits must
pass full shape coverage/sensitivity/numerical tests. No decision from merely
pooling away a failed lap. Additional tests use the same development events and
are not independent population events or untouched permanent benchmarks.

Add a hand-built reversal fixture proving source-only mask behavior, unchanged
native XY scoring, explicit unfiltered diagnostic retention and valid-target
abstention. SIMULATED CLI controls combine missing intervals, a missing boundary
and a reversal. Refit/replay ALL arrays and decisions, audit saved real outputs
independently, and run full regression/lint/Python3.11/3.12 CI before R029 DONE.

R029 closure remains scoped to source-supported reconstructed reference shapes,
not surveyed centerlines, absolute accuracy, vehicle/world-model validation or
production/R3 promotion. Ancillary UNKNOWN fields and prior research limitations
remain explicit. If the new confirmation fails, preserve the failure; do not
change gates after inspection.
