# R041 same-compound negative control

Use only the 28 previously opened race archives, corrected stint ages and
the existing same-phase rule. For each distinct driver pair and stint pair
on the same compound find disjoint blocks of twelve consecutive matched
ages with lap ends within 30 seconds and at most one race lap apart.
Use the last three matched ages as the target. Estimate the paired pace
difference with the median of all distinct same-compound lap pairs completed
before either driver started the block, requiring six pairs. Apply the
existing greedy nonreuse rule within each driver pair. Compare with zero
difference and with the median difference of the first three block ages.
Require the target laps to start after the prefix has completed.

Report coverage, race-average absolute errors, and counts of races improving
over each comparator. Repeat with all controls from the two evaluated stints
excluded to measure transfer to a different stint. This study scores driver
and car pace offsets only. It cannot qualify a crossover model.
