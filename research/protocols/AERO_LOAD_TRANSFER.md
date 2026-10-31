# R032 aero balance and quasi-static load transfer

Frozen 2026-10-31 before implementation or R032 outcomes. **ADAPTATION,
SYNTHETIC evidence, GENERIC PRIOR parameters; research only.**

## A. Current state

Base 4927926005b663526b7fe9600557f44b205e68d0. R031's published full regression
has 634 passing tests; exact main CI 41222004204 passed Python 3.11/3.12.
A fresh full baseline passes 634 tests in610.78s with two existing dependency
deprecations (Python3.12.12/Windows), before physics implementation. The fresh
`bicycle-dynamics-study` and `verify-bicycle-dynamics` reference at
`.cache/r032-baseline-reference-20261031` passes, maximum reload difference 0,
summary seal `333a0930fb714f6120be3046f9100d44f9981ada1de67ce77c06fe024b01f5d4`.
Research foundation R1, kernel R0. R030/R031 dependencies are complete.

## B. Scope

Add aero drag/downforce and front/rear aero balance to the R031 planar axle
model, with self-consistent quasi-static longitudinal load transfer. Report
sensitivity and structural identifiability. Preserve R031 behavior/source and
production interfaces. No suspension dynamics, lateral roll transfer, four-wheel
loads, ride-height map, DRS calibration, thermal tyre state, observed-car fit or
production promotion. R033 alignment and R034 predictive errors are separate.

## C. Sources and priors

