# R029 frozen public-position reference-curve reconstruction

Preregistered 2026-10-19 at d695e29. Fresh baseline508 tests pass246.42s;
research26/73 DONE, build13/66, scoped researchR1/kernelR0. Preserve pre-existing
untracked artifacts/, output/ and tmp/. No production promotion in this slice.

## Scope and identity

Reconstruct a two-dimensional reference RACING TRACE, not a surveyed centerline
or track boundaries. Use already verified/offline-replayed FastF1 race archives:
Bahrain2024R01/2023R01 and Monza2024R16/2023R14. All are development events;
the nine permanent whole-event benchmarks remain excluded before native reads.
R021 mask d79966d3b13c06cb8a0bd6f6bcff1690a10965d6414e0e71840ecf6d7811d6a2
selects2024 laps. R026 mask28f947c68e71c1d97b61b52d3cfcdfed0b30fce801bad3f0ee49136fa61a966d
selects2023 laps. Masks and source bindings remain unchanged.

Per circuit: train the first3 eligible2024 driver4 laps; validation first3
eligible2024 driver44 laps; final development test first3 eligible2023 laps for
each driver4/44. No fastest-lap choice or replacement after geometry inspection.
Metadata-only eligibility inspection gives Bahrain train15/16/17, validation2/3/4,
test4:4/5/6 and44:3/4/5; Monza train2/3/4, validation2/3/4, test4:6/7/8 and44:2/3/4.
Earlier descriptive inspection of these development events is disclosed.

Use native SessionTime/X/Y/Source/Status, converting decimetres to metres per
FastF1 3.8.3 core.Telemetry docstring. No dense legacy CSV or imputed telemetry.
Require finite, strictly increasing native times and native pos/OnTrack samples.
Interpolate only the two lap-timing boundary anchors between valid bracketing
native positions, with maximum bracket/interior gap.75s. Record source rows and
interpolation explicitly. Native LapStartTime/Time/LapTime must agree within.1s.
Each selected lap requires>=100 native samples; raw endpoint closure<=30m.
An unsupported selected lap fails the case; do not silently swap or fill it.

## Frame, geometry and fitting

Treat XY as a local mathematical right-handed plane; positive curvature turns
counterclockwise and the positive lateral normal points left. No geographic
north, surveyed width or calibrated elevation is inferred.

First training lap defines the reference frame. Other laps receive a declared
rigid translation/rotation from 512 equal-phase arclength correspondences to
that first training lap. No scaling, reflection or nonrigid warp is allowed.
Persist transforms and errors before/after alignment. Held-out pose registration
is an evaluation coordinate-gauge operation, not geometry fitting; results concern
shape after registration, not absolute georeferencing. All shape coefficients
fit training laps only. Final test laps never select smoothing/configuration.

Normalize each lap's cumulative native chord distance to u in[0,1]. Fit periodic
Fourier XY coefficients by mean squared residual plus alpha*(k/K)^4 coefficient
penalty (constant unpenalized). Three frozen candidates: (K48,alpha.05),
(K96,alpha.05), (K96,alpha.5). Select lowest mean validation nearest-curve squared
distance, using the same4096-node search resolution. No post-test retuning.

Analytic first/second Fourier derivatives give heading and signed curvature
(x'y''-y'x'')/(x'^2+y'^2)^(3/2). Integrate speed on16384 intervals to define true
arc station; monotone PCHIP inverts station to u. Curvature uses analytic parametric
derivatives, not the second derivative of PCHIP. Check station/length convergence
against32768 intervals. Closest-point projection uses global dense lookup then
bounded scalar refinement; report held-out backward-projection fractions.

Independent controls: first training lap's raw closed polyline for positional
error; held-out25m-spaced chord turning-angle curvature as a COARSE PROXY, not
surveyed physical curvature. Report all per-lap/driver/year metrics and phase
registrations. Quantify training-lap sensitivity with three leave-one-training-lap
fits and pointwise normal offsets. This is a small-sample sensitivity range,
not a calibrated population confidence band.

## Annotations, interfaces and unknowns

Represent start/finish at reconstructed station0. Project training-source sector
timing boundaries and available driver4 pit-in/out observations to the curve,
recording support/reconstruction status and spread. Unsupported observations
remain UNKNOWN with reasons. Official DRS zones, physical width, surveyed
centerline and validated elevation remain UNKNOWN. Driver DRS activation alone
does not identify official zones. A complete pit-lane route is not inferred.

Synthetic and reconstructed maps share a typed geometric sampling contract.
Current synthetic simulation behavior stays unchanged. Research sampling returns
explicit unknown ancillary fields; any legacy simulator export must demand
explicit declared ancillary priors and must not silently substitute12m/zero/false.
This completes R029 reference geometry only, not every track-promotion criterion
in Master Build Guide9.2 or an R3 production track model.

## Frozen gates and stopping rule

Independent circle/ellipse tests check length, signed curvature, rigid-transform
invariance, normals, inverse station and nearest projection. Circle curvature
relative error<=1e-4; ellipse absolute curvature error<=1e-4/m; periodic analytic
position/tangent seam errors<=1e-8; numerical length refinement difference<=.001m.
Invalid/nonfinite/degenerate geometry and unobserved ancillary use fail loudly.

For BOTH public cases, all selected laps must meet source/raw-closure support.
Require finite monotone station, positive derivative norm>=5% of median, maximum
absolute curvature<=.12/m and fitted length within3% of median training chord
length. All six final held-out laps per case require registered XY RMSE<=6m,
95th distance<=12m, 95th distance no worse than raw-polyline baseline by>2m,
backward projection steps<=2%, coarse curvature-proxy MAE<=.003/m and95th
absolute difference<=.015/m. The coarse comparison is consistency evidence,
not measured curvature accuracy. No silent clipping or outcome-based gate changes.

R029 DONE requires both real cases passing frozen gates; saved source-labelled
lap inputs, coefficients/station arrays, unknown-aware annotations, all predictions,
controls, candidate scores, sensitivity and independently reloadable sealed
artifacts; numerical/boundary/protected-source/leakage/reload tests; full regression,
lint and Python3.11/3.12 CI. SIMULATED smoke cannot close research acceptance.
Failure stays visible and cannot be converted into production promotion.

Stop after R029 closure and documentation/commits. Next P0 is R030 longitudinal
calibration; R027/R028 remain pending P1 explanation/counterfactual studies.
