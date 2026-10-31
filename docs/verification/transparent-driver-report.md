# R035 conditional transparent driver evaluation

2026-10-31. Numerical campaign decision **ACCEPT_CONDITIONAL_RESEARCH_DRIVER**.
This component demonstrates generated-action, closed-loop path tracking in the
generic-prior R032 six-state car. It does not establish measured full-car replay,
accurate F1 pace, surveyed road containment or formal R4 maturity. Foundation
remains R1 and production kernel R0.

## Frozen inputs and selection

The [protocol](../../research/protocols/TRANSPARENT_DRIVER.md) was committed before
calibration. The [calibration summary](transparent-driver-calibration-summary.json),
[all nine candidate results](transparent-driver-calibration.json) and
[unaltered lap catalog](transparent-driver-lap-catalog.json) were pushed in
`06d34f8e0ccbc1dc6e5fe1efd9279eb6b265d564` before any public simulated-lap result.
There was no test-driven retuning or failed-case replacement.

The accepted R03388-lap source snapshot and R029 Bahrain/Monza reference curves
are supplied offline conditions. Training/validation calibration uses22,531
matched native speed/reference-position rows from68 laps:2023 development events
train;2024 Bahrain validates. Test labels from2024 Monza are excluded. The nine
pace candidates combine fractions {.35,.5,.65} and caps {60,80,95}m/s. Equal-lap/
driver validation speed-profile MSE selects fraction.65/cap60m/s. Its validation
RMSE is16.496604m/s. This weak pace fit is explicitly conditional on generic grip,
aero, the map and braking prior; it is not identified human style or physical-car
calibration. Nine permanent benchmark events remain untouched.

Calibration seal:
`2dc610c27b9219caf53759c0d8f1211a8b5d492b82758c04743997e099059b1e`.
Study seal:
`58a8e7a318e12c0db80a9c70c2dfffb6fd5818534a15fa657a8e33d6b0b49ae0`.

## Generated-action lap results

The first two frozen Monza laps per driver are the complete mandatory test catalog.
Every nominal case completed without state resets, clipping, teleports, fabricated
recorded steering or a forced path constraint. The simulated speed, steering,
forces, body lateral velocity and yaw all evolve through actual R032 integration.
The map is supplied; initial speed is observed; initial lateral/yaw velocity is
zero PRIOR and subsequent state is SIMULATED. Generic car/aero parameters are not
estimated from unavailable chassis measurements.

| Source lap condition | Simulated finish(s) | Maximum reference error(m) | P95 error(m) | Source lap time(s) |
|---|---|---|---|---|
| Monza2024 /4 /lap2 | 133.582425 | .325421 | .233591 | 85.458 |
| Monza2024 /4 /lap3 | 133.583387 | .325922 | .234154 | 85.110 |
| Monza2024 /44 /lap2 | 133.584081 | .326161 | .234582 | 86.043 |
| Monza2024 /44 /lap3 | 133.586633 | .325604 | .235154 | 85.630 |

All four pass the frozen300s finish, maximum5m and P95<=2m gates. Four analogous
Bahrain validation conditions also complete:149.0227–149.0945s, maximum error
<=.339793m. The geometry-only pure-pursuit baseline completes all four Monza cases
with the same profile and force limits; maximum error2.83098–2.83156m and P95
1.57397–1.57656m. Both successes are retained; the feedback controller tracks the
supplied map more closely. Neither case set establishes population generalization.

Across all16 nominal/validation/baseline/refinement runs, maximum squared friction
utilization is.608357, minimum contact load3678.531539N, maximum pitch residual
1.01509e-8Nm and maximum power identity error9.31323e-10W. Every intermediate RK4
stage is checked. Angle/rate and force-envelope actuator interventions are logged;
they act on controls/forces and do not modify chassis states.

## Numerical and independent checks

Controls are held for.1s and RK4 substeps are at most.02s. All four held-out
feedback cases are repeated with.01s substeps. Maximum common-station differences
across those cases are.000070433m in XY,.000045527m/s in speed and.000004355s in
finish time, well below the unchanged.5m/.5m/s/.2s gates.

The independent R032 scalar tyre/load-bisection/DOP853 implementation replays one
complete held-out lap with1336 held-action intervals. Maximum XY difference is
.002084195m, body-velocity difference.000038197m/s, heading difference.000002759rad
and yaw-rate difference.000026832rad/s. This independent replay uses no primary
force, load root or RHS helpers. Thirty-two representative intervals across all
four nominal held-out conditions also pass. The full-lap tolerance is.05m and
.01m/s; neither threshold was changed after results.

## Pace limitation and truth boundary

The simulated laps are47.54–48.47s slower than their source lap times. Post-evaluation
native-speed comparisons at matched backward reference stations give RMSE
24.76–25.26m/s, with a negative speed bias. These source comparisons do not enter
calibration or feedback. They are descriptive discrepancies, not successful
real-car predictive validation. The public observation layer has0% complete
measured bicycle-state/control coverage; that fact remains unchanged.

Known-map preview, registration, generic tyre stiffness/grip, power/braking limits
and pace selection materially condition these results. The5m reference corridor
is an experiment tolerance, not road width. Thermal tyres, fuel/ERS, traffic,
unknown maps, multi-lap accumulated drift and broad recovery/OOD behavior remain
outside this component's acceptance scope.

## Reproduction

See the [model/run card](../models/transparent-driver-v1.md) and
[equation map](../../research/equations/TRANSPARENT_DRIVER_V1.md). Fresh output
directories are required. Calibration is frozen independently from evaluation;
changed controller code requires an explicit new freeze. Original artifacts stay
immutable. The final publication includes exact inventories and independent/
scientific replay receipts. Task closure additionally requires final regression
and Python3.11/3.12 CI; progress is registered in the live maturity status.
