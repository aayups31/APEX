# R049 per-car gap replay during neutralization and restart

Use previously opened OpenF1 development races and the nine verified
FastF1 race archives from the span audit. Keep fully bounded SC and
VSC episodes without intervening red flags or mode switches.

Join the most recent green same-lap snapshot before deployment,
the latest crossing snapshot inside the episode, and the first
green complete-lap snapshot after release. Require at least five of
the same drivers at each snapshot with known nonpit timing. In the
middle snapshot require the crossing itself inside neutralization.
Use green crossings within four minutes of deployment or release.
This permits short VSC episodes whose preceding timing line was
crossed under green. Select the common drivers deterministically,
prefer more common drivers, then closer snapshots. Treat any change
in observed driver order as an error opportunity and keep it.

For each held-out race and mode, derive scale factors for gap to
the matched cohort's earliest driver. Fit using medians across other
races, with a median across per-episode ratios within each race.
Ratios use the sum of individual gaps after scaling relative to the
pre-event sum. Compare against carrying the same gap through each
phase. Keep preserve-before as the fixed restart rule for VSC.
Require at least three scored races in each mode, no phase worse
than persistence, and an improvement in at least one phase per
mode. Check finite nonnegative gaps, a zero leader gap, unchanged
modeled order, and switch to green at release. Distinguish matched
timing-line replay from full trajectory or live control validation.
