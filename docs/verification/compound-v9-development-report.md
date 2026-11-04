# R041 bounded development evidence

**Development qualified; R041 is not complete.** Foundation R1 and production
R0 remain unchanged. The prior v8 Qatar rejection is retained.

The new source-bound corpus appends the opened v8 panel: 358 comparison cases,
22 supported events and 24 source events across 2023-25. Australia 2023 and
Miami 2025 have zero eligible comparisons and remain explicit. Native weather
is available at all 358 forecast cutoffs. Completed same-compound field windows
are available for 325 cases; 2,070 individual contributions were independently
checked against native lap records, including availability timestamps.

The registered nested whole-event procedure excludes each outer event from
both parameter fitting and inner model selection. It compares reference,
contrast and midpoint baselines, pace/context features, two ridge penalties
and 0/0.25/0.5-second residual bounds. Every fallback stays in the denominator.
The event head is selected independently on inner event folds. A mutation test
changes outer outcomes without changing that event's selected settings, point
forecasts, event scores or uncertainty intervals.

| Nested result | Difference of medians | Pairwise median |
|---|---:|---:|
| Macro event pace MAE | 0.479 s | 0.490 s |
| Reference persistence MAE | 0.588 s | 0.592 s |
| Contrast persistence MAE | 0.704 s | 0.685 s |
| Observed / predicted / matched crossovers | 89 / 85 / 51 | 88 / 85 / 46 |
| Recall / precision | 57.3% / 60.0% | 52.3% / 54.1% |
| Macro interval coverage | 92.5% | 90.9% |

Intervals average 2.286 seconds wide. They use inner cross-event residuals,
never training residuals or outer outcomes; they remain descriptive rather
than guaranteed confidence intervals. Event scores are uncalibrated decisions.

**The stronger comparators matter:** unbounded ridge obtains 0.404/0.407-second
macro MAE, and the tree obtains 0.447/0.444 seconds. Both beat the bounded model
on average. The bounded model's potential benefit is its limited learned
influence and explicit fallback, not superior average accuracy. Several event
gates still fail; Qatar nested MAE is 0.592/0.655 seconds against reference
0.349/0.387. No general reliability or perfect forecasting claim is justified.

The final development selection is reference persistence plus pace-feature
ridge alpha 10, capped at +/-0.5 seconds, with training-range fallback. Added
age/weather/field context did **not** win selection. The event head selects
C=1 and threshold=0.5. Neither selection is prospective acceptance evidence.

Artifacts: [data](compound-v9-development-data.json),
[full compressed tables and predictions](compound-v9-development.json.gz),
[readable summary with every outer event](compound-v9-development-summary.json),
[independent forecast audit](compound-v9-development-audit.json),
[independent native context audit](compound-v9-context-audit.json),
[development protocol](../../research/protocols/COMPOUND_BOUNDED_V9.md),
[prospective protocol](../../research/protocols/COMPOUND_BOUNDED_CONFIRMATION_V9.md).

The four fresh events are frozen in advance. At least two must supply positive
crossover evidence under both definitions; every supported event must pass
pace gates, and zero-event labels require zero false alarms. No supported
failure can be dropped. The scientific target remains effective fuel-prior
corrected public pace, with physical tyre wear and causal compound effects
unknown. There is no production promotion.
