# R041 processed adapter and source recovery

R041 remains IN_PROGRESS. The free archive adapter is implemented and its
registered model fails prediction acceptance. Research foundation R1 and
production R0 apply. R042 remains downstream.

## Delivered adapter

Pinned TracingInsights JSON supplies 2,238 distinct input-lap files across the
opened 2023–2025 races. The adapter selects two completed laps per group, trims
each lap's first and last second and requires a 30-second forecast buffer.
It validates identity, clocks, tyre metadata, channel schemas and DRS encoding.
It preserves exact downloaded bytes and sealed URL receipts, with bounded
network retries and integrity checks on replay.

All 392 comparisons remain in scoring. All three driving groups are supported
for 372 cases. Thirty-four input associations are rejected, comprising 26
tyre-identity conflicts in Canada 2025 and eight clock conflicts in Bahrain
and Spain 2025. Rejections remain explicit through support indicators.
None of these source conflicts is silently reconciled with the target data.

## Errors found and corrected

The first adapter iteration used the wrong 2023 folders for R14 and R15.
Verified Jolpica calendars and FastF1 manifests identify Italy and Singapore.
The new adapter now resolves names from verified calendars and checks export
dates. OpenF1-derived event joins also require exact session keys. The wrong
folders' inputs failed identity checks. Their downloaded snapshots and initial
diagnostic results remain locally quarantined under
.cache/r041-v20-rejected-first. Their initial 12/24 result is invalid for
scientific comparison.

Earlier nomination metadata assigned the Dutch C1/C2/C3 allocation to
2023 R14. The corrected Monza allocation is C3/C4/C5. R15's C3/C4/C5 codes
agree with Singapore, and its source reference is now corrected too.
Both announcements predate their forecasts. Prior frozen experiments remain
historical records. Current comparisons use the repaired inventory for both
the matched control and primary model.

## Validated comparison

| Calendar-corrected recipe | Passing races | Macro both-label MAE |
|---|---:|---:|
| Nomination and practice control | 11/24 | 0.440175 s |
| Control plus processed driving state | 10/24 | 0.458105 s |

The primary gains Saudi Arabia but loses Abu Dhabi and Canada relative to
the corrected control. It has 14 failed races and three failed negative-control
event-label gates. Prediction precision/recall and pace baselines still fail.
The processed-driving hypothesis is rejected under the frozen recipe.

The independent audit reconstructs all 784 control/primary checkpoint
forecasts and all 96 event-label metrics. It checks source hashes, corrected
nomination bindings, feature arithmetic, output bounds and qualification.

## Native validation and limits

The comparison covers 522 distinct known laps across all eight supported
FastF1 races. The ninth older source, Australia 2023, has zero cohort support.
Every paired comparison reaches 90% joint coverage under the same trimmed mask.

| Channel | Mean absolute difference |
|---|---:|
| Speed | 0.093465 m/s |
| Throttle | 0.002434 fraction |
| Brake | 0.001886 fraction |
| Coasting | 0.006707 fraction |
| DRS-open | 0.000498 fraction |

The exports interpolate merged car and position signals and omit native
sample provenance. Two buffered laps and edge trimming reduce endpoint
exposure. They cannot certify unseen source timing. Complete prediction
acceptance and a separate causal availability review are required before
prospective confirmation. No holdout acquisition or production promotion is
authorized by these results.

Twelve adapter regressions cover units, DRS, malformed arrays, identities,
clock tolerances, timing buffers, missingness, calendar renumbering and the
saved full-cohort independent audit. Earlier driving and authentication
regressions also pass locally. Full source CI runs the old audits, the new
audit, all regressions, package builds and simulator verification.

## Reproduction

From the repository root, use fresh output paths.

```text
python research/scripts/prepare_compound_processed.py --cache .cache/r041-v20-snapshots --output <fresh-data.json>
python research/scripts/compare_compound_processed.py --data <fresh-data.json> --output <fresh-comparison.json>
python research/scripts/diagnose_compound_processed.py --data <fresh-data.json> --output <fresh-model.json>
python research/scripts/audit_compound_processed.py --data <fresh-data.json> --result <fresh-model.json> --output <fresh-audit.json>
```

The cache permits exact extraction replay without new downloads. Model and
audit inputs retain APEX's original fuel correction and targets.

## Next work

The historical access obstacle has a free implementation path. Additional
driving summaries have not established better prediction transfer. Next,
inspect the corrected control's failed cases against the primary's residuals
and support, including the Canada tyre-age disagreements and negative-control
alarms. Establish a new forecast-time signal before registering another model.
R041 completion still needs all prediction gates and independent prospective
confirmation.

Evidence includes [processed inputs](compound-v21-processed-data.json),
[corrected nominations](compound-v21-nominations.json),
[native comparison](compound-v21-native-comparison.json),
[model results](compound-v21-development.json) and
[independent audit](compound-v21-audit.json).

Official allocation sources are
[Monza, published 31 July 2023](https://press.pirelli.com/news-and-tyre-choices-for-zandvoort-and-monza/) and
[Singapore, published 30 August 2023](https://press.pirelli.com/unchanged-nominations-for-singapore-japan-and-qatar--in-name-at-least/).
