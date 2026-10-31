# R035 conditional transparent controller equation map

Adaptation, not reproduction of human steering or a calibrated team controller.
Pure-pursuit baseline follows the geometry described by Coulter1992,
[CMU-RI-TR-92-01](https://publications.ri.cmu.edu/storage/publications/pub_files/pub3/coulter_r_craig_1992_1/coulter_r_craig_1992_1.pdf).
Feedback, understeer approximation and conservative force envelope are declared
research adaptations. R031/R032 equation maps define the underlying six-state car.

| Quantity | Equation / convention | Implementation and check |
|---|---|---|
| Curve pace | v²*abs(kappa)<=f*mu_y*(g+.5*rho*ClA*v²/m), v<=Vmax | `speed_profile`; hand inequality |
| Braking reachability | v_i²<=v_(i+1)²+2*6*ds, periodic | `speed_profile`; periodic envelope test |
| Understeer coefficient | K=m/L*(b/Cf-a/Cr) | `command`; SI radian feedforward |
| Feedforward steering | delta_ff=(L+K*v²)*kappa | `command`; left/right signs |
| Heading error | wrap(map_heading-psi-atan2(vy,vx)) | `command`; no future measured state |
| Feedback steering | delta_ff+1.5*heading_error-atan(.8*e_y/(v+5))+.15*(v*kappa-r) | `command`; disturbance recovery |
| Actuators | abs(delta)<=.6rad; abs(delta-delta_previous)<=1.5*.1rad | explicit projections; rate test |
| Net acceleration | .8*(v_target-v)+v_target*dv_target/ds | `command`; source targets absent from feedback API |
| Tyre request | m*a_net+drag+rolling; aero counted once by R032 | force-sign/capacity tests; independent physics |
| Contact enclosure | radius=h/L*(mu_x+mu_y*abs(sin(delta)))*N | `command`; <=.75 of minimum possible axle capacity |
| Pure pursuit | delta=atan(2*L*goal_lateral/chord²), preview6+.3*v metres | `command(mode=pure_pursuit)`; identical information/limits |
| Propagation | six-state loaded Newton/Euler; controls held.1s, RK4<=.02s | `simulate_driver`; R032 independent bisection/DOP853 |
| Refinement | common-station XY/speed; finish-time interpolation at L | `refinement_metrics`; incomplete/drifting paths rejected |

Steering and forces are SIMULATED, initial lateral/yaw states and car parameters
are PRIOR, reference geometry is RECONSTRUCTED, native speed is parsed-source
observation. Friction/actuator constraints change applied forces/controls; chassis
states are not clipped or teleported. Failed prefixes and attempted actions remain
available for inspection. No real-car steering identification is implied.
