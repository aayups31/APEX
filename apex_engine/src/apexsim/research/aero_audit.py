"""R032 independent scalar tyre forces, load bisection and DOP853 dynamics."""
from __future__ import annotations

import math

import numpy as np
from scipy.integrate import solve_ivp

from apexsim.research.aero_bicycle import AeroParameters
from apexsim.research.bicycle import BicycleControl, BicycleParameters


def independent_loaded_rhs(values: np.ndarray, command: BicycleControl, p: BicycleParameters,
                           aero: AeroParameters) -> tuple[np.ndarray, tuple[float, float]]:
    """No primary RHS/tyre/load/root helper calls; solve the scalar balance by bisection."""
    _, _, psi, vx, vy, yaw = values
    delta, a, b = command.steering_rad, p.front_distance_m, p.rear_distance_m
    speed = math.hypot(vx, vy)
    q = aero.air_density_kgpm3*(vx*vx+vy*vy)/2
    down, drag = q*aero.downforce_area_m2, q*aero.drag_area_m2
    total = p.mass_kg*p.gravity_mps2+down
    alpha_f, alpha_r = math.atan2(vy+a*yaw, vx)-delta, math.atan2(vy-b*yaw, vx)

    def force(normal, request, stiffness, alpha):
        fx = math.copysign(min(abs(request), p.mu_x*normal), request)
        # At the exact longitudinal cap the lateral budget is mathematically
        # zero; subtracting two squared loads can invent a tiny nonzero force.
        if abs(request) >= p.mu_x*normal:
            return fx, 0.
        scaled = abs(request)/p.mu_x
        budget = p.mu_y*math.sqrt((normal-scaled)*(normal+scaled))
        fy = -budget*math.tanh(stiffness*alpha/budget) if budget else 0.
        return fx, fy

    def at_load(load):
        f = force(load, command.front_fx_request_n, p.front_stiffness_nprad, alpha_f)
        r = force(total-load, command.rear_fx_request_n, p.rear_stiffness_nprad, alpha_r)
        tx = f[0]*math.cos(delta)-f[1]*math.sin(delta)+r[0]
        balance = load-p.mass_kg*p.gravity_mps2*b/(a+b)-aero.front_downforce_fraction*down+aero.cg_height_m*tx/(a+b)
        return balance, f, r

    low, high = aero.minimum_contact_load_n, total-aero.minimum_contact_load_n
    if at_load(low)[0] > 0 or at_load(high)[0] < 0:
        raise ValueError("Independent R032 contact bracket absent")
    for _ in range(80):
        middle = (low+high)/2
        residual = at_load(middle)[0]
        if residual > 0:
            high = middle
        else:
            low = middle
    load = (low+high)/2
    _, f, r = at_load(load)
    front_x = f[0]*math.cos(delta)-f[1]*math.sin(delta)
    front_y = f[0]*math.sin(delta)+f[1]*math.cos(delta)
    rhs = np.array([vx*math.cos(psi)-vy*math.sin(psi), vx*math.sin(psi)+vy*math.cos(psi), yaw,
                    yaw*vy+(front_x+r[0]-command.resistance_n-drag*vx/speed)/p.mass_kg,
                    -yaw*vx+(front_y+r[1]-drag*vy/speed)/p.mass_kg,
                    (a*front_y-b*r[1])/p.yaw_inertia_kgm2])
    return rhs, (load, total-load)


def independent_loaded_path(initial: np.ndarray, t: np.ndarray, commands: list[BicycleControl],
                            p: BicycleParameters, aero: AeroParameters) -> np.ndarray:
    states = [initial.copy()]
    for i, dt in enumerate(np.diff(t)):
        command = commands[i]
        solved = solve_ivp(lambda time, y, cmd=command: independent_loaded_rhs(y, cmd, p, aero)[0],
                           (0., float(dt)), states[-1], method="DOP853", rtol=1e-11, atol=1e-12)
        if not solved.success:
            raise ValueError("Independent R032 DOP853 failed")
        states.append(solved.y[:, -1])
    return np.array(states)
