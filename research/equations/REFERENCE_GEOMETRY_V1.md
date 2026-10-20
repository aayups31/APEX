# Reference racing-trace geometry v1

R029 is an independently specified reconstruction ADAPTATION. It does not
reproduce a surveyed centerline or a minimum-lap-time paper's complete track/
vehicle problem. Native units and source semantics were checked in installed
FastF1 3.8.3 `core.Telemetry`: X/Y/Z use decimetres; native timestamps retain
session-relative time. XY is converted to metres. North/orientation and physical
road boundaries are not inferred.

## Geometry and coordinate gauge

For native points p_i, define `d_i=||p_i-p_(i-1)||`, cumulative chord station
`c_i=sum(d_1..d_i)` and normalized parameter `u_i=c_i/c_last`. Native support is
checked before this reconstruction; only bounded lap-boundary timing anchors
are linearly interpolated. The original source arrays remain saved.

Other laps receive a rigid registration to the first training lap. With centered
512-point equal-phase correspondences X/Y and `X'Y=U Sigma V'`, row-vector
rotation is `R=U diag(1,det(UV')) V'`, translation `t=mean(Y)-mean(X)R`.
Registration preserves lengths/curvature and disallows scale, reflection and
nonrigid deformation. Held-out full-lap registration makes this shape evaluation,
not absolute georeferencing or an online state-estimation result.

The periodic model is

```
r(u) = beta_0 + sum_k[a_k*cos(2*pi*k*u) + b_k*sin(2*pi*k*u)]
loss = mean_i ||B(u_i)*beta - p_i||^2
       + alpha*sum_k (k/K)^4*(||a_k||^2+||b_k||^2)
```

The intercept is unpenalized; coefficients are in metres and u is dimensionless.
Only training laps determine coefficients. Validation selects among the three
preregistered harmonic/penalty settings; test geometry never selects or fits shape.

Analytic r'/r'' give
`heading=atan2(y',x')`, `kappa=(x'y''-y'x'')/||r'||^3` in inverse metres.
The tangent is `r'/||r'||`; its left normal is `(-t_y,t_x)`. Curvature is positive
for counterclockwise turning in the mathematical XY frame.

Integrating `||r'||` defines station `s(u)` in metres. A strictly increasing
16384-interval trapezoidal table and
[monotone PCHIP inverse](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.PchipInterpolator.html)
map station to u. Curvature uses analytic parametric derivatives, avoiding the
piecewise interpolator's second-derivative discontinuities. Refining to32768
intervals checks numerical length convergence. A dense global candidate lookup
and bounded local scalar minimization produce nearest-curve projections.

## Code and independent checks

| Quantity | Code | Independent check |
| --- | --- | --- |
| Bounded source timing anchors, decimetre conversion | `position_laps` | Hand-built circular native stream with known boundary weights/rows |
| Rigid registration | `reference_geometry.register_lap` | Known90-degree rotation and translation |
| Periodic coefficients and derivatives | `fit_reference`, `basis` | Analytic circle/ellipse length and curvature, both traversal directions |
| Monotone station and normals | `ReferenceCurve.geometry` | Inverse projection/station, unit tangent/normal and orthogonality |
| Source/held-out separation | `fit_case` | Changed test shape leaves coefficients and selected configuration identical |
| Explicit unknown properties | `require_ancillary`, annotations | Width/elevation/official DRS/full pit route remain UNKNOWN |
| Portable scientific replay | `verify_track_reconstruction` | Stored-input refit, all prediction arrays/gates/sensitivity, relocation and tamper checks |

## Evaluation boundary

The raw first-training-lap polyline supplies an independent positional control.
Held-out25m chord turning-angle curvature supplies a COARSE PROXY consistency
check, not ground-truth physical curvature. Leave-one-training-lap sensitivity
uses three alternative fits and normal offsets; it is not a calibrated confidence
band. Imposing a periodic model guarantees structural closure, so raw source
endpoint gaps and held-out residuals are reported separately.

Start/finish derives from native timing anchors. Training-source sector and pit
timings receive reconstructed station projections, support status and spread.
These do not define official zones or a full pit route. Physical width, validated
elevation and surveyed road centerline remain UNKNOWN. The shared geometric
sampling contract adds no research-to-production promotion and changes no existing
race sampling behavior.
