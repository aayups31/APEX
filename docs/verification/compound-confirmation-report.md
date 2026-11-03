# R041 independent race confirmation

The revised candidate uses robust within-stint compound slopes and anchors each
nine-lap prediction to a three-age prefix from the same driver. Calibration used
2024 Bahrain, Australia and Miami. The code and parameters were pushed in
`41f536f` before the 2025 race outcomes were acquired. The original study
remains a separate rejected experiment.
[Protocol](../../research/protocols/COMPOUND_CROSSOVER_V2.md) | [Calibration](compound-v2-calibration.json)

| Race | Supported blocks | Unsupported pairs | Observed crossovers | Matched | Candidate MAE | Persistence MAE |
|---|---:|---:|---:|---:|---:|---:|
| 2025 Monza | 12 | 8 | 0 | 0 | 0.462 s | 0.579 s |
| 2025 Abu Dhabi | 25 | 7 | 6 | 0 | 0.825 s | 0.659 s |

The candidate predicted zero crossovers in both races. On four of the six
Abu Dhabi crossover blocks, the fitted drift pointed away from the observed
change. On the other two it was too small to cross. The Monza improvement in
contrast MAE supplies no positive crossover evidence. Race-control exclusions
cover recorded global context, with sector flags, traffic and stint-order
effects remaining potential confounders. The model estimates observational
pace differences under the declared fuel prior.

R041 remains open. Another candidate needs a predeclared treatment of race
context and a cohort with sufficient crossover support. Both evaluation runs
produced byte-identical results. Raw provider rows remain in the local archive.
[OpenF1](https://openf1.org/) | [Archive digest](compound-v2-archive.json) | [Results](compound-v2-results.json) | [Replay](compound-v2-replay.json)

The follow-up traffic audit joined the 37 frozen evaluation blocks to native
gap-to-car-ahead samples. It retained the count of finite samples and the count
below 1.5 seconds for each contributing lap. On five of the six Abu Dhabi
crossovers, the change in relative close-traffic sample share was in the same
direction as the change in the relative lap-time penalty. This is a descriptive
association based on observed future exposure. A prospective candidate needs a
traffic forecast or a declared clean-air scenario with measured support.
Two diagnostic runs produced identical files. [Traffic audit](compound-v2-traffic-audit.json)

```powershell
python research/scripts/confirm_compound_crossover.py fit --dataset .cache/tyre-dataset-20261011.json --output .cache/r041-fit-fresh.json
python research/scripts/confirm_compound_crossover.py acquire --output .cache/r041-source-fresh
python research/scripts/confirm_compound_crossover.py evaluate --frozen docs/verification/compound-v2-calibration.json --archive .cache/r041-openf1-confirmation --output .cache/r041-evaluation-fresh.json
```
