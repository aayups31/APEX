# R041 residual, sector and native recovery review

R041 remains IN_PROGRESS. The registered sector and full native driving
models both fail prediction acceptance. Research foundation R1 and production
R0 apply, and R042 depends on R041 acceptance.

## Forecast and source diagnosis

The corrected v21 control has lower pooled error in both support groups.
On 372 fully supported comparisons, control and processed MAE are 0.472664
and 0.480238 seconds. On 20 incomplete comparisons they are 0.397103 and
0.479058 seconds. In a hindsight diagnostic, substituting perfect predictions
for those 20 cases while fixing all other forecasts still leaves 13 races
failing. That diagnostic uses outcomes and cannot qualify a candidate.

The 34 processed-input conflicts consist of 26 Canadian tyre ages and eight
clock discrepancies. All 26 ages are one lap lower in the export. The clock
differences range from -1.087 to -0.506 seconds, with equal lap durations.
They remain subject to the registered source checks.

## Registered comparisons

| Recipe | Passing races | Macro both-label MAE |
|---|---:|---:|
| Corrected nomination and practice control | 11/24 | 0.440175 s |
| Processed driving state | 10/24 | 0.458105 s |
| V22 native sector shares | 9/24 | 0.450159 s |
| V23 full native driving state | 9/24 | 0.460177 s |

V22 extracts sector durations from the original guarded and verified timing
archives. Three positive finite splits must reconcile to the raw lap within
0.05 seconds. Full sector support covers 385 of 392 comparisons. The nine
features describe within-lap redistribution and group availability.

V23 restores all 228 missing OpenF1 driver histories using public historical
access. The source returned HTTP 500 for the malformed date filter. Fixing
the query key produces HTTP 200. The server's millisecond filter precision is
accounted for in the response envelope check. Exact local half-open windows
determine which samples enter features. The acquisition command now uses the
repaired request, with verified snapshot reuse for already collected histories.

Native inputs have full support for 389 of 392 cases. Three reference groups
have incomplete coverage. All 392 comparisons are scored. The native model
still fails 15 races, including three negative-control event-label checks.
Independent scalar inference and race scoring verify all 392 forecasts for
each new study. Both additions are rejected under their frozen protocols.

## Tyre-age boundary finding

All 26 Canadian associations involve nine drivers and 11 stints. Their
recorded pit-outs occur one lap after OpenF1's reported stint start. The
export assigns the reported start lap to the previous stint and the pit-out
lap to the new stint. Computing age from the pit-out matches every affected
export age.

The broader panel deduplicates known laps across the already opened OpenF1
sources. It finds 1,716 matching driver/stint/compound identities. Of these,
814 have a unique prior pit-out within the reported stint. A diagnostic
pit-out anchor resolves all 24 distinct age disagreements, with zero new
disagreements. For example, Norris's Medium stint starts at lap 29 in OpenF1.
The lap export identifies lap 29 as a Hard in-lap and lap 30 as the Medium
out-lap. Lap 31 is therefore age two under the pit-out anchor and age three
under the original reported-start formula.

The next study should freeze a pit-out-anchored cohort rebuild and independently
check eligibility, age matching, clock availability and label changes across
all source races before fitting. These diagnostics do not revise the sealed
392-case cohort. R041 requires a full development pass and separate prospective
confirmation.

## Evidence and reproduction

Use fresh output paths from the repository root.

```text
python research/scripts/diagnose_compound_residuals.py --output <fresh-residuals.json>
python research/scripts/audit_compound_canada_boundary.py --panel --output <fresh-boundary-panel.json>
python research/scripts/compound_sectors.py --output <fresh-sector-data.json>
python research/scripts/compound_sectors.py --sectors <fresh-sector-data.json> --output <fresh-sector-model.json>
python research/scripts/prepare_compound_native_recovery.py --cache .cache/r041-v23-native-car --output <fresh-native-data.json>
python research/scripts/diagnose_compound_native_recovery.py --data <fresh-native-data.json> --output <fresh-native-model.json>
```

The native cache preserves exact HTTP bodies and sealed request receipts.
The native extraction and both model refits replay exactly. Final source
57f8de9 passes 893 tests on each of Python 3.11 and 3.12, both package builds,
the prior and current audits, and every simulator verification step.
[Final review](compound-v23-final-review.json),
[completed CI](https://github.com/aayups31/APEX/actions/runs/42914722779).

[Residual ledger](compound-v22-residuals.json),
[sector results](compound-v22-development.json),
[Canadian boundary checks](compound-v22-canada-boundaries.json),
[cross-race pit-out panel](compound-v23-pit-exit-panel.json),
[native data](compound-v23-native-data.json) and
[native results](compound-v23-development.json).

OpenF1 defines the supplied stint age in completed laps and supplies lap
pit-out flags. [OpenF1 source documentation](https://openf1.org/docs/#stints)
