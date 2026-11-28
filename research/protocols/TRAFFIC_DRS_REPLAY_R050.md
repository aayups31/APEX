# R050 pre-reversal DRS association

Use the nine verified R045 FastF1 timing archives. Train on the four
2023 races and test on five 2024 races. For each pair of adjacent clean
cars separated by at most two seconds at the timing line, check their
order on the next lap. Require green, accurately timed and nonpit rows
for both laps. The result is a timing-line reversal proxy.

Join the follower's DRS telemetry from the first completed lap only.
Require at least 90% clock coverage from valid consecutive samples no
more than one second apart. Record whether DRS was open for at least
one measured second. Compare Jeffreys-smoothed training frequencies in
two gap bands (up to one second and one to two seconds) with and
without DRS status. Publish all denominators, event-level Brier and
log loss, and evaluated frequencies. Repeated drivers and adjacent
pairs create correlated observations.

This is a predictive association for timing-line order. A qualifying
traffic model additionally needs on-track pass confirmation, a
dirty-air effect and held-out gap replay.
