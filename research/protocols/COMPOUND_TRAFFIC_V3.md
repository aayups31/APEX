# R041 clean-air support and prospective traffic confirmation

Development screening requires five finite interval samples on each scored lap
and at most 20% of samples closer than 1.5 seconds. Only one of 37 earlier
blocks survives and none contains a crossover. Use a traffic forecast instead.

Fit on the 37 Monza and Abu Dhabi 2025 development blocks only. For each stint,
fit a pooled linear forecast of the last-three-age close-traffic sample share
from its first-three-age share. Constrain the slope to [0, 1] and the forecast
to [0, 1]. Estimate a nonnegative seconds-per-share coefficient from the
observed development change in relative exposure and pace, after subtracting
the frozen compound slope contribution. Use ridge penalty 1 on that scalar
coefficient. At evaluation, the pace forecast adds the estimated penalty for
the predicted relative exposure change to the frozen prefix-anchored model.
Future gaps serve as diagnostic targets only.

Freeze the implementation and calibration before opening 2025 Bahrain and Spain
race outcomes. Keep the v2 age matching, weather and global flag filters,
disjoint blocks, nine-lap forecast, and 0.15 s crossover margin. Exclude a block
from prediction only when its prefix lacks five finite samples per scored lap.
Report unsupported pairs, crossover hits and false alarms, contrast MAE versus
persistence, and traffic forecast error where future samples suffice. Require
at least one observed and predicted crossover, at least half of each matched,
and MAE no worse than persistence in each race. Preserve all earlier results.
