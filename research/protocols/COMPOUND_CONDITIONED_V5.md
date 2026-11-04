# R041 event-conditioned completed-reference forecast (v5)

Current research foundation R1, production R0; R041 remains open after v4's
Canada robustness failure. Earlier candidates, gates and failures are retained.
V4's original pairwise gate passed in both races, but its additional
difference-of-medians gate failed in Canada. Do not erase that outcome.

## Information, model and selection

Use all six already opened 2025 races (Monza, Abu Dhabi, Bahrain, Spain, Canada,
Austria) for development. Keep v4's corrected context filtering, retrospective
clean/dry eligibility, same-driver different-compound age matching, disjoint
12-age blocks, nine-lap forecast, timestamp guard and 0.15 s crossover margins.
Physical wear remains unknown; the targets are fuel-corrected effective pace.
No production promotion is authorized by this experiment.

The completed earlier stint supplies an event-specific pace-change covariate.
The current three-lap prefix supplies local slope and current pace contrast.
Fit current-stint nine-lap pace change to: three compound indicators, known
reference median pace change, 4.5 times the last-minus-first current-prefix
pace (nine-lap local linear extrapolation), and the prefix median pace contrast.
All six features are available at forecast time. Fit weighted ridge regression
with penalty 10, no intercept, no scaling, and unit total weight for each unique
later-stint/age window across its multiple reference pairs. The penalty applies
to all coefficients. Do not constrain signed proxy pace drift to physical wear.

Development compared ridge penalties 1, 10, 100 and Huber penalties 1, 10 for
four nested feature sets (compound only; add reference change; add local slope;
add prefix contrast). Select ridge/10/all features by lowest macro event MAE
under leave-one-event-out development prediction. Its exploratory macro MAE
was approximately 0.399 s. Save the reproducible ridge-grid development table
with the frozen fit; Huber comparisons were diagnostic and not retained models.
LOEO values are development selection evidence, not independent confirmation.

Forecast later-stint target pace as median(current prefix) + predicted change.
Subtract from median(known reference target). Publish the same constant-target
point forecast against both difference-of-medians and original pairwise-median
labels, as in v4. Per compound, retain a weighted empirical 90% training absolute
residual radius; report fresh coverage and width descriptively.

## Independent confirmation and stopping gate

Freeze this protocol, code and parameters before opening China 2025 round 2
(session 9998, meeting 1255) or Hungary round 14 (session 9928, meeting 1266)
lap outcomes. Only session identities have previously been opened. Fetch five
OpenF1 tables per event with an immutable manifest and benchmark guard.

In EACH race, under EACH of the two label definitions: at least one observed
and predicted crossover, at least half of observed and half of predicted
matched, and MAE no worse than both contrast persistence and completed-reference
persistence. Report the frozen 2024 compound-drift baseline as well. Retain
all unsupported pairs, timestamp exclusions, compound breakdowns, RMSE,
uncertainty coverage and width. Never tune on these fresh outcomes while calling
the same result independent. R041 closes only with a passing confirmation,
saved evidence, exact replay, causal/hand-calculation tests and applicable CI.

No available reference or inadequate compound training support means abstain.
Conditional support and previous failures must remain in the final model card.
The six timing-derived inputs cannot establish causal compound effects or
physical wear; track evolution, fuel priors and traffic remain confounders.
Rollback: preserve R041 open and retain v4 and all earlier candidates.

Sources and units follow [v4](COMPOUND_REFERENCE_V4.md). Public source and terms:
https://openf1.org/ ; endpoint base https://api.openf1.org/v1/ .
