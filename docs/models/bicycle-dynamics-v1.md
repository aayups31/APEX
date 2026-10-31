# R031 bicycle dynamics v1

Research-only equation-level **ADAPTATION**, with synthetic evidence and generic
parameter priors. [Protocol](../../research/protocols/BICYCLE_DYNAMICS.md) and
[SI equation map](../../research/equations/BICYCLE_DYNAMICS_V1.md) define the
interface, frame, default values, constraints and acceptance thresholds.

The model integrates position, heading, forward/lateral body velocity and yaw.
Inputs are actual front road-wheel steering radians, front/rear longitudinal
force requests in N and nonnegative body resistance in N. The existing engine's
normalized steering field is **not** an angle and cannot be passed directly.

Static axle loads and per-axle longitudinal-priority ellipses enforce shared
grip. Every request reduction is counted; lateral force uses a dissipative tanh
prior. A full rear longitudinal request can remove all rear cornering authority.
The versioned campaign preserves this unsafe case and explicitly abstains at
the first unsupported state. It does not lower its request or clip yaw to finish.

Forward body speed support is 5–110 m/s, sideslip <=.35 rad, yaw <=2 rad/s,
steering <=.35 rad and axle slip <=.5 rad. Intermediate and accepted states are
checked. RK4 max step is .02 s; default .01 s. Invalid times, excessive substep
budgets, nonfinite values and unsupported states fail explicitly.

`StraightPowerDragInput` decomposes a supplied R030 effective law into requested
rear force and resistance, only for straight 40–105 m/s/full-throttle states.
The law is reevaluated at every RK stage. It matches scalar R030 acceleration
only without grip limiting; this algebra check does not identify actual force,
mass, grip or cornering parameters. The equivalence fixture's mu_x=8 is an
explicit **synthetic unsaturated fixture**, not a physical tyre estimate.

## Reproduce

Use the existing development environment. From the repository root:

```powershell
python -m apexsim.cli bicycle-dynamics-study --output .cache/bicycle-study-new
python -m apexsim.cli verify-bicycle-dynamics .cache/bicycle-study-new
python -m apexsim.cli audit-bicycle-dynamics .cache/bicycle-study-new
```

The output path must be fresh. A study saves `configuration.json`, `results.json`,
`trajectories.npz`, sealed `summary.json` and `manifest.json`, plus exact equation,
audit, study and protocol source snapshots. It records every supplied command,
three timestep trajectories, independent solver paths, constraint interventions,
rejected boundary states, code commit and runtime versions. Failed numerical
criteria produce a rejected decision and nonzero CLI status. Unexpected contract
exceptions abort without publishing acceptance.

Verification checks exact file/content integrity, then mathematically regenerates
all gates and arrays using rtol1e-7/atol1e-8. Hashes establish content integrity,
not external authentication. Independent audit uses its own scalar forces and
DOP853, verifies time coverage and the rejected case's terminal support root.
Both commands operate offline; a portable output folder needs no provider cache.
CI runs the entire campaign, replay and independent audit on Python 3.11/3.12.

## Supported conclusion and limits

The 14-case campaign contains 13 supported synthetic rollouts and one unchanged
abstention challenge. It tests force balance, dissipation, local stability,
time refinement and numerical consistency. It supplies **no measured-car
prediction error or calibrated uncertainty**. There is no fitting or benchmark
telemetry access. Parameters remain generic priors; wheel spin, aero, load
transfer, tyres, road geometry and actual controls remain uncalibrated/omitted.

Research foundation remains R1; production kernel remains R0. No component is
written into `sim_core`. Stop consuming this research module to roll back; prior
production and R030 results remain intact. Next dependency is R032 aero balance
and load transfer with sensitivity/identifiability evidence; R033/R034 recorded
state/control alignment and full replay errors remain required afterwards.