Master guide sections 8/9/11/15/16, maturity model, R032 backlog, R031 equations,
vehicle/tyre optimal-control protocol and replication standard. The Newton/Euler
pitch balance below is derived explicitly. Dynamic-pressure force law:
[NASA drag equation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/drag-equation/)
(read 2026-10-31). [CommonRoad dynamic bicycle](https://optimal-control-ad-personal-repos-bb7de67c51e7f51ec3bda98b62f32.pages.gitlab.lrz.de/explanations/vehicle_dynamics/db/)
provides the load-transfer reference; this adaptation solves actual constrained
tyre-force balance instead of inserting commanded acceleration into axle loads.
No reproduction claim for CommonRoad, Perantoni/Limebeer or Pacejka.

R031 vehicle defaults remain priors. New defaults: air density 1.225 kg/m³,
effective CdA=1.1 m², downward ClA=3 m², front downforce fraction beta=.45,
CoG height h=.30 m. Drag acts at CoG opposite the body velocity vector; additional
`BicycleControl.resistance_n` also acts at CoG along negative body x. No wind,
grade, vertical velocity or pitch acceleration. Effective coefficient-area
products are explicit; no absolute Cd or Cl is inferred. No raw or benchmark
data are needed for this equation/sensitivity task.

## D. Equations and implementation

Use R031 six-state/body-frame conventions and road-wheel force requests.
V=sqrt(vx²+vy²), q=.5*rho*V², D=q*CdA, Z=q*ClA (downward).
Drag vector is `-D*[vx,vy]/V`, with zero yaw moment at CoG.
Total normal load N=m*g+Z. Let T_x be the total constrained tyre force along
body x, including the rotated front lateral force. Quasi-static pitch balance:

`Fzf = m*g*b/(a+b) + beta*Z - h*T_x/(a+b)`; `Fzr=N-Fzf`.

Equivalently, the downward aero center is x_cp=beta*(a+b)-b relative to CoG,
and `-a*Fzf+b*Fzr+x_cp*Z-h*T_x=0`. External drag/resistance at CoG has no pitch
moment. Transfer therefore depends on tyre force, not net acceleration with drag
subtracted a second time. This contact-patch/force-height convention is explicit.

Tyre forces use R031's axle ellipse/tanh law evaluated at the solved loads.
Solve `g(Fzf)=Fzf-base+h*T_x(Fzf)/(a+b)=0` on
`[minimum_contact_load,N-minimum_contact_load]`, default minimum 1 N.
For uniqueness, enclose every possible root in
`I=[base-h*Tmax/L,base+h*Tmax/L]` intersected with the contact domain, with
`Tmax=(mu_x+mu_y*abs(sin(delta)))*N`. On I, the rear Fx slope is <=mu_x.
For steered front forces: if the request is fully saturated throughout I, the
front body-x slope is <=mu_x*abs(cos(delta)); if fully unsaturated throughout I,
the slope is <=mu_y*abs(sin(delta))/sqrt(1-(Fx_req/(mu_x*I_lower))²).
Require h/L times the summed front/rear bounds <.9. At zero steer use2*mu_x;
at zero h the load is explicit. If the front saturation threshold crosses I,
abstain. These are conservative sufficient conditions, not global stability.
This corrects the initial draft's constant lateral-slope bound during algebra
review before study outcomes: a fixed-Fx ellipse has an unbounded normal-load
slope near partial saturation. No numerical accuracy gate is changed.
No bracket means loss of contact/support; reject rather than clamp loads.
Use Brent root solve, xtol1e-9 N, rtol1e-12; report force/moment residuals.

Body wrench adds drag vector and supplied resistance. Preserve exact kinetic
power identity, including `-D*V` drag work. No artificial normal-force work on
the constrained flat plane. Independent scalar equations use bisection instead
of the primary force helper/Brent solver. No R030 power/drag input is accepted
here: adding aero drag to a fitted law that already contains drag is ambiguous.

New modules: `research/aero_bicycle.py`, independent audit, sensitivity study,
unit/artifact tests, immutable CLI study/verify/audit and report/card/equation map.
Source snapshots, config, runtime, every case and array are saved. No R031
refactor or production file change is needed.

## E. Acceptance and stopping gate

1. Hand load fixture at vx50, vy/r/delta0, m900, a1.6, b2, h.3,
   Fxfront900/Fxrear1800: downforce4593.75 N, drag1684.375 N,
   Fzf6747.1875 N, Fzr6675.5625 N. Errors <=1e-8 N.
2. Per-axle load sum error <=1e-7 N, pitch residual <=1e-6 Nm, ellipse
   utilization <=1+1e-12, lateral dissipation <=1e-9 W. Drive unloads front;
   braking loads front. Aero center shifts loads correctly; q scales with V².
3. Independent bisection loads/wrench agree within 1e-7 N / 1e-7 SI RHS units.
   Zero-aero/zero-height RHS and trajectories match original R031 to 1e-8.
   Exposed contact-loss and nonunique-support fixtures must reject explicitly.
4. Coast/drive/brake/left/right/combined-brake/pulse synthetic paths: RK4
   .02/.01/.005 s vs independent DOP853 (rtol1e-11,atol1e-12) <=1e-4 in each
   six-state SI component; .01/.005 differences <=1e-4. Force/power residual
   <=1e-6 W absolute, 1e-10 relative. No state/load clipping.
5. Publish one-at-a-time ±20% CdA/ClA/h and beta±.1 trajectory/load sensitivity,
   retaining every failure. This is a prior-model experiment, not fitted response.
6. Structural oracle: at speeds20/40/70 m/s and known unsaturated tyre Fx
   {-2000,0,2000} N, observations [drag,Fzf,Fzr]. Relative-parameter Jacobian
   for [rho,CdA,ClA,beta,h] has expected rank4/5, with null direction
   [1,-1,-1,0,0]; fixing density gives rank4/4. At zero tyre Fx, height is
   unidentifiable. Drag-only longitudinal observations have rank1. Analytic
   Jacobian vs central differences error <=1e-5 after declared normalization;
   product-preserving rho*1.1, CdA/1.1, ClA/1.1 changes observations <=1e-8.
   Oracle axle forces/loads are unavailable in public data: no real-parameter
   identification or confidence interval is claimed.
7. All unit/integration/artifact tests and CI pass; replay regenerates all
   results with rtol1e-7/atol1e-8 while stored hashes remain exact. Relocation,
   byte tampering, resealed false gates/trajectories and numeric tolerance tested.

Completion requires the sensitivity/identifiability report and acceptance
artifacts in Git, with full applicable regression and documented limitations.

## F. Risks

Static pitch equilibrium omits suspension/vertical dynamics and lateral transfer;
fixed axle stiffness omits load-dependent tyre stiffness. Missing mass, wind,
force/steering/ride-height measurements prevent actual F1 identification.
Grip/load coupling may lose contact or sufficient uniqueness support; abstain.
No synthetic agreement establishes full-car or closed-loop validity.

## G. Order

Commit protocol; implement/test load solver; push; implement independent dynamics
and sensitivity; push; publish inspected evidence; complete R032 gate, then R033.
