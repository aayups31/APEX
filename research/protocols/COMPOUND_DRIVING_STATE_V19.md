# R041 observed driving state

Foundation R1 and production R0. R040 is complete and R041 is IN_PROGRESS.
Baseline 8f9e26b passes 849 tests on both CI Python versions. Nine current
regressions pass locally and the independent v15-v17 audit replays.

Test whether recorded driving state adds transferable information to v17's
practice and nomination inputs. Before scoring, acquire only the 228
driver/session histories required for the already opened OpenF1 races. Native
FastF1 car tables supply the other nine source races. Guard reservations before
payload reads. Keep raw response bytes and query receipts, hash snapshots and
fail on identity conflicts. Query bounds span only the required observed
reference/current windows. For each forecast, select only native samples within
the relevant completed laps and before its original cutoff.

For every current prefix, reference prefix and reference target lap compute
time-weighted speed (m/s), throttle fraction, brake fraction, coasting fraction
(throttle below 0.05 with no brake) and DRS-open fraction. Use preceding sample
values on intervals of at most one second, with both sample timestamps within
the completed lap. Never interpolate, fill gaps or extend endpoints. Joint
validity requires finite speed in [0,120] m/s, throttle in [0,1], source-native
brake boolean or OpenF1 0/100, and a known DRS code under R033. Require 90%
joint time coverage for all three laps to support a group.

Append the supported current group's five means and last-minus-first values,
its mean differences from each reference group, and three support indicators
to the v17 matrix. Missing groups or differences are zero with explicit support
indicators. Keep every case. Fit the unchanged equal-event, unique-window
weighted, train-scaled ridge alpha 10, whole race excluded, three outputs and
two-second lap-change bound. V17 is the saved matched input ablation. This is
one registered candidate with no parameter search.

Preserve all 392 cases, 28 source events, 24 supported races and both v12 label
gates, original baselines, 50% precision/recall, zero false alarms on negative
controls, and at least two informative races. Save all forecasts/checkpoints,
coverage, failures, source and code hashes. Independently replay feature
arithmetic, checkpoint inference and per-race scoring. Tests must mutate future
telemetry and targets and verify their isolation. Full regression and package
CI must pass. Only full primary development qualification permits a separately
frozen prospective confirmation. Failure ends this registered experiment.
