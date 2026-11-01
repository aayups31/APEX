# R036 simulated-expert demonstration contract

The [R036 protocol](../../research/protocols/IMITATION_DRIVER.md) and
[sequencing/source ADR](../architecture/adr-0008-conditional-imitation.md) govern
this research dataset. It does not create observed steering channels in R033.

## Source conditions

The immutable parent is accepted R035 study
`58a8e7a318e12c0db80a9c70c2dfffb6fd5818534a15fa657a8e33d6b0b49ae0`, with calibration
`2dc610c27b9219caf53759c0d8f1211a8b5d492b82758c04743997e099059b1e`.
It carries the accepted R033 native cohort and supplied R029 registered curves.
The first two frozen source laps per event/driver define16 initial conditions:
eight2023 training, four2024 Bahrain validation, four2024 Monza test.

Each training condition is simulated nominally and with a signed initial lateral
offset.4m/heading.01rad. Driver4 uses positive signs,44 negative; these are declared
experimental perturbations, not observed events. Expert collection has16 episodes;
learner collection adds16 training-only episodes. Test has eight nominal/disturbed
cases; four additional nominal refinements use smaller integration steps.

Initial scalar speed is the first accepted native car observation. Initial pose
comes from the map and initial body lateral velocity/yaw rate are zero PRIOR.
Full initial measured chassis state is unavailable. The car/aero and propulsion
assumptions remain generic PRIORS; frozen pace remains fraction.65/cap60m/s.

## Features and labels

| Raw feature | Meaning/unit | Truth |
|---|---|---|
| v²/3600 | speed squared divided by(60m/s)² | SIMULATED, prior scaling |
| 50*kappa | current curvature times50m | RECONSTRUCTED supplied map |
| 50*kappa_preview | known-map curvature at s+tau*v | RECONSTRUCTED map, SIMULATED query |
| velocity heading error | wrapped tangent minus velocity direction, rad | SIMULATED relative to map |
| cross-track atan | atan(.8*e_y/(v+5)), rad | SIMULATED, declared prior gains |
| yaw error | v*kappa-r, rad/s | SIMULATED relative to map |
| body sideslip | atan2(vy,vx), rad | SIMULATED |
| previous steering | last applied road-wheel angle, rad | SIMULATED actuator memory |

Target is expert raw-steering minus R035 raw-steering, radians, labelled
`SIMULATED_EXPERT; NOT_MEASURED_HUMAN`. No event/driver identity, absolute XY,
absolute station, future native source row or expert answer is an inference input.
Future known-map preview is a declared supplied condition available to every method.

## Weights, stages and integrity

Training rows retain episode index, source condition ID, event/driver/role,
collection round, state, local projection, previous applied action and raw expert
label. Every episode gets equal total weight within its round, rounds equal
weight; the balanced catalog makes event/driver/lap/disturbance weights equal.
Dense native/simulated rows cannot dominate merely through row count.

`inputs.json` guards the complete catalog before binary access. A public profile
must match the accepted source seals and exact regenerated case catalog; a smoke
profile is explicitly simulated and cannot close the task. The role check occurs
again at the initial-speed payload boundary and before fitting/aggregation.

The prepared dataset, development package and final evaluation each have separate
exclusive summary/manifest seals. Development contains all candidate weights,
train-only normalizers, full trial paths and base/aggregated arrays. Final
evaluation copies the frozen development and its full dynamics-replay receipt.
No failed case is replaced, no test labels enter fitting and no immutable package
is overwritten. Protected benchmark headers, unsafe identifiers, tampered files,
resealed false model choices and false completion are rejected by their declared
guards and scientific verifiers. Raw provider data stays in local immutable caches;
published evidence contains conditions, metrics, weights and hashes.
