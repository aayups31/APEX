# R037/R038 equations, units and source boundaries

Engineering ADAPTATION of accepted R035/R036/R032 equations plus an empirical
runtime monitor. [Protocols](../protocols/MULTILAP_RECOVERY.md) and
[support protocol/source](../protocols/SUPPORT_FALLBACK.md) fix all thresholds.
The NASA Simplex paper motivates decomposition only; its PVS proof is not reproduced.

| Symbol | Equation / implementation | Unit/source |
|---|---|---|
| z | (x,y,heading,vx,vy,yaw rate), R032 RK4 | m,rad,m/s,rad/s; SIMULATED |
| s | local segment projection, unwrapped across laps | m; supplied reconstructed map |
| delta pulse | raw policy angle + signed.01rad for5commands | rad; synthetic disturbance |
| lap RMSE | sqrt(mean(e_y(s_grid)^2)),2001uniform station nodes/lap | m; closed_loop.lap_metrics |
| recovery | first post-pulse time with abs(e_disturbed(s)-e_nominal(s))<=.15m for2s | s; closed_loop.recovery_metrics |
| c_i | (q.005(train x_i)+q.995(train x_i))/2 | raw R036 feature units |
| h_i | max((q.995-q.005)/2,declared floor_i) | same units as feature |
| d(x) | max_i abs((x_i-c_i)/h_i) | dimensionless; empirical box score |
| T | max(1.25,1.1*q.995(validation d)) | dimensionless; validation only |
| reversion | d>T, unavailable features or invalid raw correction(abs>.2rad/nonfinite) | immediate before actuation |
| release |10 consecutive valid actions with d<.8T |100ms sampled prior; hysteresis |
| hard exit | unavailable trusted map/state/known assumptions, R031 state support exit or abs(e_y)>2m | latched abstention |

Quantiles use linear interpolation at p*(n-1). Independent audit sorts each scalar
column and implements this interpolation without calling NumPy quantile or the
primary fit helper. Half-range floors are [.05,.02,.02,.005,.005,.02,.01,.01] in
the eight R036 raw feature units, declared priors rather than identified physics.
Hand fixture train alternating +/-1 in every coordinate gives c=0,h=1,T=1.25;
validation alternating +/-3 changes T to3.3 without changing training centers/ranges.

The mode machine is causal and has no test-label/future-state input. A hard exit
requires a new explicitly initialized run, not automatic recovery. Reversion uses
R035 independently computed trusted-state feedback; actual angle/rate/force limits
remain shared. Applied actions, including every projection, are stored. Independent
held-action DOP853 checks numerical equations, not the unproved safe region of a
real car. No hidden state clipping or lap-boundary reset enters these equations.
