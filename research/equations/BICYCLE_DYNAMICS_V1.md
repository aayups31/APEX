# R031 planar bicycle equation map

**ADAPTATION; SYNTHETIC validation; generic PRIOR parameters.** Scope and source:
[protocol](../protocols/BICYCLE_DYNAMICS.md). This is a six-state planar axle
model, not the four-wheel Perantoni/Limebeer vehicle or Pacejka Magic Formula.
The production kernel and normalized steering contract are unchanged.

| Symbol | SI unit / truth | Interface |
|---|---|---|
| X,Y | m, simulated | `BicycleState.x_m/y_m`, inertial coordinates |
| psi | rad, simulated | `heading_rad`, positive counterclockwise |
| vx,vy | m/s, simulated | forward/left body velocities |
| r | rad/s, simulated | `yaw_rate_radps`, positive left |
| delta | rad, supplied synthetic control | front road-wheel angle, not normalized steering |
| Fx_req,f/r | N, supplied synthetic control | requested axle longitudinal wheel forces |
| R | N, prior/synthetic | opposing body-x resistance, nonnegative |
| m,Iz | kg, kg m², prior | `mass_kg`, `yaw_inertia_kgm2` |
| a,b | m, prior | CoG to front/rear axle, positive |
| Cf,Cr | N/rad per axle, prior | axle cornering stiffness |
| mux,muy | dimensionless, prior | longitudinal/lateral friction coefficients |
| Fzf,Fzr | N, simulated from priors | static normal loads |
| alpha_f/r | rad, simulated | wheel velocity direction relative to wheel forward |
| B_f/r | N, simulated | remaining lateral budget after Fx allocation |

Coordinate frame is right-handed, body x forward, y left, z up.

```
L = a+b
Fzf = m*g*b/L; Fzr = m*g*a/L
Vxf = cos(delta)*vx + sin(delta)*(vy+a*r)
Vyf = -sin(delta)*vx + cos(delta)*(vy+a*r)
Vxr = vx; Vyr = vy-b*r
alpha_f = atan2(Vyf,Vxf); alpha_r = atan2(Vyr,Vxr)
```

For each axle j:

```
Qx = mux*Fz; Qy = muy*Fz
Fx = min(Qx,max(-Qx,Fx_req))
B = Qy*sqrt(max(0,1-(Fx/Qx)^2))
Fy = -B*tanh(C*alpha/B) if B>0 else 0
u2 = (Fx/Qx)^2+(Fy/Qy)^2 <= 1
```

This explicitly prioritizes longitudinal demand. Both signs of braking/drive
share the ellipse; no arbitrary residual grip is retained at |Fx|=Qx. Smooth
lateral saturation is a constitutive PRIOR, not a fitted force-slip curve.
`AxleForce` reports requested/applied Fx, unsaturated `-C*alpha`, applied Fy,
remaining budget, utilization and over-budget/projected indicators.

```
Fxf_body = Fx_f*cos(delta)-Fy_f*sin(delta)
Fyf_body = Fx_f*sin(delta)+Fy_f*cos(delta)
Fx_body = Fxf_body+Fx_r-R
Fy_body = Fyf_body+Fy_r
Mz = a*Fyf_body-b*Fy_r
Xdot = vx*cos(psi)-vy*sin(psi)
Ydot = vx*sin(psi)+vy*cos(psi)
psidot = r
vxdot = r*vy+Fx_body/m
vydot = -r*vx+Fy_body/m
rdot = Mz/Iz
```

Front longitudinal force contributes to lateral body force and yaw when steered;
omitting this rotation violates the declared wrench and power balance.

Energy balance, excluding wheel rotation/suspension:

```
T = .5*m*(vx^2+vy^2)+.5*Iz*r^2
Tdot = m*(vx*vxdot+vy*vydot)+Iz*r*rdot
     = Fx_f*Vxf+Fy_f*Vyf+Fx_r*vx+Fy_r*Vyr-R*vx
Fy_f*Vyf+Fy_r*Vyr <= 0
```

Hand force fixture: Fz=1000 N, mux=2, muy=1, request Fx=1200 N,
C=20000 N/rad, alpha=.08 rad gives Qx=2000 N, B=800 N,
Fy=-800*tanh(2) N. Flat-load fixture m=900 kg, a=1.6 m, b=2 m yields
4905/3924 N, summing to 8829 N and balancing pitch moment.

Small-angle, constant-vx reference for z=[vy,r], zero longitudinal forces:

```
zdot = A*z+Bdelta*delta
A11 = -(Cf+Cr)/(m*vx)
A12 = (-a*Cf+b*Cr)/(m*vx)-vx
A21 = (-a*Cf+b*Cr)/(Iz*vx)
A22 = -(a*a*Cf+b*b*Cr)/(Iz*vx)
Bdelta = [Cf/m,a*Cf/Iz]
z(t) = (I-exp(A*t))*(-inv(A)*Bdelta*delta)  [z(0)=0]
```

This is the local zero-slip Jacobian, not a global saturation theorem. A separate
oversteering parameter fixture deliberately has a positive eigenvalue. RK4
checks state support at all four stages and each accepted endpoint; its reported
`stage_evaluations` includes all five checks per substep. Controls are left-held.
The R030 adapter instead holds throttle/DRS and recomputes its power-dependent
force at every stage, restricted to the original straight/high-speed domain.

The independent audit reconstructs scalar equations without the primary RHS,
tyre helper, force adapter or RK4. DOP853 supplies a second integration method.
A terminal root independently locates the unchanged saturated-rear challenge's
support exit. Both completed paths and the rejected challenge's bounded prefix
are preserved. No synthetic stability result establishes public cornering
accuracy, actual axle loads, full-lap autonomy or production readiness.
