# R041 known peer stint forecast

On the v24 cohort, retain the nomination/practice ridge forecast as fallback.
For the current driver seek another driver in the same race with a
completed twelve-age window matching the current compound and all twelve
tyre ages. Require every native lap end in the peer window to precede or
equal the registered forecast clock. Estimate subject-minus-peer pace
using the v26 same-phase matching rule and at least six distinct earlier
same-compound pairs. Exclude the subject's current stint and the peer's
reference stint. Require control laps to finish strictly before the
subject's forecast window starts. For an eligible peer, add the median
driver offset to each of its three observed target-age lap times. Take a
median across eligible stints per peer, then a median across peers per
target age and enforce the same two-second change bound. Use the estimate
on all supported cases. No blending, tuning or case removal.

Publish each contributor and support counts. Replay the complete original
two-label gates. For diagnosis only, optionally replace supported cases
with their bounded true target laps to show remaining failures on a
favorable counterfactual. Races failing with zero supported cases establish
a hard limit on this fallback design. Only an actual full development pass
permits fresh confirmation.
