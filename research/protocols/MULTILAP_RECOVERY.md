# R037 continuous multi-lap compounding-error and recovery benchmark

Preregistered2026-11-01 before new controller simulation. Engineering ADAPTATION.

## A. Current state

Base9e77601723a16eaab0df7453541ab96ac2311c53;713 tests and all artifact workflows
pass Python3.11/3.12 in CI41355474238. A fresh local full baseline is running;
its result must be recorded before closure. Fresh R036 smoke reference and full
replay pass (seal ccb3c8b922b832934ad01de057ad943e890f2f4bcb5b02fb95e185d5103f6b7a).
Its failed improvement gate remains SIMULATED_EXECUTION_ONLY. Research foundation
R1, production kernel R0; R035/R036 are accepted conditional research components.
Real-car full-state replay, pace calibration and formal R4 remain unavailable.

## B. Scope and dependencies

R037 depends on the accepted R036 frozen driver and R032 physics. Test continuous
multi-lap drift and recovery; do not retrain, change pace, reset states at lap seams
or promote production. R038 follows successful R037 evidence.

## C. Inputs and truth

Use accepted R036 evaluation seal
2f549c5224413fde09f5d99af2043305c5cac81ce49daa9afd9647a2be4264ae and its complete
event-guarded parent. All four2024 Monza source initial conditions remain the
test catalog. Known reconstructed maps and initial scalar source speed are supplied;
subsequent chassis states/actions and interventions are SIMULATED, vehicle PRIOR.
Nine reserved benchmark events remain untouched. Reusing development events is
explicit, not a new independent population. No historical row beyond initial
speed enters deployment. Research5laps; simulated smoke3laps, never task eligible.

## D. Implementation and equations

Keep R035/R036/R032 accepted files unchanged. New research runner uses the same
sample-and-hold100ms commands, RK4<=.02s, actuator/force equations and local map
projection. Station is unwrapped; pose, body states and actuator memory continue
across every seam. No chassis state clipping or resets. Frozen pace.65/60m/s.
Compare R035 transparent and frozen R036 learned policy on nominal, positive and
negative road-wheel disturbance cases. A pulse adds +/-.01rad to generated raw
steering for five commands at first crossing of1.25L and3.60L (smoke2.60L for
second pulse). Reapply the common physical actuator/force equations using actual
steering and memory; report interventions. Pulses are declared exogenous action
disturbances, not measured steering or state teleports. The .3rad/20-command
positive challenge on the first condition is retained, including failed prefix;
it is a challenge outside the required recovery envelope and cannot be substituted.

## E. Stopping gate and reporting

Exact required catalog:4conditions*2actors*3scenarios=24 runs plus4 learned nominal
refinements at.01s. Every required run completes five continuous laps within
300s/lap, monotone station, finite supported physics, per-lap RMSE<=.5m,
P95<=1m, maximum error<=2m. Last-lap RMSE minus first-lap RMSE<=.1m.
Friction utilization squared<=1+1e-12, positive contact, pitch residual<=1e-6Nm,
power identity error<=1e-6W. Speed/force/angle limits remain unchanged.
Each pulse must occur and recover within10s after pulse end: lateral difference
from its same-actor nominal common-station path<=.15m continuously for2s.
Report per-lap RMSE/P95/maximum/finish, same-phase state drift and recovery time;
station metrics use2001nodes/lap. Absolute reference corridor is experimental,
not measured road width. Nominal learner completion no more than1% slower than
transparent baseline; no credit for slowing the controller.

Refinements: common-station XY<=.5m, speed<=.5m/s, finish difference<=.2s over
the full horizon. Independent scalar-load-bisection/DOP853 held-action replay:
one complete five-lap learned nominal path plus representative intervals including
seams and post-pulse states; XY<=.05m/body velocity<=.01m/s. This is held-control
numerical verification, separate from autonomous recovery. Full deterministic
regeneration checks every required/challenge path, metrics, arrays, exact catalog,
source snapshots and false completion (atol1e-8/rtol1e-7). Publish receipts, plots,
data/component cards and failures; pass full regression/CI before DONE.

## F. Risks

Known-map/perfect simulated localization, generic tyres/vehicle, stationary grip,
no fuel/thermal evolution, one reused test event and finite signed pulses limit
interpretation. Five laps do not establish race-distance or arbitrary recovery.
R038 support/fallback and real-car calibration remain separate gates.

## G. Execution order

Record baseline; freeze protocol; implement runner/metrics and adversarial tests;
commit/push; freeze accepted input/catalog/source; run complete test/challenge,
refinement and independent audits; push primary evidence; regenerate all outputs;
publish limitations and regression; close only after every required gate passes.
