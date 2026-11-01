"""R036 simulated-expert steering imitation; all vehicle assumptions remain PRIOR.

Only the bounded steering correction is learned. Accepted R035 and production
sources remain unchanged. Inference reads no demonstrations, expert or event ID.
"""
from __future__ import annotations

from dataclasses import asdict
from math import atan, atan2, cos, hypot, sin, sqrt

import numpy as np

from apexsim.research.aero_bicycle import integrate_aero_bicycle
from apexsim.research.bicycle import BicycleControl, BicycleState
from apexsim.research.transparent_driver import AERO, CAR, DriverMap, speed_profile, wrap

LEADS = (.025, .05, .075, .10)
ALPHAS = (1e-8, 1e-4)
FEATURES = ("speed_squared_over_3600", "curvature_times_50", "preview_curvature_times_50", "velocity_heading_error_rad",
            "cross_track_atan_rad", "yaw_error_radps", "body_sideslip_rad", "previous_steering_rad")
RESIDUAL_LIMIT_RAD = .2


def observation(state: BicycleState, track: DriverMap, station: float, lateral: float, previous: float, lead_s: float) -> np.ndarray:
    """Current simulated state plus known-map preview; no future measured outcomes."""
    if lead_s not in LEADS or not np.isfinite([station, lateral, previous]).all():
        raise ValueError("R036 invalid local observation or preregistered preview")
    speed = hypot(state.vx_mps, state.vy_mps)
    _, heading, curvature = track.at(station)
    _, _, preview = track.at(station+lead_s*speed)
    beta = atan2(state.vy_mps, state.vx_mps)
    return np.array([speed**2/3600, 50*curvature, 50*preview, wrap(heading-state.heading_rad-beta),
                     atan(.8*lateral/(speed+5)), speed*curvature-state.yaw_rate_radps, beta, previous])


def expert_residual(row: np.ndarray) -> float:
    """SIMULATED analytic label; never called by a deployed learned policy."""
    length = CAR.front_distance_m+CAR.rear_distance_m
    understeer = CAR.mass_kg/length*(CAR.rear_distance_m/CAR.front_stiffness_nprad-CAR.front_distance_m/CAR.rear_stiffness_nprad)
    return float((length+understeer*3600*row[0])*(row[2]-row[1])/50)


def baseline_raw(row: np.ndarray) -> float:
    length = CAR.front_distance_m+CAR.rear_distance_m
    understeer = CAR.mass_kg/length*(CAR.rear_distance_m/CAR.front_stiffness_nprad-CAR.front_distance_m/CAR.rear_stiffness_nprad)
    return float((length+understeer*3600*row[0])*row[1]/50+1.5*row[3]-row[4]+.15*row[5])


def design_matrix(x: np.ndarray, degree: int) -> np.ndarray:
    """Explicit constant/linear/upper-triangle quadratic monomials, deterministic order."""
    x = np.asarray(x, float)
    if x.ndim != 2 or x.shape[1] != len(FEATURES) or not np.isfinite(x).all() or degree not in (1, 2):
        raise ValueError("R036 invalid finite feature matrix or degree")
    columns = [np.ones(len(x)), *x.T]
    if degree == 2:
        columns.extend(x[:, i]*x[:, j] for i in range(x.shape[1]) for j in range(i, x.shape[1]))
    return np.column_stack(columns)


def fit_policy(x: np.ndarray, y: np.ndarray, weights: np.ndarray, degree: int, alpha: float) -> dict:
    """Train-only weighted normalization and ridge; unpenalized intercept; no pickle."""
    x, y, weights = np.asarray(x, float), np.asarray(y, float), np.asarray(weights, float)
    if (x.ndim != 2 or x.shape[1] != len(FEATURES) or len(x) < 12 or y.shape != (len(x),) or weights.shape != y.shape
            or not np.isfinite(x).all() or not np.isfinite([y, weights]).all() or np.any(weights <= 0) or alpha not in ALPHAS):
        raise ValueError("R036 invalid training-only arrays, weights or ridge penalty")
    weights = weights/weights.sum()
    mean = weights@x
    variance = weights@((x-mean)**2)
    scale = np.sqrt(variance)
    constant = scale < 1e-12
    scale[constant] = 1.
    matrix = design_matrix((x-mean)/scale, degree)
    penalty = np.eye(matrix.shape[1])*sqrt(alpha)
    penalty[0, 0] = 0.
    augmented = np.vstack([matrix*np.sqrt(weights[:, None]), penalty])
    target = np.r_[y*np.sqrt(weights), np.zeros(matrix.shape[1])]
    coefficients, _, rank, singular = np.linalg.lstsq(augmented, target, rcond=None)
    error = matrix@coefficients-y
    return {"schema_version": "apex-imitation-policy-v1", "feature_names": list(FEATURES), "degree": degree, "alpha": alpha,
            "mean": mean.tolist(), "scale": scale.tolist(), "constant_features": np.flatnonzero(constant).tolist(),
            "coefficients": coefficients.tolist(), "training_rows": len(x), "augmented_rank": int(rank),
            "augmented_condition_number": float(singular[0]/singular[-1]), "parameters": len(coefficients),
            "training_weighted_mse_rad2": float(weights@(error**2)), "residual_limit_rad": RESIDUAL_LIMIT_RAD,
            "target_truth": "SIMULATED_EXPERT_STEERING_RESIDUAL; NOT_MEASURED_HUMAN_ACTION"}


