# R041 relative outlap pace forecast

Use the corrected v24 cohort and the completed outlap comparison
defined in the seven-race coverage audit. Extend the identical
clock and peer filters to every supported development race. Keep
all cases, including cases without an eligible outlap.

Refit the nomination/practice ridge with two extra values. The
first is the difference between the subject's outlap duration and
the median duration of eligible peers. The second indicates
availability. Use two zeros for unavailable observations. Preserve
whole-race exclusion, original training weights, three-lap forecast
bounds and every original acceptance gate. Score against the frozen
nomination/practice ridge and report the seven recurring failures
separately. No exact-exit feature or parameter sweep.

Continue this direction only if the full pass count improves and
at least one recurring failure passes. Fresh confirmation requires
a complete development pass.
