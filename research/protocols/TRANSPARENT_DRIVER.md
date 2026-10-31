# R035 transparent conditional research driver

Frozen2026-10-31 before controller calibration or held-out simulated laps.
Physics/control ADAPTATION. This is a **conditional research controller**, not
observed human steering recovery, calibrated full-car dynamics or R4 promotion.

## A. Current state

Baseline and maturity are as in R034. R031/R032 independently tested planar
equations are available; public R033 has0% complete measured bicycle input
coverage. R034 supplies supported replay/error accounting and explicit unavailable
full-car scopes. Transparent driver code may be researched without deploying or
promoting its generic-prior vehicle. Complete real-car replay remains unresolved.

## B. Scope

Calibrate transparent pace parameters from training/validation native speed
targets; generate road-wheel steering and longitudinal forces from current
simulated state and a supplied frozen map. Demonstrate complete held-out
lap-conditioned rollouts in the six-state R032 vehicle, without recorded-speed
resets or forced path constraints. Report failures, source-time discrepancies and
controller limitations. No imitation/RL/MPC/world model, production change or
claim of human/team driving equivalence. R037/R038 broader robustness remains later.

## C. Inputs and truth

Use the same sealed R03388-lap cohort and R029 reference curves; event guards
before binary reads. Geometry is a supplied offline registered reference trace,
not surveyed road boundaries or independent online localization. Training uses
all2023 speed/reference-position targets; validation2024 Bahrain; test2024 Monza.
Controller and target-speed model must not consume test outcomes in calibration.
Known map preview is allowed; future recorded speed/control is not.

R032 vehicle/aero defaults remain GENERIC_PRIOR. Additional generic propulsion
prior:740kW*.92 effective power, brake ceiling40kN, rolling coefficient.015,
low-speed power divisor floor8m/s. No R030 calibrated law is extrapolated below
its support. Wheel steering bound.6rad is an explicit research prior; other
forward/sideslip/yaw/axle-slip bounds remain R031 defaults. Limit steering rate
to1.5rad/s and log actuator projections. Safe axle Fx requests are capped at.75
of conservative minimum axle longitudinal capacities, preserving lateral budget
and the R032 front-load uniqueness guarantee. No state/load clipping.

Map tabulation spacing<=2m. Use local continuous projection and unwrapped progress;
reject branch jumps, excessive backward progress or a >5m reference corridor.
The corridor is an experiment tolerance, not a measured road width. Initial XY/
heading comes from map start; vy/r=0 are labelled PRIOR, initial speed is observed.
Steering, throttle/brake and subsequent chassis states are SIMULATED.

## D. Transparent algorithm and calibration

Generate a map-only speed profile from
`v²*|kappa| <= f*mu_y*(g+.5*rho*ClA*v²/m)` and a maximum speed Vmax. Apply
a periodic backward braking envelope with prior planning deceleration6m/s².
No historical target is used to construct a test-map speed profile. Candidate
pace fractions f={.35,.5,.65}, Vmax={60,80,95}m/s. Fit/compare all nine using
training targets; choose by equal-driver validation speed-profile MSE, tie-break
slower maximum then lower fraction. This calibrates a conditional pace rule,
not driver style separately from uncertain vehicle/grip parameters.

Steering combines geometric/understeer feedforward and heading, lateral error,
yaw-rate feedback with declared prior gains. Understeer term:
`K=m/(a+b)*(b/Cf-a/Cr)`; feedforward delta≈`(a+b+K*v²)*kappa`.
Use actual velocity direction `psi+atan2(vy,vx)` for heading error. Default gains:
heading1.5, cross-track.8/s with speed softening5m/s, yaw feedback.15s.
Longitudinal proportional gain.8/s plus profile derivative feedforward generates
requested net acceleration, converted to drive/brake forces with aero drag counted
once and rolling resistance explicit. Pedal/force limits and steering/rate
projections are recorded. All feedback uses current simulated state only.

A simple geometry/pure-pursuit steering baseline shares the same map, speed
profile and force limits. [Coulter, CMU-RI-TR-92-01](https://publications.ri.cmu.edu/storage/publications/pub_files/pub3/coulter_r_craig_1992_1/coulter_r_craig_1992_1.pdf)
is the primary geometric reference (read2026-10-31); the dynamic feedback and
force-envelope adaptation is not a paper reproduction. No named racing-paper
magnitude claim is made. Record the baseline's failures as well as successes.

Freeze calibration before test simulation. Source-only test catalog: the first
two frozen2024 Monza laps by lap number for each driver4/44 (four nominal cases),
and analogous first two2024 Bahrain laps/driver for validation. No replacement
of a failed case. Two synthetic closed curves exercise controller signs/units
and disturbances before public evaluation, without inspecting test outcomes.

## E. Acceptance and stopping gate

All four held-out nominal map-conditioned laps must complete within300s, with
continuous simulated six-state dynamics, maximum reference error<=5m and95th
percentile<=2m. No chassis speed/pose resets, teleports or hidden state clipping;
force ellipses<=1+1e-12, positive contact loads, pitch residual<=1e-6Nm and power
identity<=1e-6W. Source observed lap time and speed-profile discrepancies must
be reported but are not real-car predictive acceptance claims under generic priors.
Keep source/event/driver identities and every unsuccessful run.

RK4 maximum substep.02s, held controller command every.1s; compare primary test
conditions at.01s: completion-time difference<=.2s, common-station maximum XY
drift<=.5m and speed difference<=.5m/s. Independently replay held applied controls
using R032 scalar bisection/DOP853; verify selected representative intervals and
at least one complete held-out lap, no primary RHS reuse (path tolerance.05m,
velocity.01m/s). Compare nominal baseline with identical information/limits.
Unit tests cover hand steering/force signs, map seam/local projection, rate and
force bounds, causal future-target independence, small disturbance recovery and
numeric refinement. Artifact tests cover frozen train/validation choice, protected
sources, immutability, relocation, tampering, false completion and scientific replay.

Full applicable regression/CI and published report/card/equation map required.
DONE means this declared conditional research-driver component completes its
held-out lap catalog. It does not establish full observed-car replay, surveyed
road containment, full R4 maturity or production promotion. If any mandatory
case fails, preserve failure and do not mark the task DONE merely for a prototype.

## F. Risks

Missing true steering/chassis/tyre/ERS states; generic vehicle priors; offline
geometry and pose conditions; controller exploitation of weak dynamics; source
map reuse; speed-profile fit confounded with grip/aero. Four cases and one test
event cannot support population generalization. Any protocol revision after
observing a failure must be explicit, versioned and retain the original outcome.

## G. Order

R034 report first; implement/test controller/map/limits on synthetic curves;
push; freeze source target calibration and selection; push before held-out
simulation; run complete case catalog and independent/refinement checks; publish
all outcomes; full regression; close only if every declared driver gate passes.
