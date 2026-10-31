# R031 bicycle dynamics and combined grip v1

Preregistered 2026-10-31 before implementing or evaluating the R031 model.
Classification: **equation-level ADAPTATION with SYNTHETIC evidence**. No public
cornering calibration, paper reproduction or production promotion.

## A. Current state

Baseline a9c17cb337e82a596af45635c5700b465378e299: 607 tests pass in 339.46s,
two existing dependency deprecations (Python 3.12.12/Windows). Tests run from
`apex_engine`. An initial root-directory invocation failed relative config paths;
this was an invocation error, corrected without source changes. Reference:
`python -m apexsim.cli longitudinal-calibration-smoke --output
.cache/r031-baseline-reference-20261031`; saved replay difference 0 m/s;
independent DOP853 difference 3.769e-9 m/s. Reference summary seal
`380e16964c2f803787ffe3821acfc1efd679f1cca93837d6f95dc997c7902452`.
R030's public gate is complete. Research foundation R1, production kernel R0.

## B. Scope

R031: planar dynamic bicycle in `apexsim.research`, static axle loads, actual
road-wheel steering angle, forward body velocities, yaw and inertial position;
longitudinal-priority axle friction ellipses and explicit applied/requested force
diagnostics. No changes to the production state/action contract or its normalized
steering proxy. No aero/load transfer (R032), recorded state alignment (R033),
lap calibration, driver/controller, thermal states, wheel spin, braking calibration
or planner. Synthetic force requests are inputs, not observed actuators.

## C. Sources and truth

