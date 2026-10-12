# R024 causal motion and R006 wheel-energy proxy: units and assumptions

Classification ADAPTATION. Todd's proprietary wheel targets are not available;
the existing APEX R006 proxy is reused without changing its equations. Inputs
are now explicitly source-bound, with no claim that these are measured wheel
forces/slip/energy or that the full paper was reproduced.

| Symbol | Units | Source/truth |
| --- | --- | --- |
| v | m/s | Provider Speed km/h divided by 3.6, RECONSTRUCTED |
| u | fraction | Provider throttle percent divided by 100, RECONSTRUCTED |
| b | fraction | Provider brake-applied boolean as 0/1 magnitude, PROXY |
| a_x | m/s² | Causal five-sample speed/time least-squares slope, RECONSTRUCTED |
| omega | rad/s | Causal seven-position quadratic fit, RECONSTRUCTED |
| kappa | 1/m | omega/geometry speed, PROXY of path curvature |
| a_y | m/s² | -v*omega, PROXY; rightward-positive convention |
| delta | rad | atan(wheelbase*kappa), steering PROXY |
| m | kg | 900, PRIOR |
| dt | s | Native preceding car-sample interval, RECONSTRUCTED |
| E_i / P_i | kJ / kW | Wheel sliding-energy/power PROXY |

Only timestamps at or before the car sample enter its reconstruction. Position
coordinates use FastF1's documented 1/10 m unit. XY right-handedness and
left/right interpretation are a declared convention prior, not a calibrated
geographical frame. Local motion fitting is not R029 track reconstruction.

R006 uses static load `m*g` with g9.81 m/s²; longitudinal transfer
`m*a_x*h/L`, lateral transfer `m*a_y*h/track_width`, split by front fraction .46.
Frozen h=.32 m, L=3.6 m, width2 m, aero0 N; remaining aero fraction.46,
driven-rear fraction1 and brake-front fraction.58 are PRIOR. Actual wheel loads,
powertrain drag and mass/fuel trajectory are not observed. Before calling R006,
R024 rejects any unclipped load below its 50 N projection floor.

Axle force fractions are (.29,.29,.21,.21) when b>u; otherwise (0,0,.5,.5).
Longitudinal force proxy is `m*a_x`; lateral force proxy is `m*a_y` distributed
in proportion to normal load. Slip proxies use the existing empirical PRIORs:

```
v_slip_x = v*(.002 + .018*b^1.5 + .010*u^1.5 + .004*abs(u-b))
v_slip_y_base = .010*v + .11*abs(delta)*v + .015*abs(a_y)*v/9.81
v_slip_y_i = (1.25,1.25,.78,.78)_i * v_slip_y_base
P_i_W = (abs(Fx_i)*v_slip_x + abs(Fy_i)*v_slip_y_i)*(Fz_i/mean(Fz))^.18
E_i_kJ = P_i_W * dt / 1000
P_i_kW = E_i_kJ / dt
```

Force times slip speed has W units; seconds/1000 yields kJ. Empirical slip and
load coefficients are assumptions, not calibrations. Validated inputs never
require the legacy estimator's throttle/brake/load/energy clipping.

With aero0 and fixed kinematics/control, changing mass by factor f scales all
forces/loads by f and leaves normalized loads unchanged: energy scales by f.
The +/-10% sensitivity separately checks whether the 50 N support boundary is
still satisfied and reports excluded sensitivity rows. It does not identify mass
or physical energy from observations.

Tests independently check translated quadratic-motion derivatives, the hand
constant-acceleration energy calculation, conversion/energy-power units, future
invariance, histories at gaps/pit resets, label tampering and portable artifacts.
