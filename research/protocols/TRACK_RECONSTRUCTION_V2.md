# R029 v2: observed support across multiple laps

## A. Baseline and decision boundary

Preregistered 2026-10-19 after df51bf4. Fresh baseline:523 tests pass in246.19s,
two existing dependency warnings. The v1 native-source audit reproduces its
10/24 supported,14/24 rejected decision. V1 remains rejected and immutable.
Research26/73 DONE; build13/66; scoped researchR1/kernelR0. User requests R029
completion and frequent direct-to-main commits. Preserve artifacts/,output/,tmp/.

## B. Scope and prior inspection

Deliver an accepted 2D reference RACING TRACE for Bahrain and Monza, with source
support, analytic curvature, monotone station, uncertainty diagnostics and portable
scientific replay. This is an ADAPTATION, not a surveyed centerline, road boundary
or minimum-lap-time paper reproduction. Width/elevation/official DRS/full pit route
remain explicitly UNKNOWN; production promotion and R3 maturity remain separate.

V1 outcomes inspected source gaps only; no public geometry was fitted. A new
training/validation source preflight inspected boundary/row/closure availability,
not shape errors. R021/R026 masks and four archive seals remain those in v1.
Development events have prior tyre/forecast use. The new 2023 holdout laps below
exclude the first three eligible laps per driver used in the v1 gap audit. They
are new to this geometry study, not permanently untouched research benchmarks.

## C. Frozen cohort and source policy

All queries are non-benchmark races:2024R01/2024R16,2023R01/2023R14. Guard the
nine reserved whole-event benchmarks before native reads. Verify complete archives
and exact original mask/archive bindings before extraction and after the run.

Per circuit use ten training, ten validation, twelve test laps (64 total):

| Circuit | 2024 driver4 train | 2024 driver44 validation | 2023 driver4 test | 2023 driver44 test |
| --- | --- | --- | --- | --- |
| Bahrain | 15–24 | 2–9,14,15 | 7,8,9,19,20,21 | 6–11 |
| Monza | 2–11 | 2–11 | 9–14 | 5–10 |

These are the first ten original-mask eligible2024 laps per role and eligible
2023 positions[3:9] per driver. All40 train/validation laps passed metadata-only
source preflight with no replacement. No replacement of any frozen test lap.

Keep v1 unit/frame/timing/row rules: XY decimetres to metres; finite strictly
increasing native times, >=100 native pos/OnTrack samples; clean-dry mask identity;
lap timing agreement<=.1s; raw closure<=30m; nondegenerate adjacent chord steps.
Only the two lap-boundary anchors may use supported <=.75s brackets.

An interior interval longer than.75s remains UNSUPPORTED. It is retained and
reported, not interpolated into an observed trace or used for curvature targets.
The model fits actual native XY vertices. Cumulative chord parameter is explicitly
a reconstruction/lower-bound distance across gaps, not measured true arc length.
Rigid pose estimation uses the same512 equal-phase correspondences as v1;
interpolation there establishes a coordinate gauge only, never additional samples.
All original XY/time/native-parent arrays and interval masks remain saved.

## D. Method, baselines and uncertainty

Reuse v1 Fourier ridge loss, analytic derivatives,16384 integration intervals,
monotone PCHIP station and4096-node projection lookup with bounded refinement.
Six candidates: (K48,alpha.05),(K96,.05),(K96,.5),(K160,.05),(K160,.5),(K96,.005).
Candidates must pass training-only geometric sanity; select lowest mean validation
native nearest-curve MSE at the same4096-node resolution. Test shapes never
select parameters or fit coefficients. Test rigid pose registration remains an
evaluation gauge; results concern registered shape, not absolute localization.

Position errors use EVERY native/timing-anchor point, without dropping high
residuals. The baseline is the first training lap's supported native segments plus
its observed vertices; do not connect unsupported intervals or invent a closing
segment. Report raw-source closure and all baseline errors.

For each held-out lap, use25m-spaced chord-turning targets with a +/-25m stencil.
A target is supported only when its entire stencil crosses no native interval
longer than.75s. Unsupported targets/coordinates are NaN UNKNOWN, with a separate
saved boolean mask. Require >=75% supported targets and >=100 targets per lap.
Coarse curvature is a consistency PROXY, never surveyed physical curvature.

At10m stations around the fitted circuit, count distinct training laps whose
SUPPORTED consecutive projected intervals cover that station. Intervals must
advance positively by<=100m in station; the100m limit is a declared engineering
support guard, not an F1 physical fact. Never count a long time gap as support.
Require at least THREE donor laps at EVERY queried station. Identical holes in
all laps must reject acceptance even if a smooth periodic curve can bridge them.

Refit ten leave-one-training-lap curves using the selected configuration and
fixed training coordinate gauge. Save their station-matched normal offsets and
lengths. Require p95 absolute offset<=3m, maximum<=8m. These are descriptive
fit-sensitivity ranges, not calibrated confidence intervals. Save per-bin donor
counts and unsupported spans as separate missing-data uncertainty diagnostics.

## E. Frozen acceptance and stopping gate

Both circuits and ALL12 test laps per circuit must pass. Retain v1 numeric gates:
analytic position/tangent seams<=1e-8; length16384/32768 difference<=.001m;
positive derivative norm>=5%median; max|curvature|<=.12/m; fitted length within3%
of median training chord length. Test XY RMSE<=6m,p95<=12m,p95-minus-supported-raw
baseline<=2m, backward projection<=2%; supported coarse curvature MAE<=.003/m,
p95 absolute difference<=.015/m. Add test maximum XY distance<=30m, the >=75%/100
coarse-support rules, full >=3-donor station coverage and sensitivity gates above.

Independent analytic circle/ellipse controls retain v1 tolerances. Add staggered
missing intervals with successful multi-lap coverage, all-lap common-hole rejection,
exact support-window exclusion, native interval provenance, test-isolation,
unknown-aware annotations and refusal, immutable output, relocation, all-array
refit/replay, tamper/resealed-promotion refusal, and CPU synthetic CLI smoke.
Smoke cannot close public research. Full regression, lint and Python3.11/3.12 CI
must pass. Inspect real arrays and quantitative per-lap/regime failures; create
source-labelled reports, equation/model cards, sealed compact evidence and plots.

R029 DONE only after both real cases pass all v2 gates and replay, with v1 failure
still visible. No threshold loosening or test-driven configuration/cohort changes.
A genuine implementation bug may be corrected with explicit diagnosis and a new
immutable run; a real methodological failure remains a failure.

## F. Risks and limits

Native public positions may be reconstructed upstream. Racing-line variation,
rigid full-lap alignment, chord-phase bias and shared feed gaps constrain meaning.
Only two development circuits; sensitivity is not survey accuracy or calibrated
population confidence. Annotation timing projections need source support and
spread. Unknown ancillary fields stay UNKNOWN; no legacy defaults may enter a
research export. Source/geometry quality alone does not validate vehicle dynamics.

## G. Execution order

1. Commit this protocol and the explicit v1/v2 decision record before fitting.
2. Implement source interval representation and tests; commit/push.
3. Implement supported targets/coverage/selection/sensitivity and independent tests;
   commit/push. Add fresh CLI/artifact replay and synthetic CI; commit/push.
4. Run frozen train/validation and new development holdout, inspect all gates.
5. Independently audit saved outputs, source identity and immutable scientific
   replay. Run full checks; commit evidence and update status only on acceptance.
6. Stop after R029 closure. R027/R028 remain separate tasks; do not start R030 here.