def predict_residual(model: dict, row: np.ndarray) -> float:
    """Portable pure-numeric inference; raw correction returned before exposed bound."""
    if (model.get("schema_version") != "apex-imitation-policy-v1" or model.get("feature_names") != list(FEATURES)
            or model.get("residual_limit_rad") != RESIDUAL_LIMIT_RAD):
        raise ValueError("R036 policy feature/schema/bound mismatch")
    mean, scale, coefficients = (np.asarray(model[k], float) for k in ("mean", "scale", "coefficients"))
    if (row.shape != (len(FEATURES),) or mean.shape != row.shape or scale.shape != row.shape or np.any(scale <= 0)
            or not all(np.isfinite(a).all() for a in (row, mean, scale, coefficients))):
        raise ValueError("R036 invalid finite policy parameters/observation")
    matrix = design_matrix(((row-mean)/scale)[None], model["degree"])
    if coefficients.shape != (matrix.shape[1],):
        raise ValueError("R036 policy coefficient dimension mismatch")
    return float(matrix[0]@coefficients)


def apply_steering(raw: float, state: BicycleState, track: DriverMap, profile: np.ndarray, station: float, previous: float):
    """Exact R035 actuator/force equations, evaluated at actual applied steering."""
    if not np.isfinite(raw):
        raise ValueError("R036 nonfinite raw action")
    steering = float(np.clip(raw, max(-CAR.max_steering_rad, previous-.15), min(CAR.max_steering_rad, previous+.15)))
    speed = hypot(state.vx_mps, state.vy_mps)
    target = float(track.interpolate(profile, station))
    gradient = float(track.interpolate((np.roll(profile, -1)-profile)/track.spacing, station))
    acceleration = .8*(target-speed)+target*gradient
    q = .5*AERO.air_density_kgpm3*speed**2
    rolling = CAR.mass_kg*.015*CAR.gravity_mps2*speed/sqrt(speed**2+4)
    requested = CAR.mass_kg*acceleration+q*AERO.drag_area_m2+rolling
    length = CAR.front_distance_m+CAR.rear_distance_m
    total = CAR.mass_kg*CAR.gravity_mps2+q*AERO.downforce_area_m2
    base = CAR.mass_kg*CAR.gravity_mps2*CAR.rear_distance_m/length+AERO.front_downforce_fraction*q*AERO.downforce_area_m2
    radius = AERO.cg_height_m/length*(CAR.mu_x+CAR.mu_y*abs(sin(steering)))*total
    front_cap = .75*CAR.mu_x*max(AERO.minimum_contact_load_n, base-radius)
    rear_cap = .75*CAR.mu_x*max(AERO.minimum_contact_load_n, total-base-radius)
    if requested >= 0:
        front, rear = 0., min(requested, 740000*.92/max(speed, 8), rear_cap)
    else:
        braking = min(-requested, 40000)
        front, rear = -min(.6*braking, front_cap), -min(.4*braking, rear_cap)
    return BicycleControl(steering, front, rear, rolling), {"steering_projected": abs(raw-steering) > 1e-15,
                                                         "force_projected": abs(front+rear-requested) > 1e-9}


def policy_command(state: BicycleState, track: DriverMap, profile: np.ndarray, station: float, lateral: float,
                   previous: float, lead_s: float, kind: str, model: dict | None = None):
    row = observation(state, track, station, lateral, previous, lead_s)
    base = baseline_raw(row)
    if kind == "transparent":
        raw_residual = 0.
    elif kind == "expert":
        raw_residual = expert_residual(row)
    elif kind == "learned" and model is not None:
        raw_residual = predict_residual(model, row)
    else:
        raise ValueError("R036 unknown policy or missing learned checkpoint")
    bounded = float(np.clip(raw_residual, -RESIDUAL_LIMIT_RAD, RESIDUAL_LIMIT_RAD)) if kind == "learned" else raw_residual
    action, log = apply_steering(base+bounded, state, track, profile, station, previous)
    return action, row, {**log, "raw_residual_rad": raw_residual, "bounded_residual_rad": bounded,
                         "residual_projected": abs(raw_residual-bounded) > 1e-15}


