# R041 multi-season development corpus

The training expansion verifies nine existing FastF1 race archives and their
frozen calendar catalogs, then combines supported cases with the ten already
opened OpenF1 races. It acquires no fresh heldout race outcomes.

There are 284 windows across 18 supported events, drawn from 19 source events.
2023 Australia has zero qualifying windows. FastF1 filtering requires accurate,
undeleted, exact-green, non-pit dry-compound laps and observed dry weather.
Native UTC lap timestamps establish causal reference availability. Merging
segments of a driver/stint preserves excluded age gaps. OpenF1 retains the
earlier, less strict global-flag quality mask; provider differences remain a
limitation. Pace is a fuel-prior-corrected proxy; physical wear is unknown.

| Development label | Observed / predicted / matched | Pace macro MAE | Contrast persistence | Reference persistence |
|---|---:|---:|---:|---:|
| Difference of medians | 74 / 71 / 41 | 0.409 s | 0.734 s | 0.608 s |
| Pairwise median | 70 / 71 / 37 | 0.403 s | 0.710 s | 0.609 s |

The event selection uses leave-one-whole-event-out predictions, with the full
C/threshold grid retained. The chosen C=10, threshold=0.54 achieves minimum
pooled precision/recall 0.5211. These are development selection metrics. They
do not supersede any earlier independent rejection or close R041.

Additional nine-lap-history/three-lap-target diagnostics on the ten opened
events did not pass the crossover recall bar and were not advanced to a fresh
test. [Longer-history diagnostic](compound-history-development.json)

The derived training corpus is committed so the fit can be reproduced without
re-downloading large native archives. Source manifests and exact native table
hashes remain bound to every event. Frozen source/text fingerprints normalize
LF/CRLF line endings; native source archives retain byte-exact hashes.
Synthetic tests cover UTC clocks, yellow/weather exclusions, missing-age gaps,
benchmark denial before native reads and portable fingerprint tamper detection.

[Training cases](compound-multiseason-training.json),
[development table](compound-multiseason-development.json),
[fresh-test protocol](../../research/protocols/COMPOUND_MULTISEASON_V7.md),
[frozen model](compound-v7-calibration.json).

```text
python research/scripts/diagnose_compound_multiseason.py prepare --output .cache/r041-multiseason-new.json
python research/scripts/diagnose_compound_multiseason.py compare --dataset .cache/r041-multiseason-new.json --output .cache/r041-multiseason-new-development.json
python research/scripts/confirm_compound_multiseason.py fit --output .cache/r041-v7-refit.json
```

Sources and terms: [FastF1](https://docs.fastf1.dev/), [OpenF1](https://openf1.org/).
