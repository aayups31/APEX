# R041 multi-point traffic proxy

Test whether timing inside the lap adds forecast information beyond the
start/finish line. Use the frozen corrected cohort and already opened
native timing archives. No additional races.

Use the three current prefix, three reference prefix and three reference
target laps. For each subject lap with reconciled sector splits, reconstruct
the first and second sector crossings from its lap start and elapsed splits.
At each timing point, find the most recent strictly earlier crossing by
another driver at that same point within ten seconds. A peer split is
eligible only if its entire lap finished by the case forecast cutoff.
This allows full-lap consistency checks on archived split data without
looking past the forecast clock. At the finish, use all archived timed
laps and the same strictly earlier rule. Finishing order at a timing
point is a proximity proxy, including traffic on other race laps.

For each of the three windows and each timing point compute mean capped
gap, share at or below 1.5 seconds, and last minus first gap. Use ten
seconds when there is no eligible previous car. For an intermediate
point, use zero features and a missing flag unless all three subject
laps have reconciled splits. Record each selected peer and its lap-end
clock. Publish coverage, including at the latest observed lap.

Refit the nomination/practice ridge with finish-only features as the
control and with the intermediate point features added as the primary.
Use the existing equal-race weights, whole-race exclusion, lap bounds
and both crossover gates on all 393 cases. Compare both to the frozen
nomination/practice ridge. The finish-only control uses the same summary
formula and retains the original denominator. Qualification and fresh
confirmation require a full primary development pass.
