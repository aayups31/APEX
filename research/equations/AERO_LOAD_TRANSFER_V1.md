# R032 aero and longitudinal load-transfer equations

Equation-level **ADAPTATION**, with synthetic validation and generic priors.
[Frozen protocol](../protocols/AERO_LOAD_TRANSFER.md) defines the gates. The R031
body frame and six-state interface remain unchanged; production is untouched.

| Symbol | SI units / truth | Implementation |
|---|---|---|
| rho |kg/m³, prior|`AeroParameters.air_density_kgpm3`|
| CdA, ClA |m², prior|effective drag/downward-lift coefficient-area products|
| beta |fraction [0,1], prior|front share of downward aero load|
| h |m, prior|CoG height above tyre-force plane|
| V |m/s, simulated|sqrt(vx²+vy²), zero-wind airspeed approximation|
| D,Z |N, simulated|drag magnitude and downward aerodynamic force|
| Fzf,Fzr |N, simulated|solved total axle normal loads|
| Tx |N, simulated|sum of constrained tyre forces along body x|
| N |N, simulated|mg+Z|

```
q = rho*V²/2
D = q*CdA; Z = q*ClA
drag_body = -D*[vx,vy]/V
x_cp = beta*(a+b)-b
base = mg*b/(a+b)+beta*Z
Fzf = base-h*Tx/(a+b)
Fzr = mg+Z-Fzf
Tx = Fx_front*cos(delta)-Fy_front*sin(delta)+Fx_rear
```

Drag and any supplied additional resistance act at CoG. Tyre forces act at the
road plane; downforce acts at x_cp. Static pitch equilibrium is
`-a*Fzf+b*Fzr+x_cp*Z-h*Tx=0`. It is tyre force, not net deceleration after drag,
that creates the tyre-height pitch moment. This convention prevents counting
aerodynamic deceleration again as a tyre-force transfer.

R031's axle ellipse/tanh law is evaluated at the solved loads. The model thus
solves a scalar implicit load/force equation rather than feeding unconstrained
requested forces into load transfer. Wheel forces and their front steering
rotation then enter the six-state Newton/Euler balance. CoG drag has zero yaw
moment. Power balance includes aerodynamic work `-D*V`; normal forces do no work
in this flat constrained plane. Suspension/vertical/roll dynamics are omitted.

## Supported unique solution

Every possible root lies within base±h*Tmax/L, where L=a+b and
Tmax=(mux+muy*|sin(delta)|)*N, intersected with the minimum-contact domain.
The interval is enclosed outward by16 floating-point ULPs of N, preventing an
exact capacity-boundary root from being lost through endpoint roundoff. This is
a numerical enclosure, not load clipping or a physical correction.

The rear longitudinal-force slope is bounded by mux. Front body-x force has:

- fully saturated Fx across the interval: slope bound mux*|cos(delta)|;
- fully unsaturated Fx across the interval: bound
  `muy*|sin(delta)|/sqrt(1-(Fx_req/(mux*interval_lower))²)`;
- zero steering: longitudinal slope bound mux.

Require h/L times summed front/rear bounds <.9. At h=0 the load is explicit.
If the front saturation threshold crosses the interval, the implementation
abstains: fixed-request ellipse lateral force has an unbounded normal-load slope
near that threshold. A constant muy slope bound would be invalid. The supported
residual is strictly increasing; Brent solves it. Missing contact bracket or
insufficient uniqueness support produces a named rejection.

## Hand fixture and independent evidence

At vx50 m/s, m900 kg, a1.6 m, b2 m, rho1.225, CdA1.1 m², ClA3 m²,
beta.45, h.3 m, requested front900/rear1800 N and zero steering/slip:

`Z=4593.75 N; D=1684.375 N; Tx=2700 N; transfer=225 N;`
`Fzf=6747.1875 N; Fzr=6675.5625 N; ax=1.1284722222 m/s²`.

The independent module rebuilds scalar tyre forces and uses bisection instead
of Brent, then DOP853 instead of RK4. Exact full longitudinal saturation has
zero lateral budget; factorized arithmetic avoids subtracting two large squared
normal loads to invent a tiny force at the boundary.

The sensitivity study changes each declared prior independently. Its analytical
force-sensor oracle measures drag and both axle loads with mass/tyre force known.
For [rho,CdA,ClA,beta,h], its relative Jacobian has rank4/5. Scaling rho byk while
dividing both coefficient-area products byk preserves all oracle observations.
Fixing density gives rank4/4; zero tyre force removes height sensitivity; drag
alone gives rank1. Public telemetry lacks these force/load sensors, so these
structural results identify no real-car parameter or uncertainty interval.
