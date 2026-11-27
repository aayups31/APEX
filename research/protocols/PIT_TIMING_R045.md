# R045 pit timing calibration

Use only the already opened, manifest-verified FastF1 development races.
Train on 2023 rounds 1, 3, 14 and 15. Test on 2024 rounds 1, 3, 6, 16
and 18. Keep the permanent benchmark reservation enforced. This is a
held-out-season development test.

Require adjacent inlap and outlap, explicit green and undeleted timing,
lap start/end/duration agreement within 0.1 s, one pit entry on the first
lap and one pit exit on the second. Require both pit clocks inside their
respective laps. The elapsed time between them is measured pit-lane
transit including service.

Estimate a separate incremental pace proxy for the inlap and outlap.
The stopped driver's expected lap is their preceding three-lap median
plus the median change in contemporaneous unpitted peers. The target
uses peer outcomes on the two pit laps, available retrospectively only.
Use three or more peers with clean contiguous laps on the same five race
lap indices, a single stint and initial clean-prefix end times within
120 seconds of the subject. Require the stopped driver's prefix and
inlap to share a stint. Apply the native clean timing checks to all prefix
and peer rows. Keep exclusions explicit, and preserve negative proxies.

Fit separate medians of measured lane time, incremental inlap and outlap
time, and the sum of the two incremental times. Use the circuit median
from 2023 when there are at least five training stops at the circuit.
Otherwise use the pooled 2023 median. The fixed baseline always uses the
pooled 2023 median. No held-out clocks enter the predictions. Report
held-out MAE by race and channel. Qualify this calibration only if all
five test events supply at least five supported stops, the circuit model
beats pooled total incremental MAE averaged across events, and it
reduces that error in at least three events. Report other channels and
all fallback use. Keep the research timing proxy distinct from a
measured no-pit counterfactual.
