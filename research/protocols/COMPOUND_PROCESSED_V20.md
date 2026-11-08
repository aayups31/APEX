# R041 completed-lap processed telemetry

Foundation R1, production R0. R041 remains IN_PROGRESS and R042 depends on its
acceptance. The v19 native-data diagnostic failed. A pinned free archive now
contains all needed 2025 input-lap files, with processing differences from
native observations. This study explicitly evaluates that representation.

Use TracingInsights/2023 commit 737c84d3ae14b9883a671ca248d015b69cf1cb58,
2024 commit d1543a71370d9b617b627319f8ad80b2f85dfd5e and 2025 commit
dfb3ea3f50b69857fe8e40cabe5e899743c59f6a. Acquire only opened development
event metadata and the first TWO laps of each current prefix, reference prefix
and reference target group. Preserve all 392 comparisons and 28 source events.
Keep APEX's original labels, fuel prior and nine-age-lap horizon.

The third known lap supplies a completed-lap timing buffer. Require the
selected export lap to end at least 30 seconds before the forecast cutoff.
Trim the first and last second within each selected lap. These precautions
limit edge interpolation exposure. They do not identify the unavailable native
sample provenance of every export. Record that uncertainty explicitly.

Validate session year/round/name through pinned session metadata, driver number
and code, lap number, stint, compound, tyre age, original lap duration and
start clock against the sealed APEX observations. Permit at most 0.5 seconds
clock discrepancy and 0.05 seconds duration discrepancy. Record all differences.
Reject ambiguous identity or nonmonotonic arrays. Reject nonfinite times,
unequal channel lengths and unknown DRS representations. Numeric invalid
channel values remain unavailable. Convert binary exported DRS 1 to open,
speed km/h to m/s, throttle percent to fraction and brake 0/1 or 0/100 to
fraction. Never execute upstream code or deserialize upstream pickle caches.

Integrate preceding valid values on adjacent intervals of at most one second.
Joint valid speed/throttle/brake/DRS coverage must reach 90% of each trimmed
lap. Keep missing groups explicit and retain all cases. Inputs are the same
23 v19 arithmetic features, now using two completed laps per group. Compare
all available native FastF1 laps using identical time masks. Report paired
channel errors, support and end-clock discrepancies across all nine archives.
The native comparison is descriptive and cannot prove unseen native provenance.

Fit one v17-plus-processed-input ridge using the unchanged equal-event,
unique-window weights, alpha 10, training-only scaling, three target laps,
whole-race exclusion and two-second lap bound. Saved v17 is the matched
input ablation. No model search. All v12 per-race and per-label gates apply.
Save checkpoint forecasts and independently reconstruct features and gates.
Test identities, clocks, DRS, missingness, future-target isolation and cutoff
invariance. Recheck previous audits, full regression and package CI.

Failure ends this registered candidate. Even a prediction pass needs a
separate provenance/causal timing review before any prospective confirmation.
No new holdout acquisition is authorized by this processed-data experiment.
