# R041 distance-aligned native speed profiles

The v24 fuel sensitivity audit separates fragile crossover labels from
stable decisions, and both sets still contain misses. A whole-lap speed
average can hide a driver trading pace in slow sections for pace on the
straights. Test that signal directly on the sealed corrected v24 cohort.
Use the existing native archives and telemetry receipts only.

For each of the nine known laps, integrate the archived speed samples over
the native lap clock using trapezoids. Extrapolate speed to either lap
boundary only within one second. Reject a lap for an interior gap greater
than two seconds, fewer than two samples, invalid speed or cumulative
distance, or less than 95% clock coverage by gaps of at most one second.
Require at least 1 km of total distance. Interpolate speed at the centers of
64 equal-distance bins. Normalized distance is an alignment proxy.

Use the per-bin median profile from the three completed reference prefix
laps to define the 16 slowest and 16 fastest bins, breaking ties by bin
index. Use the same mask for the nine known laps. Require all nine profiles
and a ratio of longest to shortest integrated lap distance of at most 1.03.
Compute the slow and fast mean speed for each lap. Append six values to the
v24 native input vector: the three-lap median speed difference between
current and reference prefix, the corresponding current versus reference
target difference, and the last-minus-first current prefix speed, each for
slow and fast bins. Add one support flag. Use zeros and a false flag for
unavailable profile inputs. Never use current target telemetry.

Refit the original v24 native ridge and the expanded ridge (alpha 10,
same weights, same three lap offsets and two-second bounds) on identical
whole-race splits. The expanded ridge is the primary. Independently
verify bin alignment arithmetic, checkpoint inference and the full original
v12 pace and crossover gates for both arms. Keep every v24 evaluation row
and both crossover definitions. Do not use the fuel diagnostic to change
labels, exclude windows or select results. No fresh timing outcomes can be
opened before a complete primary pass.
