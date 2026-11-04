# R041 multi-season completed-reference confirmation, v7

Current research foundation R1, production R0. R041 remains open; retain every
v1-v6 rejection. The longer-prefix, shorter-horizon, field-context and tree
diagnostics were development only and did not justify fresh confirmation.

## Dataset and method freeze

Expand training to the ten opened 2025 races plus nine already archived 2023/24
races. The prepared dataset contains 284 supported windows across 18 events;
2023 Australia is the nineteenth source but has zero eligible windows. Its
exclusion remains explicit. Preserve native archive/calendar hashes and source
code bindings in the committed derived training dataset. Native timestamps
must prove the earlier reference curve was complete at forecast time.
Frozen text/source hashes normalize CRLF to LF for portable Git checkouts;
native archive files retain exact byte hashes and JSON evidence retains seals.

FastF1 uses the existing R021 accurate, undeleted, exact-green, non-pit,
dry-compound mask, plus dry observed weather throughout each retained lap.
Interpret native UTC dates consistently across workstations. Merge segments
only within the same actual driver/stint, preserving missing age gaps. OpenF1
retains v4's corrected global flag/dry mask; this provider-quality difference
is a limitation, not an assertion that the two quality masks are identical.
Fuel priors and effective-pace truth labels remain unchanged. Physical wear
is unknown. Permanent benchmark reservations remain untouched.

Keep v6's two outputs and covariates, nine-lap horizon, disjoint 12-age blocks,
0.15 s margins and both label definitions. Refit the pace head with weighted
ridge alpha 10. Refit the balanced logistic event head on the expanded dataset.
Select C from {0.1,1,10} and decision threshold from 0.35 through 0.65 in 0.01
steps using pooled leave-one-whole-event-out development predictions. Maximize
the minimum precision/recall across BOTH label definitions; break ties by lower
C, then threshold closest to 0.5. The frozen choice is C=10, threshold=0.54.
Training normalization and label/window weighting remain as specified in v6.

Save the full selection table. Development primary counts are 74 observed,
71 predicted, 41 matched; pairwise counts are 70 observed, 71 predicted,
37 matched. The resulting minimum precision/recall is 0.521127. Pace macro
MAE is 0.409342 s primary and 0.402952 s pairwise, compared with completed-
reference persistence 0.608344 s and 0.608651 s. These are selection results,
not independent confirmation. Balanced scores and training residual radii
are still uncalibrated; report their limits and both-head disagreements.

## New independent split and unchanged numeric gate

Freeze code, protocol, derived training cases, selection results and parameters
before opening United States (Austin) 2025 round 19, session 9888/meeting 1271,
or Mexico round 20, session 9877/meeting 1272. Only race identities were opened
as session metadata. Verify the 2025 event reservations before any lap request.

For EACH fresh race, under EACH label definition: nonzero observed and predicted
events, at least half of observed and half of predicted matched by the event
head, and pace-head MAE no worse than BOTH contrast persistence and completed-
reference persistence. Report the 2024-prior baseline, compound breakdowns,
RMSE, empirical interval coverage/width, unsupported pairs and timestamp gaps.
No threshold, model, cohort or error tolerance changes after opening outcomes.

Closing R041 requires passing these gates, exact saved-result replay, native
and scalar independent audit, causal/UTC/context/benchmark tests and CI. The
supported output remains conditional public pace forecasting and crossover
event decisions against a completed historical reference. Absent that reference,
abstain. This does not identify physical wear, establish counterfactual compound
causality, validate a strategy engine or promote the production kernel.

Rollback: retain R041 open and preserve all attempted candidates and archives.
Sources and terms: https://openf1.org/ and https://docs.fastf1.dev/ .
