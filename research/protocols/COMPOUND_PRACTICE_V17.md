# R041 pre-race practice long runs

Collect practice only for the 28 opened race weekends. Match to the verified
race calendar by year and the preceding four days, and to the recorded meeting
key wherever available. Select FP2, or FP1 if FP2 is absent/cancelled. Require
one meeting and a finished session before race day. Record missing practice
explicitly. Preserve the downloaded endpoint records and digests locally.

For each HARD/MEDIUM/SOFT stint retain dry, globally green/unflagged timed
interior laps under the existing OpenF1 masks. Restore raw lap durations before
calculating practice slopes. Split into consecutive age runs and disjoint
six-lap blocks. Drop a block if slowest/fastest exceeds 1.07 to reduce
cooldown contamination. Estimate seconds per nine laps as nine times the median
of the 15 pairwise slopes. Use the median across blocks per driver/compound,
then the median across drivers. This is an observed practice pace trend.
Fuel load, programme and transfer to race conditions remain uncertain.

Use v13 nominated features with four additional inputs: reference and current
practice drift, each with log(1 + number of supporting drivers). Zero-fill
absent drifts and counts. Fit the same weighted ridge, excluding the entire
outer race, with the same bounds as v13. The control is sealed v13. No tuning
or altering the cohort. Report all folds, support and both-label gates. A
failure ends this registered study. Subsequent research must identify new
evidence or reconsider the forecast question explicitly, without changing the
current acceptance decision. Keep permanent reservations and unopened race
outcomes closed until a primary development candidate qualifies.
