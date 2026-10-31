# R030 effective longitudinal equation and unit map

Classification: physics-guided descriptive ADAPTATION. See the
[frozen protocol](../protocols/LONGITUDINAL_CALIBRATION.md). The power/drag balance
is the power-limited, low-curvature specialization of the existing point-mass
prior. It is not a minimum-lap-time paper reproduction or a production upgrade.

| Symbol | Unit / truth | Code / interpretation |
|---|---|---|
| t | s, public parsed source | native SessionTime, checked against Date differences |
| v | m/s, public parsed source | Speed/3.6; upstream reconstruction possible |
| u | dimensionless source observation | Throttle/100; source domain[.98,1] |
| z | source DRS indicator |0/1/8 closed;10/12/14 open; other codes UNKNOWN |
| kappa |1/m, reconstructed reference | frozen R029 offline registered curve, latest native position only |
| m | kg, UNKNOWN actual | no actual mass identified;900kg PRIOR only in the baseline |
| p | W/kg=m2/s3, calibrated effective ratio | engine/ERS/efficiency/mass confounded; not measured engine power |
| d |1/m, calibrated effective drag-like ratio | nominally rho*CdA/(2m); wind/setup/grade remain confounded |
| r |m/s2, PRIOR |.015*9.81=.14715; no coast-based rolling identification |
| a |m/s2, model |p*u/v-[d_open+d_extra*(1-z)]*v2-r |
| y_i |m/s, reconstructed training target |v_(i+1)-v_i+r*dt_i |
| X_i |mixed physical units |dt_i*[u_i/v_i,-v_i2,-(1-z_i)*v_i2] |
| theta |[p,d_open,d_extra] | bounded convex fit of X*theta to y; shared-drag omits extra column |
| RMS_j |design-column unit |training-only sqrt(mean(X_j2)); no mean centering |
| w_j |scaled coefficient |theta_j*RMS_j; solver bounds scale identically |
| delta_v |m/s |native speed increment; not measured instantaneous acceleration |
| speed MSE |m2/s2 |future native-node errors only; observed initial node excluded |
| speed integral |m, reconstructed |trapezoidal integral of speed; not surveyed GPS distance |

Force balance under the stated power-limited flat-road approximation:

`m*dv/dt = P_eff*u/v - .5*rho*CdA(z)*v2 - m*Crr*g`.

Mass, actual power and airspeed are unavailable. The implemented law therefore
identifies conditional effective ratios, with no physical CdA conversion.
Nonnegative d_extra encodes closed drag>=open as a structural PRIOR. When one
training state is absent, the richer design is rank deficient and the class is
ineligible; do not infer the missing coefficient from validation/test.

Analytic derivatives audited against central finite differences:

- `da/dv=-p*u/v2-2*[d_open+d_extra*(1-z)]*v`;
- `da/dtheta=[u/v,-v2,-(1-z)*v2]`.

Hand fixture: p900W/kg,d_open.0005/m,d_extra.0002/m,r.14715m/s2 at50m/s,u1,z0
gives18-1.75-.14715=16.10285m/s2. DRS-open increases this model acceleration
by.5m/s2. These are synthetic equation checks, not real-car intervention evidence.

Identification fits native increments with a left-endpoint Euler approximation.
Replay uses RK4 max.05s (and independent.025s convergence), without observed-speed
resets. Recorded left-held controls are supplied exogenous inputs. Only observed
initial speed and a five-sample causal slope initialize the respective baselines.

Fit ranges are declared priors: p[100,2000]W/kg, drag coefficients[0,.005]/m.
Column-normalized rank/condition tests identify algebraic support, not separation
of engine power, ERS, wind, fuel or setup effects. Active bounds and200 training-
lap bootstrap draws remain visible, along with rolling-prior +/-50% sensitivity.

Errors average native future nodes within section, sections within lap, laps
within driver, then drivers equally. A paired500-draw lap bootstrap fixes the
test event and drivers. It is not population-level race generalization.

Independent audit reconstructs X/y with scalar loops, checks bounded-fit KKT
conditions, integrates held controls with SciPy DOP853, and recalculates speed MSE
without the RK4 or hierarchical-score helpers. Replay separately reconstructs
native sections, refits training and regenerates every stored decision/array.