Master guide sections 8/9/11/15/16; maturity model; research backlog R030–R034;
`VEHICLE_AND_TYRE_OPTIMAL_CONTROL.md`; existing longitudinal model and state/action
contract. Equation basis: rigid-body planar force/moment balance and the
[CommonRoad dynamic bicycle equations](https://optimal-control-ad-personal-repos-bb7de67c51e7f51ec3bda98b62f32.pages.gitlab.lrz.de/explanations/vehicle_dynamics/db/)
(read 2026-10-31: body-frame velocities, slip and yaw equations). Adaptation uses
N/rad axle stiffness, static loads, explicit wheel-frame longitudinal forces and a
bounded tanh lateral law instead of that reference's linear load-scaled force law.
This is not the nonlinear four-wheel Perantoni/Limebeer model, Pacejka Magic
Formula or a reproduction of either paper. Those remain research-family context.

Every parameter is a declared generic PRIOR or SYNTHETIC fixture. Defaults:
m=900 kg, Iz=1500 kg m², a=1.6 m, b=2.0 m, g=9.81 m/s²,
Cf=100000 N/rad, Cr=120000 N/rad, mux=1.5, muy=1.7.
These are not identified F1-car parameters. Flat road, no wind/aero/grade.
No public/raw or reserved-benchmark inputs are read; no training/test split or
prediction interval is asserted. R030 integration is an explicit straight-only
force-decomposition consistency check using a supplied SpecificPowerDrag model;
no claim that its effective force coefficients identify lateral mass or grip.

## D. Equations and interfaces

Right-handed body x forward, y left, z up; positive heading/yaw/steering is left.
State order `[x_m,y_m,heading_rad,vx_mps,vy_mps,yaw_rate_radps]`.
Control: front steering delta rad, requested front/rear wheel-frame Fx N,
nonnegative opposing body-x resistance N. Controls held left-constant over each
supplied time interval. No future controls or observed-state resets.

Static Fzf=mg*b/(a+b), Fzr=mg*a/(a+b).
Front wheel velocity is rotation by -delta of `[vx,vy+a*r]`; rear `[vx,vy-b*r]`.
Slip alpha=atan2(wheel lateral velocity,wheel forward velocity).
For each axle: qx=mux*Fz, qy=muy*Fz;
Fx=clip(request,-qx,qx), B=qy*sqrt(max(0,1-(Fx/qx)^2));
Fy=-B*tanh(C*alpha/B), with Fy=0 at B=0.
Only the real force constraint clips; record requested/applied force and reduction.
Do not clip states, rates or steering. This is a longitudinal-priority empirical
combined-slip adaptation, not an identified tyre law or optimizer projection.

Rotate front forces into body axes. Body wrench gives
`vx_dot=r*vy+Fx_body/m`, `vy_dot=-r*vx+Fy_body/m`,
`r_dot=(a*Fyf_body-b*Fyr)/Iz`, plus exact inertial kinematics.
Return kinetic-energy rate and wheel-frame power terms for independent balance.
RK4 with requested max step <=.02 s; validate initial, intermediate and final
states. Domain PRIOR: vx in [5,110] m/s, |atan2(vy,vx)|<=.35 rad,
|r|<=2 rad/s, |delta|<=.35 rad, each |alpha|<=.5 rad, forward wheel velocity>0.
Reject nonfinite values, unsupported states, bad times and invalid controls;
never silently use a low-speed blend or stabilizing state limiter.

## E. Evaluation and stopping gate

Freeze these tests before running; all are mandatory:

1. Static load/moment and hand force fixtures to 1e-9 absolute (SI).
2. Ellipse utilization <=1+1e-12; lateral slip power <=1e-9 W over
   Fz {500,1000,5000} N, mux {.7,1.5}, muy {.8,1.7},
   alpha {-.3,-.05,0,.05,.3}, Fx fraction {-2,-1,-.6,0,.6,1,2}.
   Stronger longitudinal demand reduces available lateral force; full capacity
   leaves zero lateral force. Braking/drive and left/right signs are symmetric.
3. Rigid-body/wheel power identity relative 1e-10, absolute 1e-7 W; no-input
   kinetic energy nonincreasing to 1e-6 J per output node. Nonzero-steering
   front longitudinal rotation and yaw moment must be independently tested.
4. Straight constant-force analytical position/speed to 1e-9; R030 straight
   unsaturated instantaneous acceleration agreement to 1e-10 m/s², and speed
   trajectory agreement <=1e-6 m/s, explicitly within its original domain.
5. Analytic small-angle 2x2 lateral Jacobian matches finite differences to
   1e-5 absolute; default real eigenvalues' maximum <0 at speeds
   {5,10,20,40,70,100,110} m/s. A deliberately oversteering fixture must expose
   positive eigenvalue rather than conceal instability.
6. At 20/40/70 m/s and steering 1e-4 rad, nonlinear vy/yaw-rate agree with
   independently integrated linear small-angle response within 1% relative
   (1e-6 absolute). Zero-steering disturbance at 40 m/s must decay by at least
   90% in vy/r magnitude over 6 s; this is open-loop response, not R4 driving.
7. Fixed cases: coasting straight; drive; braking; left/right steering;
   combined braking/steering; near-limit drive/steering; steering pulse;
   initial lateral/yaw disturbance; small-angle cases. Compare RK4 .02/.01/.005
   and independently coded DOP853 (rtol1e-11/atol1e-12).
   Every six-state component differs <=1e-4 SI units against DOP853 and
   <=1e-4 between .01/.005. Report regime, utilization, constraint projection,
   limits, runtime and errors per case; retain all failures.
8. Reproducible immutable CLI evidence with source/config/array hashes, runtime
   versions, protocol snapshot, independent replay, relocation and tamper tests.
   Exact file integrity is separate from numerical replay tolerance (rtol1e-7,
   atol1e-8). Regenerated gate decisions must match; resealed false evidence fails.

Completion means this scoped force/stability gate passes, all tests/lint pass,
artifacts are inspected and report/card/backlog are updated. No held-out accuracy
improvement is claimed: independent equations/linearization are the references,
and kinematic bicycle is only an explanatory comparison, not measured truth.

## F. Risks

Generic mass/stiffness/grip are not public-data identified. Axle/static-load model
omits four-wheel transfer and aero; it is unsuitable for F1 high-g validation.
Longitudinal priority can erase cornering force and create unstable motion;
diagnostics and support rejection expose this. Tanh is a smooth prior, not a
physical tyre fit. Forward-only model must abstain at low speed/high slip.
Synthetic stability is parameter/domain conditional; it cannot establish full-lap
or closed-loop safety. Never pass it directly to a planner or race kernel.

## G. Execution order

1. Commit this frozen plan; mark R031 IN_PROGRESS.
2. Implement unit-labelled forces, states and wrench with hand/invariant tests;
   commit/push a passing milestone.
3. Add bounded integration, linearization and R030 consistency; test and push.
4. Add independent solver and immutable evidence CLI/replay; test and push.
5. Run declared cases, inspect outputs, publish evidence and limitations.
6. Run full regression and CI, close R031 only on acceptance, hand off R032.
