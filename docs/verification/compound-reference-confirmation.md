# R041 completed-reference confirmation

Commit `33508d6` froze the model, parameters and acceptance protocol before
acquiring Canada and Austria 2025 race lap outcomes. The model forecasts the
later stint only, using an earlier stint curve whose measured timestamps all
precede the forecast time. It estimates signed effective pace drift from four
previously opened races, deduplicating repeated current-stint windows.

| Fresh event | Blocks | Crossovers observed / predicted / matched | MAE | Contrast persistence | Reference persistence |
|---|---:|---:|---:|---:|---:|
| Canada, difference-of-medians labels | 11 | 1 / 1 / 0 | 0.351 s | 0.594 s | 0.416 s |
| Austria, difference-of-medians labels | 28 | 9 / 8 / 7 | 0.354 s | 0.592 s | 0.456 s |
| Canada, original pairwise-median labels | 11 | 2 / 2 / 1 | 0.312 s | 0.548 s | 0.373 s |
| Austria, original pairwise-median labels | 28 | 8 / 7 / 5 | 0.402 s | 0.463 s | 0.515 s |

The original pairwise checks pass in both events. The additional preregistered
difference-of-medians check fails in Canada; the complete v4 gate therefore
fails and R041 remains open. Lower pace error alone does not close that gate.
No reference timestamp violations occurred. Unsupported compound/stint pairs
numbered 92 and 16 respectively. The single soft-current-stint Austria window
had 1.032 s error, worse than either persistence baseline.

The empirical development residual intervals covered 100% and 96.4% of primary
targets, with mean widths 2.288 s and 2.318 s. These broad intervals are
descriptive training residual radii, not a calibration claim or a reliable
certainty statement for a 0.15 s crossover threshold. Public timing identifies
effective pace, not physical tyre wear. The retrospective clean/dry cohort
conditions on future scored lap availability and does not forecast flags/pits.

[Frozen protocol](../../research/protocols/COMPOUND_REFERENCE_V4.md),
[parameters](compound-v4-calibration.json), [complete results](compound-v4-results.json),
[source manifest](compound-v4-archive.json). Public source: [OpenF1](https://openf1.org/).

Reproduce from the repository root with the project Python environment:

```text
python research/scripts/confirm_compound_reference.py evaluate --frozen docs/verification/compound-v4-calibration.json --archive .cache/r041-reference-holdout --output .cache/r041-v4-replay.json
```

Further development may use these six opened races, with a newly frozen model
and fresh event split required for another independent confirmation.
