# R035 conditional transparent research driver

Component under evaluation; closure requires the complete frozen held-out lap
catalog and all independent/refinement gates. The
[preregistered protocol](../../research/protocols/TRANSPARENT_DRIVER.md) defines the
scope. This component stays in `apexsim.research`; it cannot advance the formal
maturity level or influence the production simulator.

## Inputs and generated behavior

The supplied frozen R029 registered reference curve is tabulated at<=2m spacing.
Its XY, tangent and curvature are RECONSTRUCTED. It is not surveyed road geometry,
measured boundaries or independent live localization. A lap begins at map origin
and tangent with observed initial speed; lateral velocity and yaw rate start at
zero PRIOR. The generic R032 mass/grip/stiffness/aero parameters remain PRIOR.

A map-only speed profile combines curvature/downforce grip and backward braking
reachability. Nine candidate lateral fractions and maximum speeds are compared
using native training and validation speed targets, matched to backward source
positions on the supplied offline map. Validation driver/lap weights are equal;
the test event is excluded. This estimates conditional pace, not uniquely
identified human driving style. The selection was frozen and pushed before test
simulation: fraction.65, maximum60m/s. Calibration seal:
`2dc610c27b9219caf53759c0d8f1211a8b5d492b82758c04743997e099059b1e`.

Steering uses understeer/geometric feedforward, velocity-heading error, lateral
error and yaw-rate feedback. Longitudinal feedback and profile feedforward produce
requested tyre force; the declared power, braking and conservative per-axle grip
limits produce applied forces. Road-wheel angle/rate projections are logged.
A geometry-only pure-pursuit baseline uses the same map/profile/force limits.

Generated controls are held for.1s. All six simulated chassis states evolve through
R032 Newton/Euler dynamics and implicit axle-load balance. RK4 substeps<=.02s are
checked at every intermediate stage; state/pose resets and state clipping are
absent. Local segment projection tracks unwrapped progress and rejects branch,
backward-progress or5m reference-corridor exits. That corridor is an experiment
tolerance, not an observed road boundary.

## Commands and outputs

```powershell
apexsim freeze-driver-calibration --open-loop .cache/r034-public-20261031 --output .cache/r035-calibration-NEW
apexsim verify-driver-calibration .cache/r035-calibration-NEW
# Review/freeze/push that choice before test simulation.
apexsim transparent-driver-study --calibration .cache/r035-calibration-NEW --output .cache/r035-study-NEW
apexsim verify-transparent-driver .cache/r035-study-NEW
```

Fresh destinations are required. Source snapshots, parameters, calibration labels,
case catalog, applied actions, states, reference errors, actuator interventions,
failure prefixes, timestep comparisons and independent scalar replay are saved.
The verifier distinguishes exact inventory integrity from tolerant scientific
regeneration. Complete-lap independent replay uses bisection/DOP853 and no primary
force or RHS helpers.

## Limits

Public sources lack measured steering/body lateral state/fuel/battery and do not
identify the full car. The offline reference is supplied, the generic vehicle is
not calibrated across braking/cornering, and speed targets inherit map/source
uncertainty. Four lap conditions on one reused development event cannot establish
general racing capability. Time/speed disagreement with source laps is reported
descriptively and is not a real-car predictive acceptance metric. Multi-lap drift,
broader disturbances, OOD/fallback, tyres, fuel and ERS require later work.
