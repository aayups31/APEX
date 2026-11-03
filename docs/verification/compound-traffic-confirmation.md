# R041 traffic forecast and clean-air support

The clean-air screen retained one of 37 development blocks and zero crossover
examples. The third candidate therefore predicts close-traffic exposure from
each stint prefix and uses that forecast to adjust the compound pace contrast.
It uses the previous 37 blocks for development. Bahrain and Spain 2025 were
acquired after the code, fit and acceptance rules were pushed in `d6fbf69`.
[Protocol](../../research/protocols/COMPOUND_TRAFFIC_V3.md) | [Initial calibration](compound-v3-calibration.json)

The preliminary run revealed that scope-less OpenF1 safety-car deployment
messages bypassed the inherited global flag filter. Commit `50986f3` maps
those deployments to global status. The corrected run excludes affected laps,
uses the same forecast parameters and acceptance criteria, and reuses the
already opened race archives. The preliminary results remain available.
[Preliminary results](compound-v3-preliminary-results.json)

| Corrected holdout | Scored blocks | Observed | Predicted | Matched | Pace MAE | Persistence MAE |
|---|---:|---:|---:|---:|---:|---:|
| Bahrain | 16 | 6 | 2 | 2 | 0.840 s | 0.714 s |
| Spain | 17 | 6 | 4 | 2 | 1.140 s | 0.630 s |

The candidate missed the recall and pace error gates in both races. Close-traffic
share MAE was 0.386 and 0.303 respectively. The corrected result reproduced
byte for byte. Future intervals were used to score traffic predictions.
R041 remains open. The observed traffic association from the diagnostic has
limited predictive value when future exposure must itself be forecast.
[OpenF1](https://openf1.org/) | [Corrected results](compound-v3-results.json) | [Source archive hashes](compound-v3-archive.json)
