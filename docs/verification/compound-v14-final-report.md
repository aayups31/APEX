# R041 last-pass prediction and build review

R041 remains IN_PROGRESS. The nominated-compound model passes nine of the
24 supported development races. Expanding training worsens its blended
forecasts and fails 19 races. R042 remains downstream. Research inventory
remains 40/73, research foundation R1 and production R0.

## What this pass completed

- Pre-race Pirelli nomination sources now cover all 28 opened races. The inputs
  are announced C-number allocations with publication dates and season
  interactions. Different seasons may change tyre construction.
- V13 predicts three future lap times from causal history and source-bound
  reference observations. It computes each crossover definition from the same
  three-lap forecast. The matched ablation removes the C-number features.
- Weighted scaling now uses centered squares. This addresses the roundoff
  warning previously observed on constant compound/season flags.
- V14 adds 985 disjoint clean/dry training windows from the existing native
  archives. The control contains 385 unique current windows. The expanded
  training set contains 1,370 windows across all 28 source races.
- Added windows exclude all ages occupied by an original current window,
  preserve gaps and require increasing native clocks. The complete outer race
  is excluded from fitting, including its additional windows.
- The source distribution and wheel build successfully. Both archives match
  the final packaged model source. An inference fixture executes from the
  wheel. CI now builds both distributions on Python 3.11 and 3.12.

## Prediction evidence

Every evaluated procedure retains the original 392 comparisons, both label
definitions and all 28 sources. Four sources have zero evaluation support.
Primary forecasts are declared before scoring. Acceptance requires every
supported event to beat the original reference and contrast baselines plus
the definition-specific reference baseline, reach 50% precision/recall where
crossovers exist, and produce zero false alarms on negative controls. Two
informative races are required.

| Fixed recipe | Supported races passing | Macro both-label MAE |
|---|---:|---:|
| V13 matched relative-compound control | 7/24 | 0.402920 s |
| V13 nominated-compound primary | 9/24 | 0.409208 s |
| V14 paired-only blend control | 7/24 | 0.453481 s |
| V14 expanded-training blend primary | 5/24 | 0.502420 s |

Nomination features improve four event gates and worsen two relative to their
matched control. Their average error increases slightly. The expanded-data
hypothesis fails both the gate and average-error comparison. More clean pace
windows alone do not resolve the remaining errors in this registered model.
All failures and predictions are retained in the result files. None of these
development scores is a new prospective confirmation. No fresh race outcomes
were acquired.

The expanded auxiliary model reaches its declared two-second correction bound
on 91 of 1,176 forecast laps, compared with 12 for its paired-only control.
It also produces six failed negative-control event/label gates. Bound hits
remain in the metrics. These results motivate checking training-regime
compatibility before drawing conclusions from the larger sample count.

## Verification

The full local baseline passed 835 tests in 1,220.69 seconds. The two new
allocation tests passed with runtime warnings treated as errors. The three
new unpaired-window tests passed, covering gaps, overlapping ages and full
outer-event training-target isolation.

V13's independent scalar audit verifies 784 forecasts and every race gate.
V14's independent auditor solves 48 weighted ridge fits through normal
equations and checks all 784 auxiliary/blended forecasts and race gates.
Native extraction of all 985 extra windows and the complete v14 refit each
replay exactly. The extraction replay uses the same provider preprocessing,
so its scope is reproducibility rather than an independent eligibility audit.

V13 CI at source 9dd384d passed all 837 tests on both Python versions, both
distribution builds, saved forecast replay and every existing workflow step.
Final source ae557d9 adds the three window tests and independent v14 audit.
Its complete matrix passed all 840 tests on both Python versions, both
package builds, both independent audits and every simulator verification step.
Python 3.11 tests took 617.72 seconds and Python 3.12 took 415.86 seconds.
See
[final source CI](https://github.com/aayups31/APEX/actions/runs/42315107551).
The [sealed last-pass receipt](compound-v14-last-pass-review.json) records
the final status, exact replays and source bindings. The six-car race smoke
completed all six laps with zero quality violations. The research smoke also
passed, retaining its existing synthetic ridge ill-conditioning warning.

## Reproduction and evidence

Run from the repository root, using fresh output paths.

```text
python research/scripts/audit_compound_allocation.py --output .cache/r041-v13-audit-new.json
python research/scripts/audit_compound_unpaired.py --output .cache/r041-v14-audit-new.json
python research/scripts/compound_unpaired_windows.py --output .cache/r041-v14-native-new.json
python research/scripts/diagnose_compound_unpaired.py --output .cache/r041-v14-refit-new.json
```

[V13 protocol](../../research/protocols/COMPOUND_ALLOCATION_V13.md),
[V13 results](compound-v13-development.json),
[V13 audit](compound-v13-audit.json),
[package review](compound-v13-package-review.json),
[V14 protocol](../../research/protocols/COMPOUND_UNPAIRED_V14.md),
[additional windows](compound-v14-training-windows.json),
[V14 results](compound-v14-development.json),
[V14 audit](compound-v14-audit.json).

The [nomination inventory](compound-nomination-inventory.json) and
[additions](compound-v13-nomination-additions.json) link the official Pirelli
announcements. They are declared announcements rather than per-set measurements.

## Completion boundary and next dependency

The fixed experiments reject these pace-only repair hypotheses. The remaining
work is to identify a causal forecast-time signal for race-specific changes,
such as traffic and changing race conditions, and demonstrate that its value
transfers across entire held-out races. Existing traffic and weather studies
must inform that design, including their failures. The remaining fresh races
can support confirmation only after a development candidate clears the gate.
Public corrected lap times leave physical tyre wear unidentified.

R041 may close only after prediction acceptance and separate frozen
confirmation succeed. Software regression and package builds alone cannot
establish that outcome.
