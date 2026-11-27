# R041 forecast of the future field shift

The v28 future-field diagnostic reduced macro pace error. Test how much
of that information can be recovered at the original clock. Freeze both
the v28 inputs and the downstream diagnostic ridge checkpoints. For each
outer test race, fit a six-output ridge on other races' 18 causal field
features and their six future field summaries, including the empty groups.
Use v24 event/window weights, training-only standardization and ridge
penalty 10. This predicts a typical summary across possible future fields.

In each group constrain predicted log count to the interval from zero
to the current log count, and constrain median absolute deviation to be
nonnegative. Use three zeros when the current group is empty. A future
observation cannot be matched without a current peer. Use the estimate
in place of all six future inputs to the frozen, race-excluded downstream
checkpoint. Keep the same three-lap bounds, cohort and qualification test.
Record each forecast and compare race-averaged field-shift absolute error
on cases with a verified match against predicting zero and extrapolating
the current three-lap change over nine laps. Future peer availability is
used only to score this auxiliary metric. All 393 cases enter R041.
