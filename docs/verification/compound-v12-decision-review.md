# R041 decision and prediction review

R041 remains open. Its v10/v11 scoring contract demands mutually exclusive
answers at Monza 2024. The new v12 research contract can represent both
answers. The candidate still fails forecast acceptance.

## Why the old gate cannot pass

The primary label compares two median lap times. The paired label takes the
median after subtracting the two times at each matched tyre age. On the same
13 Monza cases, the first counts one crossover and the second counts zero.
With a single yes/no forecast, zero alarms misses the sole primary event.
Any alarm violates the paired negative control. More training data cannot
resolve this contradiction. Across the panel the observed labels disagree on
22 of 392 cases. The original v10 and v11 decisions stand.

V12 forecasts one sequence of three lap times, then applies each label's own
formula to that sequence. Both forecasts are available at the original cutoff.
Both must meet the original error and event thresholds on every supported
race. A diagnostic that substitutes the observed three laps reconstructs
both targets in all 392 cases. This establishes that perfect predictions
can pass the revised scoring contract.

## What the forecast achieves

The fixed candidate carries the known three-lap pattern forward and applies a
compound-specific pace change learned from other races. It passes all checks
in 5 of 24 supported races. Nineteen fail at least one check. Four more source
races have no eligible comparison. These are development results. New holdout
acquisition remains blocked. V10, v11 and v12 evaluate different outputs or
models, so their counts do not measure a pure change in model accuracy.

To isolate the effect of the output change, the [frozen v11 replay](compound-v12-v11-paired-replay.json)
keeps every original primary pace estimate within 1e-12 seconds and reconstructs
both outputs. The v11 primary model still fails 15 races. The other three
models fail 14 or 15. This retrospective comparison cannot qualify a candidate.

All 72 compound regression tests passed locally. The separate v11 receipts
verify [1,568 model forecasts](compound-v11-scalar-review.json) and
[6,495 native lap associations](compound-v11-native-review.json).

## Prior work and data

The v10 independent audit reconstructed all 392 comparisons from 28 archived
races. The legacy scope-less safety-car deployment issue was addressed in
v3. FastF1 and OpenF1 apply different provider quality masks. The fuel
correction is an assumed 105 kg start, 1.4 kg per lap and 0.03 s/kg. These
quantities describe a fuel-corrected pace proxy. Physical wear remains
unknown. V11 preserved the original forecast clocks and labels. Its primary
model failed 16 supported races. Keep all original results and source splits.

The next input worth evaluating is the tyre specification assigned to each
weekend's soft, medium and hard compounds. The allocation can be known before
the race. For example, Pirelli published C3/C4/C5 for Monza and Singapore
2024. The [initial nominations inventory](compound-nomination-inventory.json)
contains published pre-race entries for ten opened events. Expand its coverage,
check for revised nominations, then
freeze a model and its comparison before fitting it. A fresh race confirmation
requires a development candidate that passes. The five remaining 2025 race
identities have unknown eligible-case counts until their outcomes are opened.

[Pirelli allocation announcement](https://press.pirelli.com/a-soft-september-for-pirelli-in-f1-compounds-confirmed-for-monza-baku-and-singapore/)

[v10 failure audit](compound-v10-repair-report.md) ·
[v11 race results](compound-v11-development-summary.json) ·
[v12 protocol](../../research/protocols/COMPOUND_DECISION_FEASIBILITY_V12.md) ·
[v12 predictions and race results](compound-v12-decision-results.json)

Reproduce the v12 evaluation from the repository root with a fresh output path:

```text
python research/scripts/diagnose_compound_decision.py --output .cache/r041-v12-replay.json
```
