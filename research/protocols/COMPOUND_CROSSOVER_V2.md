# R041 causal crossover confirmation

The first candidate remains rejected. Adjacent equal-age contrast windows can
flip repeatedly due to race context. A global offset also lacks a way to account
for a new driver's relative stint pace. This candidate estimates age slopes
within stints and anchors each forecast to an observed same-driver contrast.

Use the sealed 2024 Bahrain, Australia and Miami segments for calibration only.
Fit the median within-segment Theil–Sen slope per compound, constrained to
nonnegative effective degradation. Freeze before reading fresh race lap times.
The contrast forecast uses the median of three consecutive age comparisons as
its starting value and applies nine laps of the fitted slope difference.
Persistence uses the same starting value and zero drift.
The horizon was set after inspecting training slopes only and before acquiring
holdout laps. Three laps cannot span both margins for medium versus hard.

Evaluate on OpenF1 2025 Monza and Abu Dhabi race data. Select same-driver
different-compound stint pairs, exclude the first and last lap of each stint,
and require twelve consecutive overlapping ages. Exclude laps with missing
timing, pit out-laps, and overlap with global yellow, safety car, red flag or
wet conditions when supported by provider context. Score disjoint twelve-age
blocks from the start of each contiguous overlap. A crossover requires the
medians of the first and last three ages to have opposite signs, both above
0.15 seconds in absolute value. Report every supported block and unsupported
pair. Require at least one observed crossover per event, at least half matched,
at least half of predicted crossovers correct, and contrast MAE no worse than
persistence in each event. Results remain conditional observational pace
proxies with the existing fuel prior. This does not change the rejected first
candidate's gate.
