# Observed track support v2: equations and evidence boundary

R029 ADAPTATION; see the [frozen protocol](../protocols/TRACK_RECONSTRUCTION_V2.md)
and [v1 geometry equations](REFERENCE_GEOMETRY_V1.md). V1's failed experiment is
preserved. This version changes observation support, not native time-gap limits.

For native/timing-anchor points p_i at session times t_i, define support
`h_i = 1[t_(i+1)-t_i <= 0.75 s]`. Missing interiors have h_i=0. Their endpoint
positions remain observed; no extra vertex or measured curvature is invented.
Only the two supported timing anchors use bounded linear reconstruction.
Normalized cumulative chord distance is a RECONSTRUCTED model parameter. Across
a missing interval its straight chord is a lower bound on distance travelled.

The Fourier ridge loss and analytic station/heading/curvature remain v1. Fit
native vertices only, with no synthetic point filling in the fitting objective.
Rigid equal-phase pose alignment includes interpolation as a coordinate-gauge
operation. Held-out shape evaluation is conditional on that full-lap registration;
this is not a causal localization or geographic survey result.

## Independent observed baseline

Let V be the first training lap's observed vertices and S its segments with h=1.
Baseline distance is `d(p)=min(min_(v in V)||p-v||, min_(s in S)dist(p,s))`.
There is no segment across h=0 and no invented closing chord. Projection onto
supported finite segments clamps their scalar coordinate to[0,1]; this enforces
the mathematical segment definition rather than clipping an invalid model state.
The fixture with segments[0,1] and[9,10] gives distance4 at x=5, not zero.

## Curvature support and UNKNOWN

At25m chord-station centers c, a +/-25m stencil is usable only if it intersects
no unsupported source interval. Supported points use the v1 turning-angle proxy;
unsupported proxy, target coordinates and matched model-curvature entries are
NaN UNKNOWN with a separate boolean mask. This mask depends only on source times
and chord coordinates, never model residuals. All native vertices still enter
positional evaluation. Support counts/fractions are reported per held-out lap.

## Multi-lap coverage

At each10m query station q, a training lap contributes at most one donor vote.
Its consecutive projected interval contributes only when h=1 and station advances
positively by<=100m. The100m guard is a declared engineering support prior.
Count a vote when q lies in that circular interval. A1e-6m endpoint tolerance
handles numerical roundoff only; source holes remain unsupported. Require>=3
distinct training-lap donors everywhere, not merely high average coverage.

The tests use staggered holes to retain three donor laps and identical holes to
produce zero support, even when the estimator constructs a closed periodic curve.
Curve smoothness and periodic closure cannot supply missing observation evidence.

## Fit sensitivity

Delete each training lap in turn and refit the selected configuration, holding
the original training coordinate gauge fixed. At2048 uniform normalized stations,
save signed normal offsets relative to the full fit and alternative lengths.
Report p95/max absolute normal offsets and pointwise min/max ranges. These are
descriptive conditional sensitivity diagnostics, not calibrated confidence or
survey error bounds. Per-station donor counts quantify observation support
separately; neither quantity is relabelled measured physical track uncertainty.

## Code/test crosswalk

| Claim | Implementation | Independent control |
| --- | --- | --- |
| No replacement/imputed vertices | `position_laps.extract_position_lap` v2 opt-in | Exact row/time counts and unchanged v1 strict failure |
| Supported baseline | `supported_polyline_distances` | Hand-calculated disjoint finite segments |
| Missing stencil abstention | `supported_windows`, `evaluate_supported` | Known missing80–100m span; saved unsupported entries are NaN |
| Distinct full-circuit coverage | `station_support` | Complementary/common gaps and endpoint roundoff |
| Test isolation | `fit_supported_case` | Changed test XY/missingness cannot change weights/config |
| No synthetic promotion | v2 workflow/verifier | Resealed simulated profile/source mismatch refusal |
| Portable science | v2 verifier | All arrays, candidate scores, gates, support and sensitivity refit |

All shape/curvature/coverage/support/sensitivity acceptance constants are frozen
in the protocol before public geometry outcomes. No proprietary curvature,
road width, elevation, official DRS zones or full pit route is inferred.
