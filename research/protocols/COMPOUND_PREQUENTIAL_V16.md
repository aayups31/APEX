# R041 within-race forecast error feedback

Use v13 nominated outer-race forecasts as the fixed model. Test whether errors
from completed windows of other drivers in the same race and on the same
compound predict a common error in an upcoming window. V10 measured absolute
field pace drift. This study measures errors relative to forecasts already
adjusted for their individual histories and compound nominations.

Reconstruct native target end times for each sealed v11 comparison. Verify the
three native target paces against the stored targets. To supply feedback a
window also needs a subsequent retained lap in its own stint. Release its error
only after this witness lap finishes, strictly before the new forecast. The
witness establishes that the target window has concluded in the stint
interior. Ignore the new subject's own driver and all other races. With several
reference comparisons for one current window, average their median lap errors.
Use the latest available unique window of each eligible peer, then the median
across peer drivers. Shrink by n/(n+3), where n counts those drivers. Apply this
same signed offset to all three base forecasts and clip each to its original
prefix plus or minus two seconds. Without feedback, replay v13 exactly.

Keep the original forecast times, 28 source races, 392 comparisons, respective
label definitions, baselines and race gates. Keep validation outcomes for
scoring separate from feedback at prediction time. Reconstruct decisions,
report contributor counts and zero-support races. Also evaluate an explicitly
unusable diagnostic that predicts observed laps perfectly on supported cases
and retains the fixed base forecast elsewhere. Its irreparable zero-support
errors diagnose the reach of the proposed correction. This diagnostic is
never a candidate. No fresh confirmation unless the primary clears all gates.
