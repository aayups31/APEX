"""R032 self-consistent axle loads, aero and planar dynamics; generic PRIORS.

Drag and additional resistance act at CoG; tyre forces act at road height.
Quasi-static pitch balance uses constrained tyre force, never double-counted drag.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import atan2, cos, sin, sqrt

import numpy as np
from scipy.optimize import brentq

from apexsim.research.bicycle import (
    AxleForce,
    BicycleControl,
    BicycleDiagnostics,
    BicycleParameters,
    BicycleRollout,
    BicycleState,
    axle_force,
    validate_state,
)


@dataclass(frozen=True)
class AeroParameters:
    """Coefficient-area products [m²], air [kg/m³], CoG height [m], balance [0,1]."""

    air_density_kgpm3: float = 1.225
    drag_area_m2: float = 1.1
    downforce_area_m2: float = 3.
    front_downforce_fraction: float = .45
    cg_height_m: float = .30
    minimum_contact_load_n: float = 1.

    def __post_init__(self) -> None:
        if (not np.isfinite(list(asdict(self).values())).all() or self.air_density_kgpm3 <= 0
                or min(self.drag_area_m2, self.downforce_area_m2, self.cg_height_m) < 0
                or not 0 <= self.front_downforce_fraction <= 1 or self.minimum_contact_load_n <= 0):
            raise ValueError("R032 finite aero/height/balance/contact parameter bounds violated")


@dataclass(frozen=True)
class LoadedAxles:
    """Solved wheel forces plus normal/pitch equilibrium and root-support diagnostics."""

    front: AxleForce
    rear: AxleForce
    downforce_n: float
    drag_n: float
    speed_mps: float
    tyre_body_fx_n: float
    transfer_to_rear_n: float
    pitch_residual_nm: float
    root_residual_n: float
    load_derivative_bound: float


def solve_axle_loads(state: BicycleState, control: BicycleControl, p: BicycleParameters,
                     aero: AeroParameters) -> LoadedAxles:
    """Solve coupled friction/load balance, with a sufficient uniqueness guarantee.

    Reject loss of contact or unsupported uniqueness rather than clipping loads.
    R030 power-drag inputs are intentionally unsupported to avoid double-counting.
    """
    validate_state(state, p)
    if not isinstance(control, BicycleControl):
        raise ValueError("R032 requires axle-force controls; no implicit R030 drag adapter")
    if abs(control.steering_rad) > p.max_steering_rad:
        raise ValueError("R032 steering outside road-wheel radian support")
    a, b, delta = p.front_distance_m, p.rear_distance_m, control.steering_rad
    length, c, s = a+b, cos(delta), sin(delta)
    vf = c*state.vx_mps+s*(state.vy_mps+a*state.yaw_rate_radps)
    lf = -s*state.vx_mps+c*(state.vy_mps+a*state.yaw_rate_radps)
    af = atan2(lf, vf)
    ar = atan2(state.vy_mps-b*state.yaw_rate_radps, state.vx_mps)
    if vf <= 0 or max(abs(af), abs(ar)) > p.max_axle_slip_rad:
        raise ValueError("R032 forward axle slip support exceeded")
    v = sqrt(state.vx_mps**2+state.vy_mps**2)
    dynamic_pressure = .5*aero.air_density_kgpm3*v*v
    down, drag = dynamic_pressure*aero.downforce_area_m2, dynamic_pressure*aero.drag_area_m2
    total = p.mass_kg*p.gravity_mps2+down
    base = p.mass_kg*p.gravity_mps2*b/length+aero.front_downforce_fraction*down
    # Every possible root lies in this force-bounded interval. Near a partially
    # saturated front ellipse, dFy/dFz is unbounded: do not assert global
    # contraction using a constant mu_y slope bound.
    maximum_tyrex = (p.mu_x+p.mu_y*abs(s))*total
    radius = aero.cg_height_m*maximum_tyrex/length
    # Outward floating-point enclosure keeps an exact capacity-boundary root
    # bracketed; this is a few ULPs, not a physical load correction.
    enclosure_roundoff = 16*np.spacing(total)
    lower = max(aero.minimum_contact_load_n, base-radius-enclosure_roundoff)
    upper = min(total-aero.minimum_contact_load_n, base+radius+enclosure_roundoff)
    if not np.isfinite([total, base, radius]).all() or lower > upper:
        raise ValueError("R032 contact-load domain is empty")
    requested = abs(control.front_fx_request_n)
    if aero.cg_height_m == 0:
        bound = 0.
    elif s == 0:
        bound = aero.cg_height_m/length*2*p.mu_x
    elif requested >= p.mu_x*upper:
        bound = aero.cg_height_m/length*(p.mu_x*abs(c)+p.mu_x)
    elif requested < p.mu_x*lower:
        lateral_slope = p.mu_y/sqrt(1-(requested/(p.mu_x*lower))**2)
        bound = aero.cg_height_m/length*(lateral_slope*abs(s)+p.mu_x)
    else:
        raise ValueError("R032 coupled-load uniqueness unsupported across front saturation boundary")
    if bound >= .9:
        raise ValueError("R032 coupled-load uniqueness support exceeded")

    def forces(front_load):
        front = axle_force(af, control.front_fx_request_n, front_load, p.front_stiffness_nprad, p.mu_x, p.mu_y)
        rear = axle_force(ar, control.rear_fx_request_n, total-front_load, p.rear_stiffness_nprad, p.mu_x, p.mu_y)
        return front, rear, front.fx_n*c-front.fy_n*s+rear.fx_n

    def balance(front_load):
        return front_load-base+aero.cg_height_m*forces(front_load)[2]/length

    if balance(lower) > 0 or balance(upper) < 0:
        raise ValueError("R032 no supported pitch-equilibrium contact bracket; no load clipping")
    fz = base if aero.cg_height_m == 0 else float(brentq(balance, lower, upper, xtol=1e-9, rtol=1e-12))
    front, rear, tyre_fx = forces(fz)
    pitch = -a*front.normal_n+b*rear.normal_n+(aero.front_downforce_fraction*length-b)*down-aero.cg_height_m*tyre_fx
    return LoadedAxles(front, rear, down, drag, v, tyre_fx, aero.cg_height_m*tyre_fx/length,
                       pitch, balance(fz), bound)


@dataclass(frozen=True)
class AeroDiagnostics:
    """Load equilibrium, body wrench and dissipated aerodynamic power [W]."""

    loads: LoadedAxles
    wrench: BicycleDiagnostics
    aero_power_w: float


def aero_bicycle_rhs(state: BicycleState, control: BicycleControl, p: BicycleParameters,
                      aero: AeroParameters) -> tuple[np.ndarray, AeroDiagnostics]:
    """Six-state Newton/Euler dynamics with actual-load tyre constraints."""
    loads = solve_axle_loads(state, control, p, aero)
    f, r = loads.front, loads.rear
    vx, vy, yaw = state.vx_mps, state.vy_mps, state.yaw_rate_radps
    a, b = p.front_distance_m, p.rear_distance_m
    c, s = cos(control.steering_rad), sin(control.steering_rad)
    front_x, front_y = f.fx_n*c-f.fy_n*s, f.fx_n*s+f.fy_n*c
    fx = front_x+r.fx_n-control.resistance_n-loads.drag_n*vx/loads.speed_mps
    fy = front_y+r.fy_n-loads.drag_n*vy/loads.speed_mps
    moment = a*front_y-b*r.fy_n
    derivative = np.array([vx*cos(state.heading_rad)-vy*sin(state.heading_rad),
                           vx*sin(state.heading_rad)+vy*cos(state.heading_rad), yaw,
                           yaw*vy+fx/p.mass_kg, -yaw*vx+fy/p.mass_kg, moment/p.yaw_inertia_kgm2])
    vxf, vyf, vyr = c*vx+s*(vy+a*yaw), -s*vx+c*(vy+a*yaw), vy-b*yaw
    aero_power = -loads.drag_n*loads.speed_mps
    wheel_power = f.fx_n*vxf+f.fy_n*vyf+r.fx_n*vx+r.fy_n*vyr-control.resistance_n*vx+aero_power
    energy_rate = p.mass_kg*(vx*derivative[3]+vy*derivative[4])+p.yaw_inertia_kgm2*yaw*derivative[5]
    wrench = BicycleDiagnostics(f, r, fx, fy, moment, vxf, vyf, vyr, f.fy_n*vyf+r.fy_n*vyr,
                                wheel_power, float(energy_rate))
    if not np.isfinite(derivative).all() or not np.isfinite([wheel_power, energy_rate]).all():
        raise ValueError("R032 nonfinite force/power propagation")
    return derivative, AeroDiagnostics(loads, wrench, aero_power)


def integrate_aero_bicycle(initial: BicycleState, time_s: np.ndarray, controls: list[BicycleControl],
                           p: BicycleParameters, aero: AeroParameters, *, max_step_s: float = .01) -> BicycleRollout:
    """RK4, left-held axle controls; fail at every unsupported intermediate/endpoint."""
    t = np.asarray(time_s, dtype=float)
    if (t.ndim != 1 or len(t) < 2 or not np.isfinite(t).all() or t[0] < 0 or np.any(np.diff(t) <= 0)
            or len(controls) != len(t)-1 or not all(isinstance(c, BicycleControl) for c in controls)
            or not np.isfinite(max_step_s) or not 0 < max_step_s <= .02):
        raise ValueError("R032 invalid increasing times, force controls or maximum timestep")
    count = np.ceil(np.diff(t)/max_step_s)
    if not np.isfinite(count).all() or sum(count) > 200000:
        raise ValueError("R032 integration budget exceeded")
    checks = {"force_evaluations": 0, "maximum_utilization_squared": 0., "projected_axle_requests": 0,
              "maximum_pitch_residual_nm": 0., "maximum_root_residual_n": 0.,
              "maximum_power_balance_error_w": 0., "maximum_positive_slip_power_w": 0.,
              "minimum_contact_load_n": float("inf")}

    def rhs(values):
        derivative, d = aero_bicycle_rhs(BicycleState.from_array(values), command, p, aero)
        checks["force_evaluations"] += 1
        checks["maximum_pitch_residual_nm"] = max(checks["maximum_pitch_residual_nm"], abs(d.loads.pitch_residual_nm))
        checks["maximum_root_residual_n"] = max(checks["maximum_root_residual_n"], abs(d.loads.root_residual_n))
        checks["maximum_power_balance_error_w"] = max(checks["maximum_power_balance_error_w"], abs(d.wrench.kinetic_energy_rate_w-d.wrench.wheel_power_w))
        checks["maximum_positive_slip_power_w"] = max(checks["maximum_positive_slip_power_w"], d.wrench.lateral_slip_power_w)
        for axle in (d.loads.front, d.loads.rear):
            checks["minimum_contact_load_n"] = min(checks["minimum_contact_load_n"], axle.normal_n)
            checks["maximum_utilization_squared"] = max(checks["maximum_utilization_squared"], axle.utilization_squared)
            checks["projected_axle_requests"] += int(axle.longitudinal_projected)
        return derivative

    values = initial.array()
    states = [values.copy()]
    for i, dt in enumerate(np.diff(t)):
        command = controls[i]
        h = dt/int(count[i])
        for _ in range(int(count[i])):
            k1 = rhs(values)
            k2 = rhs(values+h*k1/2)
            k3 = rhs(values+h*k2/2)
            k4 = rhs(values+h*k3)
            values = values+h*(k1+2*k2+2*k3+k4)/6
            rhs(values)
        states.append(values.copy())
    return BicycleRollout(t.copy(), np.array(states), checks)
