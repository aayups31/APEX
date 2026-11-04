# R041 multi-season v7 confirmation

Freeze `63ab165` preceded Austin/Mexico 2025 lap acquisition. Two temporary
OpenF1 connection failures left preserved incomplete download folders; a fresh
third acquisition completed. Neither parameters nor selection changed.

| Fresh event / labels | Blocks | Observed / predicted / matched | Pace MAE | Contrast persistence | Reference persistence |
|---|---:|---:|---:|---:|---:|
| Austin / difference of medians | 19 | 4 / 6 / 4 | 0.283 s | 0.521 s | 0.483 s |
| Mexico / difference of medians | 33 | 7 / 7 / 4 | 0.331 s | 0.566 s | 0.724 s |
| Austin / pairwise median | 19 | 4 / 6 / 4 | 0.285 s | 0.564 s | 0.478 s |
| Mexico / pairwise median | 33 | 10 / 7 / 4 | 0.353 s | 0.495 s | 0.742 s |

Three of four event/label gates pass. Mexico's original pairwise recall is
4/10, below the required half, so the complete v7 gate fails. R041 remains open.
Both label definitions' pace errors beat both persistence baselines in both
races. The independent scalar/native audit reconstructs all 52 published
cases. The result and the offline calibration refit reproduce exactly.

There are no reference timestamp exclusions; each race has three unsupported
compound/stint pairs. Primary residual-interval coverage is 100% and 90.9%,
with mean widths 1.513 s and 1.523 s. Event/point decisions differ on two and
three primary cases (two and four pairwise cases). The score is uncalibrated;
the target is effective public pace, with physical wear unknown.

[Protocol](../../research/protocols/COMPOUND_MULTISEASON_V7.md),
[training/development report](compound-multiseason-development.md),
[fit](compound-v7-calibration.json), [result](compound-v7-results.json),
[archive](compound-v7-archive.json), [audit](compound-v7-audit.json).
Source: [OpenF1](https://openf1.org/).

```text
python research/scripts/confirm_compound_multiseason.py evaluate --frozen docs/verification/compound-v7-calibration.json --archive .cache/r041-multiseason-holdout-final --output .cache/r041-v7-new-replay.json
python research/scripts/audit_compound_multiseason.py --frozen docs/verification/compound-v7-calibration.json --results .cache/r041-v7-new-replay.json --archive .cache/r041-multiseason-holdout-final --output .cache/r041-v7-new-audit.json
```

These opened races may enter later development only with a fresh independent
split. This retained failure cannot be converted into a passing confirmation
by changing its decision threshold.
