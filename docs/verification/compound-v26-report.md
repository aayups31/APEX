# R041 stint-state forecasts and driver controls

The asymmetric stint-state forecast passes 5 of the 24 supported development
races. The corrected nomination/practice ridge passes 9. All 393 comparisons
are included. Four other opened races have zero eligible comparisons.

| Forecast | Races passing | Race-averaged mean absolute contrast error |
|---|---:|---:|
| Corrected nomination/practice ridge | 9 / 24 | 0.444 s |
| Stint state with symmetric observation noise | 3 / 24 | 0.558 s |
| Stint state with asymmetric observation noise | 5 / 24 | 0.557 s |

The model estimates current pace and drift from laps completed before the
forecast. It uses a compound drift prior from other races and allows
occasional unusually slow laps. This is an adaptation of the published
stint-reset idea for the APEX horizon. The paper used Bayesian sampling,
within-race next-lap prediction and assumed fuel loads. APEX uses a finite
pace-and-drift grid, its existing fuel correction and whole-race exclusion.
Sequential and batch inference agree on every candidate forecast.
[Paper](https://doi.org/10.1177/22150218261446170),
[registered experiment](../../research/protocols/COMPOUND_STINT_STATE_V26.md),
[forecasts and race gates](compound-v26-development.json).

Across fuel-stable decisions, the asymmetric forecast missed 44 crossings
and raised 37 false alarms across the two labels. Both metrics count
label decisions, so a comparison can contribute twice.

## Does a driver's pace difference persist?

For a pair of drivers racing on the same compound, APEX measured their
earlier pace difference using at least six matched clean laps. It then
predicted the median gap on three later laps. With both target stints
excluded from calibration, 242 comparisons across 24 races qualified.
The historical driver offset gave 0.431 s of race-averaged absolute error.
The latest three laps gave 0.551 s and predicting zero difference gave
0.606 s. Historical offsets improved on the prefix in 16 of 24 races.
These gaps include both driver and car effects, and observations share laps.
[Negative-control results](compound-driver-control-check.json).

On different compounds, 49 directly controlled comparisons across seven
races qualified. An offset learned from other races for the same relative
compound pair gave 0.430 s of error, versus 0.381 s for the driver offset
alone and 0.573 s for the prefix. Adding the compound adjustment improved
on the driver offset alone in one race. Every test race had training
support for its compound pairs, although 38 of the 49 cases came from two
races. These results support a causal driver control in a limited setting.
The relative compound gap still transfers poorly in this sample.
[Transfer protocol](../../research/protocols/COMPOUND_DRIVER_TRANSFER.md),
[per-window forecasts](compound-driver-transfer.json).

## Can the earlier peer predict the subject's future laps?

The preregistered v27 model uses the driver's historical pace offset to
adjust a peer's already completed laps on the target compound and ages.
It found eligible peers for 129 of 393 cases. On the other 264 it used
the same ridge fallback. The combined forecast passed 7 of 24 races with
0.460 s of macro mean absolute error. The ridge alone passed 9 with
0.444 s. Both candidates remain unqualified.

Qatar 2025 and Singapore 2023 had zero eligible peer cases. With this
fallback, changing peer predictions cannot fix either race. Qatar recorded
no crossings and the fallback predicted none, but its pace error exceeded
reference persistence. In Singapore the pace error beat the references,
but the model called two crossings on the first definition and one on
the second when neither had an observed crossing. The nine-race failure
count obtained by substituting bounded observations on supported cases
is a diagnostic counterfactual. Only the two zero-support failures
establish a strict impossibility for this design.

An additional feasibility audit considered every mixture of the current
three-lap prefix and the three ridge projections, allowing a different
weight per case and even per label. It tested the endpoints and every
interior point at which two lap values exchange order. These points contain
the extrema of each piecewise-linear median. Even that favorable bound
cannot reach half the observed crossings for at least one label in five
races. In Hungary 2025, only two of fourteen primary crossings are reachable.
Adjusting a shared shrinkage weight per forecast cannot close R041.
[Per-race recall bound](compound-shrinkage-reach.json).

The next candidate needs to produce a different trajectory when the
current prefix and ridge both miss the direction change. Prioritize
additional independently observed fuel or tyre state, or test a model of
track evolution estimated from contemporaneous field laps across the
entire cohort. Use the five reachability failures as diagnostics alongside
the full 24-race evaluation. Keep fresh confirmation sealed until a
candidate clears the development gates.
[Peer protocol](../../research/protocols/COMPOUND_CAUSAL_PEER_V27.md),
[contributors, forecasts and gate audit](compound-v27-development.json).
