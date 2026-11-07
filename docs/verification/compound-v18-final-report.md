# R041 race-context review

R041 remains IN_PROGRESS. Its prediction acceptance gate fails. R042 remains
downstream. The original 392 comparisons, 24 supported races, two label
definitions and prospective confirmation requirement apply.

| Fixed model | Passing races | Macro error, seconds |
|---|---:|---:|
| V13 nomination control | 9/24 | 0.409208 |
| V15 timing-line proximity | 7/24 | 0.423592 |
| V16 completed-peer feedback | 9/24 | 0.397728 |
| V17 pre-race practice | 11/24 | 0.423670 |
| V18 race phase control | 10/24 | 0.435349 |
| V18 race phase plus feedback primary | 8/24 | 0.427541 |

Practice observations cover all 28 opened weekends through 23 FP2 and five FP1
sessions. The frozen filters retain 384 six-lap blocks. Both compounds have
field support for 233 comparisons. The subject driver has practice support on
both compounds for only two comparisons. The practice model improves race
count while worsening average error relative to v13.

Peer feedback becomes available for 129 comparisons. Even perfect predictions
on those supported cases leave six races failing. This diagnoses a coverage
limit for the registered correction. It does not prove that other methods
cannot predict these races.

The existing R021 fuel sensitivity coefficients of 0.020, 0.030 and 0.040
seconds/kg change at least one crossover definition for 144 comparisons across
23 races. Of the 91 original primary crossovers, 63 change their classification
somewhere in that range. This demonstrates dependence on assumed fuel effects.
It does not establish which fuel assumption is physically correct. All model
scores above use the original 0.030 coefficient.

The independent scalar audit reconstructs 1,176 forecasts and 144 race-label
gates for v15-v17. V18 has an additional independent gate reconstruction in its
regression test. Native timing-line extraction and offline practice acquisition
replay exactly. Practice source snapshots occupy about 8.4 MB locally under
.cache/r041-v17-practices. Their sealed source bindings and extracted long-run
observations are committed. Permanent reservations and fresh confirmation race
outcomes remain closed.

The v18 protocol ends this sequence of combining the opened timing observations
after failure. Further progress requires a distinct input with measured
coverage and predictive value. The next investigation is forecast-time driving
state from recorded throttle, brake and speed observations, followed by a
registered full-cohort comparison. Actual fuel and tyre state remain unknown.
Development qualification and separate prospective confirmation are required
before closing R041.

Reproduce the latest model with
`python research/scripts/diagnose_compound_phase.py --output <fresh-path>`.
The source matrix, package builds and simulator checks are verified in GitHub
CI. The machine-readable project status records the final verified source run.
