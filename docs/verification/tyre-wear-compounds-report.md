# R040 wear replay and R041 compound crossover evaluation

R040 converts lateral sliding work and tread temperature into a bounded consumed
fraction for each effective axle. For an interval with energy (E) in joules and
tread temperature (T) in kelvin, the dose is
`1e-7 * E * exp((T - 333.15) / 40)`. The remaining fraction decays by
`exp(-dose)`. Initial wear is zero in these replays. The rate and temperature
scale are research priors.

All four R039 thermal trajectories passed over 26,780 intervals. Wear increased
monotonically and the iterative update agreed with cumulative dose to within
2e-15 in consumed fraction. Doubling energy and raising tread temperature by
10 K both increased final wear. The simulated endpoints were approximately
0.295 front and 0.136 rear under the declared priors.
[Wear case results](wear-primary-results.json)

R041 fitted compound offsets and nonnegative age slopes on Bahrain, Australia
and Miami. Monza and Singapore provided held-out equal-age contrasts between
stints for the same driver. These contrasts still include stint-order, traffic
and track-evolution effects. The resulting coefficients estimate pace, while
physical wear calibration requires independent wear and energy evidence.

| Held-out event | Age contrasts | Matched crossover windows | Compound MAE | Shared-slope MAE |
|---|---:|---:|---:|---:|
| Monza | 219 | 0/12 | 0.548 s | 0.563 s |
| Singapore | 430 | 0/60 | 0.761 s | 0.717 s |

The R041 candidate failed the frozen crossover gate. The next candidate needs
better-controlled stint comparisons and an independent event evaluation.
[Frozen protocol](../../research/protocols/TYRE_WEAR_AND_COMPOUNDS.md) · [Compound results](compound-primary-results.json)

```powershell
python research/scripts/verify_tyre_wear_compounds.py --recovery .cache/r037-public-20261101 --thermal .cache/r039-thermal-20261103 --dataset .cache/tyre-dataset-20261011.json --output .cache/wear-compound-fresh
```
