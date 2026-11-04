# R041 event-conditioned confirmation

Freeze `9e65377` preceded acquisition of China and Hungary 2025 outcomes. The
six-input weighted ridge model was selected on six previously opened events.
The saved ridge-grid table reproduces development selection; macro event MAE
was 0.398683 s. These values are development results, not fresh confirmation.

| Independent event and labels | Blocks | Observed / predicted / matched | MAE | Contrast persistence | Reference persistence |
|---|---:|---:|---:|---:|---:|
| China, difference of medians | 10 | 2 / 1 / 1 | 0.330 s | 0.686 s | 0.348 s |
| Hungary, difference of medians | 36 | 14 / 3 / 2 | 0.644 s | 1.045 s | 0.975 s |
| China, original pairwise median | 10 | 2 / 1 / 1 | 0.380 s | 0.800 s | 0.345 s |
| Hungary, original pairwise median | 36 | 13 / 2 / 2 | 0.650 s | 1.054 s | 0.965 s |

The full gate fails. China passes the difference-of-medians check, but its
pairwise-label MAE is worse than completed-reference persistence. Hungary
misses crossover recall under both definitions. Its empirical interval coverage
is 66.7% (primary) and 75% (pairwise), despite 90% development residual radii.
All future current-stint targets stayed outside the forecast computation.
There were no reference-time exclusions; 17 and four compound/stint pairs
lacked the required age support. These results do not establish physical wear,
causal compound effects, uncertainty calibration or production suitability.

An independent scalar auditor reconstructed native lap labels, reference and
prefix timestamps, every forecast, aggregate errors and acceptance decisions.
It imports none of the candidate feature, fitting, prediction or metric code.
Its scope covers every published case, with no independent full-cohort
enumeration. A synthetic integration test detects an altered forecast even
when its enclosing result seal is recomputed.

[Protocol](../../research/protocols/COMPOUND_CONDITIONED_V5.md),
[frozen fit and development grid](compound-v5-calibration.json),
[results](compound-v5-results.json), [archive](compound-v5-archive.json),
[independent audit](compound-v5-audit.json). Source: [OpenF1](https://openf1.org/).

```text
python research/scripts/confirm_compound_conditioned.py evaluate --frozen docs/verification/compound-v5-calibration.json --archive .cache/r041-conditioned-holdout --output .cache/r041-v5-replay.json
python research/scripts/audit_compound_conditioned.py --frozen docs/verification/compound-v5-calibration.json --results .cache/r041-v5-replay.json --archive .cache/r041-conditioned-holdout --output .cache/r041-v5-audit-replay.json
```

R041 remains open. These eight opened races may now be development data, but
any later independent confirmation requires a new declared, frozen split.
