# R041 complete failure audit and conservative repair

**Infrastructure defects are repaired; R041's scientific acceptance still fails.**
The repaired procedure fails 13 supported development races. No fresh outcomes
were acquired, no historical rejection was changed, and nothing was promoted.
Foundation remains R1, production R0, inventory 40/73 DONE.

## Audit scope and findings

The [failure ledger](compound-v10-failure-inventory.json) includes 11 saved
historical result documents, every current event/label failure, and every
unsupported source. Historical experiments use different cohorts; their errors
must not be pooled as if they were one independent test.

Independent native reconstruction now covers **all 392 comparison cases and all
28 source races**, including the complete OpenF1 AND FastF1 eligibility
denominators. It checks quality exclusions, contiguous segments/common ages,
all different-compound pairs, reference availability, labels and missing/extra
published cases. All published cases and support counts match. This closes the
previous independent denominator-audit gap: no eligible case was lost between
the archived source tables and published cohort. It does not establish upstream
provider completeness or support outside the declared cohort.

| Failure or limitation | Repair / current disposition |
|---|---|
| Pooled/macro success hid individual failed races | New gate requires EVERY supported event and BOTH labels to pass |
| False alarms on zero-event controls | Explicit per-label zero-false-alarm check before new holdout acquisition |
| Separate event head contradicted point forecast | New interface derives one decision from the same point forecast and both prefix definitions |
| Missing independent excluded-cohort accounting | Full two-provider native enumeration; tested omitted-case and gap detection |
| Manifest save/reload could change report ordering | Canonical source ordering and round-trip regression test |
| Bounds could obscure invalid intermediate numbers | New interface rejects nonfinite aggregation/arithmetic; strict numeric/age/time checks |
| Same-driver/repeated-stint support could be misleading | Adaptive estimate excludes the forecast driver and gives each other driver equal weight |
| Japan and Qatar baseline regressions | Selected reference-persistence alternative removes them on opened-data evaluation |
| General pace/crossover prediction | Still fails 13 supported events; no acceptance or promotion |
| Four empty cohorts | Genuine retained common-age support limits; mask/horizon preserved |
| Calibrated uncertainty / physical wear | Unresolved scientific evidence; current radius is descriptive and physical quantities remain unknown |

The new interfaces are in `apexsim.research.compound_adaptive` and
`apexsim.research.compound_readiness`. Frozen v1-v9 implementations remain
unchanged for exact historical replay. These are scoped research repairs, not a
claim that every older experimental interface was rewritten or production-enabled.

## Conservative repair experiment

The registered hypothesis uses completed same-compound matching-age windows
from OTHER drivers. It compares 18 settings: no/half/full field correction,
minimum distinct-driver support 1/3/5 and decision margins 0.15/0.30 seconds.
Missing contributor support uses reference persistence, with every fallback
remaining in the denominator. Corrections are capped at 0.5 seconds. Ridge,
tree, contrast and midpoint comparisons remain in the full artifact.

Nested whole-event selection minimizes failed event/label gates first, negative
control false alarms second, then pace error. Outer labels cannot choose their
settings or interval radii. The strongest gate requires two informative events
and every supported event/label to pass both pace baselines and event criteria.

**No setting qualifies.** The full development selection chooses zero learned
correction, i.e. completed-reference persistence. This is evidence for falling
back rather than trusting the proposed field correction. It is not a new learned
tyre model. The event decision follows the same forecast and both prefix signs.

Opened-data Japan MAE becomes 0.470/0.474 seconds, with zero false alarms instead
of two. Qatar MAE becomes 0.349/0.387 seconds, with zero false alarms. Imola and
Saudi Arabia still pass their scoped event/label gates. These are development
results after outcomes were opened, not replacement prospective confirmations;
v8 Qatar and v9 Japan remain rejected in their original records.

The remaining nested failure codes comprise **14 event/label pace regressions
against contrast persistence, 12 recall failures and 4 precision failures**.
Counts overlap and refer to label gates, not distinct races. The 13 failed
supported events are:

