# R050 green-flag traffic replay

Use the four 2023 development races and five 2024 held-out races in the
sealed R045 inventory. Exclude 2026. Use the verified FastF1 clocks,
timed laps and original DRS samples. Match OpenF1 Race sessions to the
same UTC event day and verify the session and meeting identities of all
overtake entries. Keep both source digests in the report.

## Timing-line transitions

Predict the same pair's signed gap at its next crossing. The current
follower must be adjacent in the complete timing order and within two
seconds. Both cars must have three consecutive accurate green nonpit
laps, with the next lap as the outcome. Exclude the start and first
two racing laps. Use only the starting gap and the two completed lap
durations at forecast time. A positive signed gap means the same car
still leads. An overtake recorded in the interval by OpenF1 in the
expected direction must agree with an observed negative gap to count
as a corroborated pass that lasted to the next line. Report separately
the reversals without corroboration, and events that did not last.
Allow a two-second publication delay after the second next-line
crossing. Score the corroborated endpoint over all eligible cases.

Fit the signed gap change with a fixed ridge penalty of 10 on the
starting gap and the previous lap's signed pace difference. Leave
the intercept unpenalized.
Compare against both gap persistence and unshrunk pace extrapolation.
Fit Jeffreys-smoothed pass probabilities by starting gap (up to 1 s,
1–2 s) and closing rate (positive or nonpositive), backed off to the
pooled frequency for cells with fewer than 25 examples. A sparse
DRS cell uses the corresponding gap and pace cell first. Score against the pooled training
frequency with Brier and log loss. Also score a prior-DRS extension
using only the already completed lap and keep the simpler model unless
the extension wins on training leave-one-race-out Brier. Publish
per-race and pooled scores. Require at least 25 corroborated passes in
each partition, at least one per held-out race, and corroboration of
a majority of held-out timing reversals. Require pooled Brier and
log loss improvement against the pooled rate and pooled gap MAE
improvement against both baselines, with gap MAE improvement against
persistence in at least three of five held-out races.

## Following pace

Use the followers' recognized DRS state from the actual measured
lap, requiring the same 90% coverage and one-second open threshold as
the prior R050 experiment. Compare three states: up to 1 s behind
without DRS, up to 1 s behind with DRS, and 2–4 s behind without DRS.
Use the gap at lap start, clean timed neighbors, and keep the current
leader fixed through the lap. Match within driver, race and tyre stint
using nearest laps within five laps of tyre age without replacement
within each contrast. Require the same timing-line neighbor at both
ends and no recorded exchange between the two cars. Estimate a closed-DRS
close-following pace term and a separate close-following DRS
association. Compare the sign and size of race-level median contrasts
between development and held-out races. Report support and uncertainty.
A qualified pace claim requires agreement with an expected positive
following loss and negative DRS term in development and in a
majority of the five held-out races, with at least 25 matched pairs per
term per partition. A failure retains the evidence as a diagnostic.

Selection into DRS and following states is observational. Timing
clocks establish an operational lap-scale pace model, with shared
upstream timing provenance and no measured downforce. The pass label
covers corroborated order changes that persist to the timing line.
This gate is scoped to adjacent cars with clean green laps, the
pre-2026 DRS rules, and an offline research replay.
