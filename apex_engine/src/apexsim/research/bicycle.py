"""R031 forward-only planar bicycle ADAPTATION; all defaults are generic PRIORS.

SI units, body x forward/y left/z up. Axle tyre forces use wheel coordinates.
This research interface does not consume the production normalized steering proxy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import atan2, cos, sin, sqrt, tanh

import numpy as np

from apexsim.research.longitudinal_calibration import SpecificPowerDrag


@dataclass(frozen=True)
class BicycleParameters:
    """Static-load axle model, not an identified Formula One vehicle."""

    mass_kg: float = 900.
    yaw_inertia_kgm2: float = 1500.
    front_distance_m: float = 1.6
    rear_distance_m: float = 2.
    front_stiffness_nprad: float = 100000.
    rear_stiffness_nprad: float = 120000.
    mu_x: float = 1.5
    mu_y: float = 1.7
    gravity_mps2: float = 9.81
    min_vx_mps: float = 5.
    max_vx_mps: float = 110.
    max_sideslip_rad: float = .35
    max_yaw_rate_radps: float = 2.
    max_steering_rad: float = .35
    max_axle_slip_rad: float = .5

    def __post_init__(self) -> None:
        if (not np.isfinite(list(asdict(self).values())).all()
                or any(v <= 0 for v in asdict(self).values())
                or self.min_vx_mps >= self.max_vx_mps
                or max(self.max_sideslip_rad, self.max_steering_rad, self.max_axle_slip_rad) >= np.pi/2):
            raise ValueError("R031 parameters require positive finite SI values and forward-only bounds")

    @property
    def axle_loads_n(self) -> tuple[float, float]:
        """Flat-road static loads, with no aero or acceleration load transfer."""
        length = self.front_distance_m+self.rear_distance_m
        return (self.mass_kg*self.gravity_mps2*self.rear_distance_m/length,
                self.mass_kg*self.gravity_mps2*self.front_distance_m/length)


@dataclass(frozen=True)
class BicycleState:
    """SIMULATED [inertial x/y, heading, body vx/vy, yaw rate] in SI units."""

    x_m: float = 0.
    y_m: float = 0.
    heading_rad: float = 0.
    vx_mps: float = 40.
    vy_mps: float = 0.
    yaw_rate_radps: float = 0.

    def array(self) -> np.ndarray:
        return np.array(list(asdict(self).values()), dtype=float)

    @classmethod
    def from_array(cls, values: np.ndarray) -> BicycleState:
        values = np.asarray(values, dtype=float)
        if values.shape != (6,) or not np.isfinite(values).all():
            raise ValueError("R031 state requires six finite SI coordinates")
        return cls(*map(float, values))


@dataclass(frozen=True)
class BicycleControl:
    """Supplied steering [rad], axle longitudinal requests [N], body resistance [N]."""

    steering_rad: float = 0.
    front_fx_request_n: float = 0.
    rear_fx_request_n: float = 0.
    resistance_n: float = 0.

    def __post_init__(self) -> None:
        if not np.isfinite(list(asdict(self).values())).all() or self.resistance_n < 0:
            raise ValueError("R031 controls require finite forces/angle and nonnegative resistance")


@dataclass(frozen=True)
class AxleForce:
    """Applied wheel forces and exposed friction constraint intervention."""

    normal_n: float
    slip_rad: float
    requested_fx_n: float
    fx_n: float
    linear_fy_n: float
    fy_n: float
    lateral_budget_n: float
    utilization_squared: float
    longitudinal_projected: bool
    lateral_demand_exceeds_budget: bool


def axle_force(slip_rad: float, requested_fx_n: float, normal_n: float,
               stiffness_nprad: float, mu_x: float, mu_y: float) -> AxleForce:
    """Longitudinal-priority ellipse with dissipative tanh lateral saturation.

    The longitudinal force projection is a declared physical constraint. It is
    reported, never used to hide an invalid state. Stiffness is per axle [N/rad].
    """
    if (not np.isfinite([slip_rad, requested_fx_n, normal_n, stiffness_nprad, mu_x, mu_y]).all()
            or min(normal_n, stiffness_nprad, mu_x, mu_y) <= 0 or abs(slip_rad) >= np.pi/2):
        raise ValueError("R031 axle requires finite forward slip and positive load/stiffness/grip")
    qx, qy = mu_x*normal_n, mu_y*normal_n
    fx = min(qx, max(-qx, requested_fx_n))
    budget = qy*sqrt(max(0., 1-(fx/qx)**2))
    linear = -stiffness_nprad*slip_rad
    fy = budget*tanh(linear/budget) if budget > 0 else 0.
    return AxleForce(normal_n, slip_rad, requested_fx_n, fx, linear, fy, budget,
                     (fx/qx)**2+(fy/qy)**2, fx != requested_fx_n, abs(linear) > budget)


@dataclass(frozen=True)
class BicycleDiagnostics:
    """Axle and body wrench, power [W] and inertial accelerations [m/s²]."""

    front: AxleForce
    rear: AxleForce
    body_fx_n: float
    body_fy_n: float
    yaw_moment_nm: float
    front_wheel_vx_mps: float
    front_wheel_vy_mps: float
    rear_wheel_vy_mps: float
    lateral_slip_power_w: float
    wheel_power_w: float
    kinetic_energy_rate_w: float


def validate_state(state: BicycleState, params: BicycleParameters) -> None:
    """Abstain outside the finite forward-only support; never clip a state."""
    if (not np.isfinite(state.array()).all() or not params.min_vx_mps <= state.vx_mps <= params.max_vx_mps
            or abs(atan2(state.vy_mps, state.vx_mps)) > params.max_sideslip_rad
            or abs(state.yaw_rate_radps) > params.max_yaw_rate_radps):
        raise ValueError("R031 state outside forward-speed/sideslip/yaw support; no state clipping")


def bicycle_rhs(state: BicycleState, control: BicycleControl,
                params: BicycleParameters) -> tuple[np.ndarray, BicycleDiagnostics]:
    """Return six SI derivatives and force diagnostics; no mutation or state reset."""
    validate_state(state, params)
    if abs(control.steering_rad) > params.max_steering_rad:
        raise ValueError("R031 road-wheel steering outside declared radian support")
    vx, vy, r = state.vx_mps, state.vy_mps, state.yaw_rate_radps
    a, b = params.front_distance_m, params.rear_distance_m
    c, s = cos(control.steering_rad), sin(control.steering_rad)
    front_vx, front_vy = c*vx+s*(vy+a*r), -s*vx+c*(vy+a*r)
    rear_vy = vy-b*r
    af, ar = atan2(front_vy, front_vx), atan2(rear_vy, vx)
    if front_vx <= 0 or max(abs(af), abs(ar)) > params.max_axle_slip_rad:
        raise ValueError("R031 wheel velocity/slip outside forward axle support")
    fzf, fzr = params.axle_loads_n
    front = axle_force(af, control.front_fx_request_n, fzf, params.front_stiffness_nprad, params.mu_x, params.mu_y)
    rear = axle_force(ar, control.rear_fx_request_n, fzr, params.rear_stiffness_nprad, params.mu_x, params.mu_y)
    fxf_body, fyf_body = c*front.fx_n-s*front.fy_n, s*front.fx_n+c*front.fy_n
    fx, fy = fxf_body+rear.fx_n-control.resistance_n, fyf_body+rear.fy_n
    moment = a*fyf_body-b*rear.fy_n
    rhs = np.array([vx*cos(state.heading_rad)-vy*sin(state.heading_rad),
                    vx*sin(state.heading_rad)+vy*cos(state.heading_rad), r,
                    r*vy+fx/params.mass_kg, -r*vx+fy/params.mass_kg, moment/params.yaw_inertia_kgm2])
    power = front.fx_n*front_vx+front.fy_n*front_vy+rear.fx_n*vx+rear.fy_n*rear_vy-control.resistance_n*vx
    energy_rate = params.mass_kg*(vx*rhs[3]+vy*rhs[4])+params.yaw_inertia_kgm2*r*rhs[5]
    diagnostic = BicycleDiagnostics(front, rear, fx, fy, moment, front_vx, front_vy, rear_vy,
                                    front.fy_n*front_vy+rear.fy_n*rear_vy, power, float(energy_rate))
    if not np.isfinite(rhs).all() or not np.isfinite([power, energy_rate]).all():
        raise ValueError("R031 nonfinite force/power propagation")
    return rhs, diagnostic


def kinetic_energy_j(state: BicycleState, params: BicycleParameters) -> float:
    """Planar translational plus yaw kinetic energy; no wheel/suspension energy."""
    validate_state(state, params)
    return .5*(params.mass_kg*(state.vx_mps**2+state.vy_mps**2)+params.yaw_inertia_kgm2*state.yaw_rate_radps**2)


@dataclass(frozen=True)
class StraightPowerDragInput:
    """R030 straight-only consistency adapter; fixed throttle/DRS, state-dependent force.

    Effective ratios are multiplied by the supplied PRIOR mass solely to test
    algebraic compatibility. This does not identify actual engine or tyre forces.
    Grip can limit the request; equivalence holds only when it is unsaturated.
    """

    model: SpecificPowerDrag
    throttle: float = 1.
    drs: int = 0

    def __post_init__(self) -> None:
        if not np.isfinite(self.throttle) or not .98 <= self.throttle <= 1 or self.drs not in (0, 1):
            raise ValueError("R031 R030 adapter requires original full-throttle/DRS support")

    def at(self, state: BicycleState, params: BicycleParameters) -> BicycleControl:
        """Evaluate forces at each RK stage, without treating power as constant force."""
        if not 40 <= state.vx_mps <= 105 or max(abs(state.vy_mps), abs(state.yaw_rate_radps)) > 1e-12:
            raise ValueError("R031 R030 adapter is restricted to straight original speed support")
        drag = self.model.open_drag_per_mass+self.model.extra_closed_drag_per_mass*(1-self.drs)
        return BicycleControl(rear_fx_request_n=params.mass_kg*self.model.power_per_mass*self.throttle/state.vx_mps,
                              resistance_n=params.mass_kg*(drag*state.vx_mps**2+self.model.rolling_acceleration))


def lateral_linear_system(speed_mps: float, params: BicycleParameters) -> tuple[np.ndarray, np.ndarray]:
    """Exact zero-slip Jacobian for [vy,r] at fixed vx, zero longitudinal forces.

    This local small-angle reference is not a finite-slip stability guarantee.
    B multiplies road-wheel steering in radians. Both axle forces are unsaturated.
    """
    if not np.isfinite(speed_mps) or not params.min_vx_mps <= speed_mps <= params.max_vx_mps:
        raise ValueError("R031 linearization speed outside forward support")
    cf, cr = params.front_stiffness_nprad, params.rear_stiffness_nprad
    a, b, m, iz, v = params.front_distance_m, params.rear_distance_m, params.mass_kg, params.yaw_inertia_kgm2, speed_mps
    return (np.array([[-(cf+cr)/(m*v), (-a*cf+b*cr)/(m*v)-v],
                      [(-a*cf+b*cr)/(iz*v), -(a*a*cf+b*b*cr)/(iz*v)]]),
            np.array([cf/m, a*cf/iz]))


@dataclass(frozen=True)
class BicycleRollout:
    """Reproducible sampled trajectory plus all RK-stage constraint diagnostics."""

    time_s: np.ndarray
    states: np.ndarray
    integration_checks: dict


def integrate_bicycle(initial: BicycleState, time_s: np.ndarray,
                      controls: list[BicycleControl | StraightPowerDragInput],
                      params: BicycleParameters, *, max_step_s: float = .01,
                      max_substeps: int = 200000) -> BicycleRollout:
    """Forward RK4, left-held commands; validate every intermediate and final state.

    A StraightPowerDragInput holds throttle/DRS rather than force; the adapter
    resolves its power law at every stage. There are no observation resets,
    speed clipping, low-speed blends or hidden numerical stabilization.
    """
    time_s = np.asarray(time_s, dtype=float)
    if (time_s.ndim != 1 or len(time_s) < 2 or not np.isfinite(time_s).all()
            or time_s[0] < 0 or np.any(np.diff(time_s) <= 0) or len(controls) != len(time_s)-1
            or not all(isinstance(c, (BicycleControl, StraightPowerDragInput)) for c in controls)
            or not np.isfinite(max_step_s) or not 0 < max_step_s <= .02
            or type(max_substeps) is not int or max_substeps < 1):
        raise ValueError("R031 requires increasing finite times, one command/interval and max step <=.02s")
    requested_steps = np.ceil(np.diff(time_s)/max_step_s)
    if not np.isfinite(requested_steps).all() or np.sum(requested_steps) > max_substeps:
        raise ValueError("R031 integration substep budget exceeded")
    validate_state(initial, params)
    checks = {"stage_evaluations": 0, "projected_axle_requests": 0, "lateral_over_budget_axles": 0,
              "maximum_fx_projection_n": 0., "maximum_utilization_squared": 0.,
              "maximum_lateral_slip_power_w": 0., "maximum_power_balance_error_w": 0.,
              "minimum_vx_mps": initial.vx_mps, "maximum_vx_mps": initial.vx_mps,
              "maximum_abs_sideslip_rad": abs(atan2(initial.vy_mps, initial.vx_mps)),
              "maximum_abs_yaw_rate_radps": abs(initial.yaw_rate_radps)}

    def evaluate(values, command):
        state = BicycleState.from_array(values)
        applied = command.at(state, params) if isinstance(command, StraightPowerDragInput) else command
        derivative, d = bicycle_rhs(state, applied, params)
        checks["stage_evaluations"] += 1
        for axle in (d.front, d.rear):
            checks["projected_axle_requests"] += int(axle.longitudinal_projected)
            checks["lateral_over_budget_axles"] += int(axle.lateral_demand_exceeds_budget)
            checks["maximum_fx_projection_n"] = max(checks["maximum_fx_projection_n"], abs(axle.requested_fx_n-axle.fx_n))
            checks["maximum_utilization_squared"] = max(checks["maximum_utilization_squared"], axle.utilization_squared)
        checks["maximum_lateral_slip_power_w"] = max(checks["maximum_lateral_slip_power_w"], d.lateral_slip_power_w)
        checks["maximum_power_balance_error_w"] = max(checks["maximum_power_balance_error_w"], abs(d.wheel_power_w-d.kinetic_energy_rate_w))
        checks["minimum_vx_mps"] = min(checks["minimum_vx_mps"], state.vx_mps)
        checks["maximum_vx_mps"] = max(checks["maximum_vx_mps"], state.vx_mps)
        checks["maximum_abs_sideslip_rad"] = max(checks["maximum_abs_sideslip_rad"], abs(atan2(state.vy_mps, state.vx_mps)))
        checks["maximum_abs_yaw_rate_radps"] = max(checks["maximum_abs_yaw_rate_radps"], abs(state.yaw_rate_radps))
        return derivative

    values = initial.array()
    states = [values.copy()]
    for i, dt in enumerate(np.diff(time_s)):
        count = int(requested_steps[i])
        h, command = dt/count, controls[i]
        for _ in range(count):
            k1 = evaluate(values, command)
            k2 = evaluate(values+h*k1/2, command)
            k3 = evaluate(values+h*k2/2, command)
            k4 = evaluate(values+h*k3, command)
            values = values+h*(k1+2*k2+2*k3+k4)/6
            # Validate the accepted endpoint too; k4 is an intermediate estimate.
            evaluate(values, command)
        states.append(values.copy())
    return BicycleRollout(time_s.copy(), np.array(states), checks)
