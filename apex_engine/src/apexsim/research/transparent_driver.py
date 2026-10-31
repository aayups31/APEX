"""R035 conditional map-based driver, generic-prior research vehicle only.

Known reference geometry is preview information, not observed future controls.
Actuator projections are physical limits; chassis states are never clipped/reset.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import atan, atan2, cos, hypot, sin, sqrt

import numpy as np

from apexsim.research.aero_bicycle import AeroParameters, integrate_aero_bicycle
from apexsim.research.bicycle import BicycleControl, BicycleParameters, BicycleState
from apexsim.research.reference_geometry import ReferenceCurve

PACE_CANDIDATES = tuple((f, v) for f in (.35, .5, .65) for v in (60., 80., 95.))
CAR = BicycleParameters(max_steering_rad=.6)
AERO = AeroParameters()


def wrap(angle: float) -> float:
    return atan2(sin(angle), cos(angle))


@dataclass(frozen=True)
class DriverMap:
    """Periodic linear tabulation of a frozen supplied smooth reference map."""

    length_m: float
    xy: np.ndarray
    tangent: np.ndarray
    curvature: np.ndarray

    def __post_init__(self):
        n = len(self.xy)
        if (not np.isfinite(self.length_m) or self.length_m <= 1 or n < 16 or self.length_m/n > 2+1e-9
                or self.xy.shape != (n, 2) or self.tangent.shape != (n, 2) or self.curvature.shape != (n,)
                or not all(np.isfinite(a).all() for a in (self.xy, self.tangent, self.curvature))
                or not np.allclose(np.linalg.norm(self.tangent, axis=1), 1, atol=1e-7)
                or np.min(np.linalg.norm(np.roll(self.xy, -1, axis=0)-self.xy, axis=1)) < 1e-6):
            raise ValueError("R035 invalid finite periodic map tabulation")

    @classmethod
    def from_curve(cls, curve: ReferenceCurve):
        n = int(np.ceil(curve.length_m/2))
        xy, tangent, curvature = curve.geometry(np.arange(n)*curve.length_m/n)
        return cls(curve.length_m, xy, tangent, curvature)

    @property
    def spacing(self):
        return self.length_m/len(self.xy)

    def interpolate(self, values, station):
        phase = np.asarray(station) % self.length_m/self.spacing
        i = np.floor(phase).astype(int)
        fraction = phase-i
        if values.ndim == 2:
            fraction = fraction[..., None]
        return values[i]*(1-fraction)+values[(i+1) % len(values)]*fraction

    def at(self, station: float):
        xy = self.interpolate(self.xy, station)
        tangent = self.interpolate(self.tangent, station)
        return xy, atan2(tangent[1], tangent[0]), float(self.interpolate(self.curvature, station))

    def project(self, xy: np.ndarray, previous: float):
        """Exact local segment projection, unwrapped through the seam; no global jumps."""
        center = int(np.floor(previous/self.spacing))
        radius = int(np.ceil(40/self.spacing))
        unwrapped = np.arange(center-radius, center+radius+1)
        ids = unwrapped % len(self.xy)
        start = self.xy[ids]
        direction = self.xy[(ids+1) % len(self.xy)]-start
        delta = np.asarray(xy)-start
        fraction = np.clip(np.sum(delta*direction, axis=1)/np.sum(direction**2, axis=1), 0, 1)
        residual = delta-fraction[:, None]*direction
        distances = np.sum(residual**2, axis=1)
        best = int(np.argmin(distances))
        station = float((unwrapped[best]+fraction[best])*self.spacing)
        tangent = direction[best]/np.linalg.norm(direction[best])
        lateral = float(tangent[0]*residual[best, 1]-tangent[1]*residual[best, 0])
        if station < previous-1 or station > previous+30 or sqrt(float(distances[best])) > 5:
            raise ValueError("R035 local projection/progress/reference corridor exceeded")
        return station, lateral


def speed_profile(track: DriverMap, fraction: float, maximum: float, p=CAR, aero=AERO) -> np.ndarray:
    """Curvature/downforce inequality plus periodic backward braking reachability."""
    if (fraction, maximum) not in PACE_CANDIDATES:
        raise ValueError("R035 pace outside preregistered candidate grid")
    coefficient = abs(track.curvature)-fraction*p.mu_y*.5*aero.air_density_kgpm3*aero.downforce_area_m2/p.mass_kg
    speed2 = np.full(len(track.xy), maximum**2)
    positive = coefficient > 0
    speed2[positive] = np.minimum(maximum**2, fraction*p.mu_y*p.gravity_mps2/coefficient[positive])
    # Two complete periodic sweeps allow every corner's braking cone across the seam.
    for _ in range(2):
        for i in range(len(speed2)-1, -1, -1):
            speed2[i] = min(speed2[i], speed2[(i+1) % len(speed2)]+2*6*track.spacing)
    result = np.sqrt(speed2)
    if result.min() < p.min_vx_mps:
        raise ValueError("R035 map pace below research forward-speed support")
    return result


def command(state: BicycleState, track: DriverMap, profile: np.ndarray, station: float, lateral: float,
            previous_steering: float, *, mode="feedback", dt=.1, p=CAR, aero=AERO):
    """Only simulated present state, actuator memory and supplied map enter feedback."""
    _, heading, curvature = track.at(station)
    speed = hypot(state.vx_mps, state.vy_mps)
    length = p.front_distance_m+p.rear_distance_m
    understeer = p.mass_kg/length*(p.rear_distance_m/p.front_stiffness_nprad-p.front_distance_m/p.rear_stiffness_nprad)
    if mode == "feedback":
        velocity_heading = state.heading_rad+atan2(state.vy_mps, state.vx_mps)
        raw = ((length+understeer*speed**2)*curvature+1.5*wrap(heading-velocity_heading)
               -atan(.8*lateral/(speed+5))+.15*(speed*curvature-state.yaw_rate_radps))
    elif mode == "pure_pursuit":
        goal, _, _ = track.at(station+6+.3*speed)
        offset = goal-np.array([state.x_m, state.y_m])
        body_lateral = -sin(state.heading_rad)*offset[0]+cos(state.heading_rad)*offset[1]
        raw = atan(2*length*body_lateral/float(offset@offset))
    else:
        raise ValueError("R035 unknown steering policy")
    steering = float(np.clip(raw, max(-p.max_steering_rad, previous_steering-1.5*dt), min(p.max_steering_rad, previous_steering+1.5*dt)))
    target = float(track.interpolate(profile, station))
    gradient = float(track.interpolate((np.roll(profile, -1)-profile)/track.spacing, station))
    acceleration = .8*(target-speed)+target*gradient
    q = .5*aero.air_density_kgpm3*speed**2
    rolling = p.mass_kg*.015*p.gravity_mps2*speed/sqrt(speed**2+4)
    requested = p.mass_kg*acceleration+q*aero.drag_area_m2+rolling
    total = p.mass_kg*p.gravity_mps2+q*aero.downforce_area_m2
    base = p.mass_kg*p.gravity_mps2*p.rear_distance_m/length+aero.front_downforce_fraction*q*aero.downforce_area_m2
    radius = aero.cg_height_m/length*(p.mu_x+p.mu_y*abs(sin(steering)))*total
    front_cap = .75*p.mu_x*max(aero.minimum_contact_load_n, base-radius)
    rear_cap = .75*p.mu_x*max(aero.minimum_contact_load_n, total-base-radius)
    if requested >= 0:
        front, rear = 0., min(requested, 740000*.92/max(speed, 8), rear_cap)
    else:
        braking = min(-requested, 40000)
        front, rear = -min(.6*braking, front_cap), -min(.4*braking, rear_cap)
    applied = BicycleControl(steering, front, rear, rolling)
    return applied, {"raw_steering_rad": float(raw), "applied_steering_rad": steering, "steering_projected": raw != steering,
                     "target_speed_mps": target, "requested_net_acceleration_mps2": acceleration,
                     "requested_tyre_force_n": requested, "front_capacity_n": front_cap, "rear_capacity_n": rear_cap,
                     "force_projected": abs(front+rear-requested) > 1e-9}


def simulate_driver(track: DriverMap, pace: tuple, initial_speed: float, *, mode="feedback", max_step=.02,
                    maximum_time=300., initial_lateral=0., initial_heading_error=0.):
    """Continuous six-state R032 dynamics, sampled-data actions, complete failure prefix."""
    profile = speed_profile(track, *pace)
    xy, heading, _ = track.at(0.)
    xy = xy+initial_lateral*np.array([-sin(heading), cos(heading)])
    state = BicycleState(*xy, heading+initial_heading_error, initial_speed, 0., 0.)
    times, states, stations, laterals, controls, logs = [0.], [state.array()], [0.], [initial_lateral], [], []
    checks, previous, failure, attempted = {}, 0., None, None
    for _ in range(int(maximum_time/.1)):
        try:
            action, log = command(state, track, profile, stations[-1], laterals[-1], previous, mode=mode)
            attempted = asdict(action)
            rollout = integrate_aero_bicycle(state, np.array([0., .1]), [action], CAR, AERO, max_step_s=max_step)
            next_state = BicycleState.from_array(rollout.states[-1])
            station, lateral = track.project(rollout.states[-1, :2], stations[-1])
        except ValueError as exc:
            failure = str(exc)
            break
        for key, value in rollout.integration_checks.items():
            if key.startswith("maximum"):
                checks[key] = max(checks.get(key, 0.), value)
            elif key.startswith("minimum"):
                checks[key] = min(checks.get(key, float("inf")), value)
            else:
                checks[key] = checks.get(key, 0)+value
        state, previous = next_state, action.steering_rad
        times.append(times[-1]+.1)
        states.append(state.array())
        stations.append(station)
        laterals.append(lateral)
        controls.append(list(asdict(action).values()))
        logs.append(log)
        if station >= track.length_m:
            break
    complete = stations[-1] >= track.length_m
    if not complete and failure is None:
        failure = "R035 maximum elapsed time exceeded"
    completion = None
    if complete:
        completion = times[-2]+.1*(track.length_m-stations[-2])/(stations[-1]-stations[-2])
    passed = bool(complete and max(abs(np.array(laterals))) <= 5 and np.percentile(abs(np.array(laterals)), 95) <= 2
                  and checks.get("maximum_utilization_squared", 2) <= 1+1e-12 and checks.get("minimum_contact_load_n", 0) > 0
                  and checks.get("maximum_pitch_residual_nm", 1) <= 1e-6 and checks.get("maximum_power_balance_error_w", 1) <= 1e-6)
    return {"completed": complete, "passed": passed, "failure": failure, "attempted_final_control": attempted if failure else None,
            "completion_time_s": completion, "progress_m": stations[-1], "maximum_lateral_error_m": float(max(abs(np.array(laterals)))),
            "p95_lateral_error_m": float(np.percentile(abs(np.array(laterals)), 95)), "checks": checks, "mode": mode,
            "actuator_projections": {"steering": sum(r["steering_projected"] for r in logs), "force": sum(r["force_projected"] for r in logs)},
            "state_truth": "SIMULATED; INITIAL_MAP_POSE_RECONSTRUCTED; INITIAL_SPEED_OBSERVED; INITIAL_VY_YAW_RATE_PRIOR",
            "vehicle_truth": "GENERIC_PRIOR", "production_promotion": False}, {
                "time_s": np.array(times), "states": np.array(states), "station_m": np.array(stations), "lateral_m": np.array(laterals),
                "controls": np.array(controls).reshape(-1, 4), "profile_mps": profile,
                "action_diagnostics": np.array([[r[k] for k in ("raw_steering_rad", "target_speed_mps", "requested_tyre_force_n", "front_capacity_n", "rear_capacity_n")] for r in logs]).reshape(-1, 5)}
