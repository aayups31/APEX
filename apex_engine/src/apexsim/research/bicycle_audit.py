"""Independent scalar wheel-force equations and DOP853 reference for R031.

Does not call bicycle_rhs, axle_force, RK4, or the R030 force adapter.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.integrate import solve_ivp

from apexsim.research.bicycle import BicycleControl, BicycleParameters, StraightPowerDragInput


def independent_rhs(values: np.ndarray, command: BicycleControl | StraightPowerDragInput,
                    p: BicycleParameters) -> np.ndarray:
    """Rebuild the planar Newton/Euler equations with independent scalar arithmetic."""
    _, _, psi, vx, vy, yaw = values
    if isinstance(command, StraightPowerDragInput):
        model = command.model
        delta, front_request = 0., 0.
        rear_request = p.mass_kg*model.power_per_mass*command.throttle/vx
        resistance = p.mass_kg*((model.open_drag_per_mass+model.extra_closed_drag_per_mass*(1-command.drs))*vx*vx+model.rolling_acceleration)
    else:
        delta, front_request, rear_request, resistance = command.steering_rad, command.front_fx_request_n, command.rear_fx_request_n, command.resistance_n
    length = p.front_distance_m+p.rear_distance_m
    load_front = p.mass_kg*p.gravity_mps2*p.rear_distance_m/length
    load_rear = p.mass_kg*p.gravity_mps2*p.front_distance_m/length
    slip_front = math.atan2(vy+p.front_distance_m*yaw, vx)-delta
    slip_rear = math.atan2(vy-p.rear_distance_m*yaw, vx)
    forces = []
    for requested, load, stiffness, slip in (
            (front_request, load_front, p.front_stiffness_nprad, slip_front),
            (rear_request, load_rear, p.rear_stiffness_nprad, slip_rear)):
        applied_x = math.copysign(min(abs(requested), p.mu_x*load), requested)
        remaining = math.sqrt(max(0., (p.mu_y*load)**2*(1-(applied_x/(p.mu_x*load))**2)))
        applied_y = -remaining*math.tanh(stiffness*slip/remaining) if remaining else 0.
        forces.append((applied_x, applied_y))
    front_x = forces[0][0]*math.cos(delta)-forces[0][1]*math.sin(delta)
    front_y = forces[0][0]*math.sin(delta)+forces[0][1]*math.cos(delta)
    return np.array([vx*math.cos(psi)-vy*math.sin(psi), vx*math.sin(psi)+vy*math.cos(psi), yaw,
                     (front_x+forces[1][0]-resistance)/p.mass_kg+yaw*vy,
                     (front_y+forces[1][1])/p.mass_kg-yaw*vx,
                     (p.front_distance_m*front_y-p.rear_distance_m*forces[1][1])/p.yaw_inertia_kgm2])


def independent_trajectory(initial: np.ndarray, time_s: np.ndarray,
                           commands: list[BicycleControl | StraightPowerDragInput],
                           params: BicycleParameters) -> np.ndarray:
    """Integrate each held-input interval, continuing simulated state without resets."""
    states = [np.array(initial, dtype=float)]
    for i, dt in enumerate(np.diff(time_s)):
        command = commands[i]
        solved = solve_ivp(lambda t, y, cmd=command: independent_rhs(y, cmd, params),
                           (0., float(dt)), states[-1], method="DOP853", rtol=1e-11, atol=1e-12)
        if not solved.success or not np.isfinite(solved.y).all():
            raise ValueError("R031 independent DOP853 solve failed")
        states.append(solved.y[:, -1])
    return np.array(states)


def independent_support_exit(initial: np.ndarray, time_s: np.ndarray,
                             commands: list[BicycleControl | StraightPowerDragInput],
                             params: BicycleParameters) -> tuple[float, np.ndarray]:
    """Locate a forward-speed/sideslip/yaw boundary without the production checker."""
    def boundary(t, y):
        return min(y[3]-params.min_vx_mps, params.max_vx_mps-y[3],
                   params.max_sideslip_rad-abs(math.atan2(y[4], y[3])),
                   params.max_yaw_rate_radps-abs(y[5]))

    boundary.terminal = True
    boundary.direction = -1
    current = np.array(initial, dtype=float)
    for i in range(len(commands)):
        command = commands[i]
        solved = solve_ivp(lambda t, y, cmd=command: independent_rhs(y, cmd, params),
                           (float(time_s[i]), float(time_s[i+1])), current, events=boundary,
                           method="DOP853", rtol=1e-11, atol=1e-12, max_step=.005)
        if not solved.success:
            raise ValueError("R031 independent boundary solve failed")
        if len(solved.t_events[0]):
            return float(solved.t_events[0][0]), solved.y_events[0][0]
        current = solved.y[:, -1]
    raise ValueError("R031 expected support exit was absent")