- 2025 Abu Dhabi, Mexico, Singapore, Netherlands, Hungary, Austria and Spain.
- 2023 Bahrain, Netherlands and Monza.
- 2024 Miami, Monza and Singapore.

See the ledger for exact per-event metrics and codes. The repaired gate blocks
another fresh confirmation until these failures have a defensible solution.

## Empty cohorts are accounted for

| Source event | Longest retained common-age run | Explanation |
|---|---:|---|
| Miami 2025 | 0 | No retained age overlap across different-compound pairs |
| Britain 2025 | 2 | Dry/quality-supported comparison runs are too short |
| Las Vegas 2025 | 11 | Longest common run is below the fixed 12-age requirement |
| Australia 2023 | 11 | Longest common run is below the fixed 12-age requirement |

These are support limitations, not prediction errors. A new task using a
shorter horizon would require its own protocol and cannot rescue these frozen
results. No synthetic observations were inserted to make a cohort pass.

## Verification and reproduction

The full baseline passed **801 tests** in 1,046.22 seconds. The 16 new tests
cover the stronger gate, causal contributors, future-target isolation, invalid
inputs, numerical overflow, both native cohort paths, benchmark exclusion,
manifest round trips and independent scalar tamper detection. The full old/new
R041 targeted set passes **48 tests**. The updated full local suite passed **817
tests** in 1,040.95 seconds; lint passes. Python 3.11 CI passed all 817 tests and
artifact steps; Python 3.12 is queued, so the complete matrix remains pending.
[Source CI](https://github.com/aayups31/APEX/actions/runs/41864379731),
[sealed regression review](compound-v10-regression-review.json).
The research and six-car/six-lap race commands run, with zero race quality
violations. No conflicting stint interiors were found in the opened OpenF1
sources. These checks do not change the failed scientific acceptance result.

The complete nested trial replays exactly. Across all 18 settings and 392
cases, **7,056 future-target mutations** leave forecasts unchanged. The independent
scalar auditor reconstructs every setting, every inner/outer selection, every
forecast, uncertainty radius and readiness gate. Cross-event intervals remain
descriptive and do not confer guaranteed coverage.

Run from the repository root in the recorded environment, using fresh output
paths and the preserved native `.cache` archives:

```text
python research/scripts/compound_repair_data.py --output .cache/r041-repair-data-new.json
python research/scripts/audit_compound_cohort.py --dataset .cache/r041-repair-data-new.json --native-root .cache --output .cache/r041-cohort-new.json
python research/scripts/diagnose_compound_repair.py --output .cache/r041-repair-new.json
python research/scripts/audit_compound_repair.py --dataset .cache/r041-repair-data-new.json --results .cache/r041-repair-new.json --output .cache/r041-repair-audit-new.json
python research/scripts/compound_failure_inventory.py --repair .cache/r041-repair-new.json --cohort .cache/r041-cohort-new.json --output .cache/r041-failures-new.json
```

[Data](compound-v10-development-data.json),
[full compressed trial](compound-v10-development.json.gz),
[readable summary](compound-v10-development-summary.json),
[full native cohort audit](compound-v10-cohort-audit.json),
[independent scalar audit](compound-v10-development-audit.json),
[verification receipt](compound-v10-verification.json),
[registered protocol](../../research/protocols/COMPOUND_FAILURE_REPAIR_V10.md).

## What is actually left

R041 needs a model that transfers event-specific drift and crossover behavior
across the failing regimes. The simple field-adaptation hypothesis is rejected;
increasing its correction is not supported. Future work should establish a
measurable signal for trusting a correction and validate event-level recall and
false alarms before consuming another untouched race. Public physical compound
allocation, current-stint history and causal traffic may supply better context,
but their predictive value must be tested rather than assumed.

No software change can create measured physical wear or eligible historical
laps absent from the declared cohort. Those boundaries remain explicit. This
run repairs validation and reproducibility defects and preserves the unresolved
prediction evidence; it does not claim to have fixed every empirical failure.
