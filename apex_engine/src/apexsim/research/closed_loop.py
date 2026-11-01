"""R037 continuous conditional research driving; no seam reset or production use."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict

import numpy as np

from apexsim.research.aero_bicycle import integrate_aero_bicycle
from apexsim.research.bicycle import BicycleState
from apexsim.research.imitation_driver import apply_steering, baseline_raw, policy_command
from apexsim.research.transparent_driver import AERO, CAR, DriverMap, speed_profile

DT = .1


def physical_gate(checks: dict) -> bool:
    return bool(checks.get("maximum_utilization_squared", 2) <= 1+1e-12
                and checks.get("minimum_contact_load_n", 0) > 0
                and checks.get("maximum_pitch_residual_nm", 1) <= 1e-6
                and checks.get("maximum_power_balance_error_w", 1) <= 1e-6)


def lap_metrics(track: DriverMap, arrays: dict, laps: int) -> list[dict]:
    """Station-weighted metrics; partial final laps remain explicitly incomplete."""
    station, time, lateral = (arrays[k] for k in ("station_m", "time_s", "lateral_m"))
    rows = []
    for lap in range(laps):
        start, end = lap*track.length_m, (lap+1)*track.length_m
        complete = bool(station[-1] >= end and np.all(np.diff(station) > 0))
        grid = np.linspace(start, end, 2001) if complete else np.linspace(start, station[-1], 2001) if station[-1] > start else None
        if grid is None:
            break
        values = np.interp(grid, station, lateral)
        rows.append({"lap": lap+1, "completed": complete, "rmse_m": float(np.sqrt(np.mean(values**2))),
                     "p95_m": float(np.percentile(abs(values), 95)), "maximum_error_m": float(max(abs(values))),
                     "finish_time_s": float(np.interp(end, station, time)) if complete else None,
                     "duration_s": float(np.interp(end, station, time)-np.interp(start, station, time)) if complete else None})
    return rows


def run_continuous(track: DriverMap, pace: tuple, speed: float, kind: str, lead: float, model: dict | None,
                   *, laps: int = 5, scenario: str = "nominal", max_step: float = .02,
                   controller: Callable | None = None) -> tuple[dict, dict]:
    """100ms causal control in continuous R032 physics; controller may explicitly abstain.

    Optional controller receives trusted state/map/profile/current projection/memory,
    step index and nominal action/features/log. It returns an action (or None) and
    a JSON decision. It never changes chassis state. Pulses are command disturbances.
    """
    if laps not in (3, 5) or scenario not in ("nominal", "pulse_left", "pulse_right", "challenge"):
        raise ValueError("R037 invalid frozen horizon or disturbance")
    profile = speed_profile(track, *pace)
    xy, heading, _ = track.at(0.)
    state = BicycleState(*xy, heading, speed, 0., 0.)
    times, states, stations, laterals = [0.], [state.array()], [0.], [0.]
    controls, features, decisions, events, checks = [], [], [], [], {}
    previous, failure, rejected, attempted, abstained = 0., None, None, None, False
    targets = [] if scenario == "nominal" else [1.25] if scenario == "challenge" else [1.25, 3.6 if laps == 5 else 2.6]
    remaining, next_event = 0, 0
    amplitude = .3 if scenario == "challenge" else -.01 if scenario == "pulse_right" else .01
    duration = 20 if scenario == "challenge" else 5
    for index in range(int(300*laps/DT)):
        try:
            action, row, log = policy_command(state, track, profile, stations[-1], laterals[-1], previous, lead, kind, model)
            decision = {"mode": "learned" if kind == "learned" else "transparent", "score": None,
                        "reason": None, "fault_active": False, "first_fault_command": False}
            if next_event < len(targets) and stations[-1] >= targets[next_event]*track.length_m:
                remaining = duration
                events.append({"start_index": index, "end_index": index+duration, "amplitude_rad": amplitude,
                               "target_station_m": targets[next_event]*track.length_m})
                next_event += 1
            if remaining:
                raw = baseline_raw(row)+log["bounded_residual_rad"]+amplitude
                action, projection = apply_steering(raw, state, track, profile, stations[-1], previous)
                log.update(projection)
                remaining -= 1
            if controller is not None:
                action, decision = controller(state, track, profile, stations[-1], laterals[-1], previous, index, action, row, log)
                if action is None:
                    decisions.append(decision)
                    failure, abstained = decision["reason"], True
                    break
            attempted = asdict(action)
            path = integrate_aero_bicycle(state, np.array([0., DT]), [action], CAR, AERO, max_step_s=max_step)
            candidate = BicycleState.from_array(path.states[-1])
            station, lateral = track.project(candidate.array()[:2], stations[-1])
        except ValueError as exc:
            failure = str(exc)
            value = getattr(exc, "state", None)
            rejected = value.tolist() if value is not None else None
            break
        for key, value in path.integration_checks.items():
            if key.startswith("maximum"):
                checks[key] = max(checks.get(key, 0.), value)
            elif key.startswith("minimum"):
                checks[key] = min(checks.get(key, float("inf")), value)
            else:
                checks[key] = checks.get(key, 0)+value
        state, previous = candidate, action.steering_rad
        times.append((index+1)*DT)
        states.append(state.array())
        stations.append(station)
        laterals.append(lateral)
        controls.append(list(asdict(action).values()))
        features.append(row)
        decisions.append({**decision, "steering_projected": bool(log["steering_projected"]),
                          "force_projected": bool(log["force_projected"]), "residual_projected": bool(log["residual_projected"])})
        if station >= laps*track.length_m:
            break
    arrays = {"time_s": np.array(times), "states": np.array(states), "station_m": np.array(stations),
              "lateral_m": np.array(laterals), "controls": np.array(controls).reshape(-1, 4),
              "features": np.array(features).reshape(-1, 8)}
    metrics = lap_metrics(track, arrays, laps)
    complete = bool(len(metrics) == laps and all(r["completed"] for r in metrics))
    passed = bool(complete and physical_gate(checks) and all(r["rmse_m"] <= .5 and r["p95_m"] <= 1
                  and r["maximum_error_m"] <= 2 for r in metrics) and metrics[-1]["rmse_m"]-metrics[0]["rmse_m"] <= .1)
    if not complete and failure is None:
        failure = "R037 elapsed-time budget exceeded"
    # Same map phase at lap boundaries, retaining the continuous physical state.
    seams = []
    if np.all(np.diff(arrays["station_m"]) > 0):
        for lap in range(1, len(metrics)+1):
            if stations[-1] >= lap*track.length_m:
                seam = [float(np.interp(lap*track.length_m, stations, arrays["states"][:, j])) for j in range(6)]
                seams.append({"lap": lap, "state": seam})
    return {"completed": complete, "passed": passed, "abstained": abstained, "failure": failure,
            "rejected_state": rejected, "attempted_final_control": attempted if failure and not abstained else None,
            "laps": metrics, "seam_states": seams, "events": events, "decisions": decisions,
            "checks": checks, "completion_time_s": metrics[-1]["finish_time_s"] if complete else None,
            "progress_m": stations[-1], "kind": kind, "scenario": scenario, "max_step_s": max_step,
            "requested_laps": laps, "state_truth": "CONTINUOUS_SIMULATED; KNOWN_MAP_RECONSTRUCTED; GENERIC_VEHICLE_PRIOR",
            "state_resets": 0, "production_promotion": False}, arrays


def recovery_metrics(disturbed: dict, values: dict, nominal: dict) -> list[dict]:
    """First sustained two-second return to the matched nominal lateral path."""
    times, station = values["time_s"], values["station_m"]
    residual = abs(values["lateral_m"]-np.interp(station, nominal["station_m"], nominal["lateral_m"]))
    rows = []
    for event in disturbed["events"]:
        end = event["end_index"]
        recovery = None
        if end < len(times):
            for index in range(end, min(end+101, len(times)-20)):
                if np.all(residual[index:index+21] <= .15):
                    recovery = float(times[index]-times[end])
                    break
        rows.append({**event, "recovery_s": recovery, "passed": recovery is not None and recovery <= 10})
    return rows


def compare_continuous_paths(first: dict, second: dict) -> dict:
    maximum = min(first["station_m"][-1], second["station_m"][-1])
    grid = np.linspace(0, maximum, 10001)
    def sampled(a, indices):
        return np.column_stack([np.interp(grid, a["station_m"], a["states"][:, j]) for j in indices])
    xy = float(max(np.linalg.norm(sampled(first, (0, 1))-sampled(second, (0, 1)), axis=1)))
    speed = float(np.max(abs(np.linalg.norm(sampled(first, (3, 4)), axis=1)-np.linalg.norm(sampled(second, (3, 4)), axis=1))))
    return {"maximum_position_difference_m": xy, "maximum_speed_difference_mps": speed, "passed": xy <= .5 and speed <= .5}
