# R041 pit-exit cohort and robust pace forecast

The v23 timing panel found a one-lap offset at some reported OpenF1 stint
starts. Rebuild the full previously opened development inventory from the
verified native archives. Do not open any additional race timing or outcomes.

## Cohort

For an OpenF1 dry-tyre stint after lap one, shift its age anchor forward one
lap only when the reported start is explicitly not an out-lap and the very
next lap is explicitly an out-lap, with ordered native start clocks. Both
rows must be inside that stint's reported lap interval. The out-lap remains
excluded, so any corrected retained lap must follow it by lap number and
native clock. Keep the supplied age prior, reported stint interval, native
driver and compound identities, physical lap masks and fuel correction.
Keep the reported age convention when the exact pattern is unavailable.
Report other boundary patterns separately. FastF1 keeps its native TyreLife.

Recompute disjoint 12-consecutive-age blocks for every earlier/later
different-compound stint pair. Keep the first three current laps, the last
three current targets, and the original completed-reference clock and
history requirements. Recompute both labels with the existing strict
0.15-second crossover margin. Independently enumerate native eligibility and
pair denominators, compare physical laps and cutoffs, and record added and
removed blocks, reindexed blocks and both label transitions for matching
physical current windows. Reproduce the original cohort alongside the
corrected audit before fitting.

## Fixed forecasts

Use the corrected nomination inventory and the sealed pre-race practice
summaries. Refit the v21 nomination/practice ridge control and the v23 native
telemetry ridge using the rebuilt age histories. Re-extract native telemetry
at the exact driver/lap clocks. Reuse a sealed v23 snapshot only when its query
covers the full input interval. If a new interval or driver is needed, acquire
it only for an already-opened race, using an immutable bounded receipt. The
three native observation groups and their support masks remain as in v23.

The primary candidate uses the same telemetry features, training-only
weighted standardization and weights as the v23 ridge. Fit one Huber regression
per future lap offset. The residual loss is quadratic up to 0.45 seconds and
linear beyond it, with a ridge penalty of 10 on the standardized coefficients
and a free intercept. This limits the influence of large pace changes that
remain in nominally clean laps. Solve to a scaled gradient tolerance of 1e-7
or fail closed. Independently verify the gradient and replay the checkpoint.
Both controls and the primary retain the original per-lap two-second bound.

Train with whole-race exclusion, score both contrasts from each single
three-lap forecast and replay every original v12 gate independently. Report
every supported and unsupported race, all three controls/candidate results
and the comparison to v21/v23 on the old cohort. Keep fresh confirmation
locked unless the primary independently passes all development gates.
Passing development alone does not accept a candidate or promote production.
