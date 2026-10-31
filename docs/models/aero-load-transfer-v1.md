# R032 aero balance and load transfer v1

Research-only **ADAPTATION**, generic priors and synthetic evidence. See the
[protocol](../../research/protocols/AERO_LOAD_TRANSFER.md) and
[equations](../../research/equations/AERO_LOAD_TRANSFER_V1.md).

The R031 bicycle now has a separate research extension for CoG aerodynamic drag,
downforce, front aero balance and longitudinal load transfer. Axle grip limits
and applied forces are solved together through quasi-static pitch equilibrium.
The original R031 module and production kernel retain their behavior.

Actual axle loads, tyre coefficients, aero maps, inertia and mass remain
uncalibrated. Fixed axle stiffness is a prior. There is no lateral roll transfer,
suspension/vertical state, ride-height map, wind or measured steering. The
solver's conservative uniqueness/contact conditions define its support; an
unsupported request is rejected, with no state or normal-load clipping.

The independent scalar audit uses bisection and DOP853. Synthetic sensitivity
and identifiability checks report ambiguous parameter products explicitly. Their
force-sensor oracle is unavailable in public telemetry. No posterior interval,
actual Formula One parameter identification or production promotion is implied.

```powershell
python -m apexsim.cli aero-load-study --output .cache/aero-study-new
python -m apexsim.cli verify-aero-load-study .cache/aero-study-new
python -m apexsim.cli audit-aero-load-study .cache/aero-study-new
```

Use a fresh output path. Outputs include configuration, results, three RK4
trajectories per case, independent paths, source/protocol snapshots, environment
and commit metadata, and a sealed summary/inventory. Scientific replay compares
regenerated mathematics at rtol1e-7/atol1e-8; exact file hashes remain separate.
The research extension accepts axle-force commands, not an implicit R030
power/drag adapter whose fitted drag would otherwise be counted twice.

Stop using this versioned module to roll back; original R031 and production
remain intact. Next dependencies are R033 observed-state/control alignment and
R034 matched replay errors. Research foundation remains R1 and kernel R0.