def station_mse(track: DriverMap, arrays: dict) -> float | None:
    progress = arrays["station_m"]
    if progress[-1] < track.length_m or np.any(np.diff(progress) <= 0):
        return None
    values = np.interp(np.linspace(0, track.length_m, 2001), progress, arrays["lateral_m"])
    return float(np.mean(values**2))


def rollout_policy(track: DriverMap, pace: tuple, initial_speed: float, kind: str, lead_s: float, model: dict | None = None,
                   *, max_step: float = .02, maximum_time: float = 300., initial_lateral: float = 0., initial_heading: float = 0.):
    """Generate actions in continuous R032 physics; retain complete failed prefixes."""
    profile = speed_profile(track, *pace)
    xy, heading, _ = track.at(0.)
    xy = xy+initial_lateral*np.array([-sin(heading), cos(heading)])
    state = BicycleState(*xy, heading+initial_heading, initial_speed, 0., 0.)
    times, states, stations, laterals = [0.], [state.array()], [0.], [initial_lateral]
    controls, observations, diagnostics = [], [], []
    checks, previous, failure, attempted, rejected = {}, 0., None, None, None
    for _ in range(int(maximum_time/.1)):
        try:
            action, row, log = policy_command(state, track, profile, stations[-1], laterals[-1], previous, lead_s, kind, model)
            attempted = asdict(action)
            path = integrate_aero_bicycle(state, np.array([0., .1]), [action], CAR, AERO, max_step_s=max_step)
            next_state = BicycleState.from_array(path.states[-1])
            station, lateral = track.project(path.states[-1, :2], stations[-1])
        except ValueError as exc:
            failure = str(exc)
            rejected = getattr(exc, "state", None)
            break
        for key, value in path.integration_checks.items():
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
        observations.append(row)
        diagnostics.append([log[k] for k in ("raw_residual_rad", "bounded_residual_rad", "steering_projected", "force_projected", "residual_projected")])
        if station >= track.length_m:
            break
    complete = stations[-1] >= track.length_m
    if not complete and failure is None:
        failure = "R036 elapsed-time budget exceeded"
    finish = times[-2]+.1*(track.length_m-stations[-2])/(stations[-1]-stations[-2]) if complete else None
    arrays = {"time_s": np.array(times), "states": np.array(states), "station_m": np.array(stations), "lateral_m": np.array(laterals),
              "controls": np.array(controls).reshape(-1, 4), "features": np.array(observations).reshape(-1, len(FEATURES)),
              "diagnostics": np.array(diagnostics).reshape(-1, 5)}
    mse = station_mse(track, arrays)
    supported = bool(complete and mse is not None and max(abs(np.array(laterals))) <= 5 and np.percentile(abs(np.array(laterals)), 95) <= 2
                     and checks.get("maximum_utilization_squared", 2) <= 1+1e-12 and checks.get("minimum_contact_load_n", 0) > 0
                     and checks.get("maximum_pitch_residual_nm", 1) <= 1e-6 and checks.get("maximum_power_balance_error_w", 1) <= 1e-6)
    return {"kind": kind, "lead_s": lead_s, "completed": complete, "passed": supported, "failure": failure,
            "attempted_final_control": attempted if failure else None, "rejected_state": rejected.tolist() if rejected is not None else None,
            "completion_time_s": finish, "progress_m": stations[-1], "station_weighted_mse_m2": mse,
            "maximum_lateral_error_m": float(max(abs(np.array(laterals)))), "p95_lateral_error_m": float(np.percentile(abs(np.array(laterals)), 95)),
            "final_lateral_error_m": laterals[-1], "checks": checks,
            "interventions": {"steering": int(np.sum(arrays["diagnostics"][:, 2])), "force": int(np.sum(arrays["diagnostics"][:, 3])),
                              "learned_residual": int(np.sum(arrays["diagnostics"][:, 4]))},
            "state_truth": "SIMULATED; INITIAL_MAP_POSE_RECONSTRUCTED; INITIAL_SPEED_SOURCE_OR_FIXTURE; INITIAL_VY_R_PRIOR",
            "vehicle_truth": "GENERIC_PRIOR", "production_promotion": False}, arrays
