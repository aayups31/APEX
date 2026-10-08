# R015 smooth lap map v1

This is an **ADAPTATION** with synthetic **PRIOR** parameters, not a fitted FIENI
car map or a replication of its published results. Global maturity stays **R0**.
The implementation is `apexsim.research.smooth_lap.SmoothLapMap`;
the underlying units/equations are reviewed in [FIENI_2025.md](FIENI_2025.md).

For each fixed dry compound and lap mode, the continuous coordinates are
`[fuel_energy_mj, battery_delta_mj, car_mass_kg, tyre_wear]`. The domain is
`[0.9*nominal_fuel, 1.1*nominal_fuel]`, the parameter battery-delta interval,
`[empty_mass, empty_mass+initial_fuel]`, and wear `[0, 1.25]`. Numeric evaluation
rejects violations. CasADi functions deliberately extend outside this domain;
optimization callers must constrain their eight box slacks to be nonnegative
and separately impose race resource feasibility. Being inside the box alone
does not establish fuel/battery reachability or terminal legality.

The map preserves the starter's mass, fuel and cubic tyre-time-loss terms on
this domain. It evaluates the tyre polynomial directly, without clipping.
Normal, inlap, outlap and consecutive-pit (`out_inlap`) modes use the starter's
respective fixed penalties; compound/mode selection takes place before graph
construction and is not differentiable. Current battery state is not a pace
coordinate in this synthetic starter.

For battery delta `d` (negative deployment, positive recharge), define
`a=(k_deploy+k_recharge)/2`, `b=(k_recharge-k_deploy)/2` and positive `eps`:

    B_smooth(d) = a*d + b*(sqrt(d*d+eps*eps)-eps)
    B_piecewise(d) = a*d + b*abs(d)
    B_smooth'(d) = a + b*d/sqrt(d*d+eps*eps)
    B_smooth''(d) = b*eps*eps/(d*d+eps*eps)^(3/2)

Because `sqrt(d*d+eps*eps)-abs(d)` lies between zero and `eps`, the absolute
value discrepancy is at most `abs(b)*eps` seconds. This holds over the full
domain, including either ordering of the nonnegative battery slopes. Both
battery terms equal zero at `d=0`. Default `eps=0.01 MJ` gives a maximum
discrepancy bound of **0.0005 s** with the default coefficients.

Fuel/mass derivatives are constant; tyre derivatives are obtained directly
from its polynomial. The construction requires nonnegative finite pace/tyre
coefficients and certifies a positive lower bound using the maximum fuel input,
minimum battery delta, zero excess mass, nonnegative tyre/penalty terms, and
the approximation-error bound. Values, gradients and Hessians are finite at
the battery join. The default battery curvature is negative; this map does
**not** establish a convex objective or a global optimum. Smaller `eps` lowers
approximation error while increasing join curvature as `1/eps`.

Install the optional optimization extra (CasADi 3.7.2) and run from the checkout:

```powershell
python -m pip install -e './apex_engine[optimization]'
python -m apexsim.cli smooth-lap-demo --output .cache/smooth-lap-new
```

The command evaluates all twelve compound/mode maps: 228 corner/join reference
checks, 60 finite-difference derivative checks, and eight rejected box violations.
It compares independent scalar values and closed-form derivatives with CasADi,
then checks centered finite differences. Acceptance tolerances and perturbation
steps are recorded in the summary. JSON check records, summary and a final
manifest carry content/file hashes and implementation hashes. An existing output
directory is refused; failed numerical checks write no evidence. Base CLI imports
do not import CasADi. CI installs the optimization extra on Python 3.11/3.12 and
runs both tests and this command, so missing CasADi cannot silently pass CI.

See [verification report](../../docs/verification/smooth-lap-map-report.md) for
measured evidence. R016 will build and benchmark a solver adapter on these maps;
R017/R018 still precede the planned R1 review. No production transition is replaced.
