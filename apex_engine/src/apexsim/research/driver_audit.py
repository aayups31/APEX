"""R035 independent held-action six-state replay, using R032 scalar bisection."""
from __future__ import annotations

import numpy as np

from apexsim.research.aero_audit import independent_loaded_path
from apexsim.research.bicycle import BicycleControl
from apexsim.research.transparent_driver import AERO, CAR


def compare_path(primary, independent):
    position = float(np.max(np.linalg.norm(primary[:, :2]-independent[:, :2], axis=1)))
    velocity = float(np.max(abs(primary[:, 3:5]-independent[:, 3:5])))
    return {"passed": position <= .05 and velocity <= .01, "maximum_position_difference_m": position,
            "maximum_body_velocity_difference_mps": velocity,
            "maximum_heading_difference_rad": float(np.max(abs(primary[:, 2]-independent[:, 2]))),
            "maximum_yaw_rate_difference_radps": float(np.max(abs(primary[:, 5]-independent[:, 5])))}


def audit_arrays(result: dict, arrays: dict, progress=None):
    full_done, checks = False, []
    for case in result["cases"]:
        if case["mode"] != "feedback" or case["max_step_s"] != .02 or case["role"] != "test":
            continue
        key = case["case_id"]
        states, times, controls = (arrays[key+"__"+k] for k in ("states", "time_s", "controls"))
        commands = [BicycleControl(*row) for row in controls]
        if case["completed"] and not full_done:
            if progress:
                progress("Independent full-lap bisection/DOP853 replay: "+key)
            independent = independent_loaded_path(states[0], times, commands, CAR, AERO)
            checks.append({"case_id": key, "scope": "COMPLETE_LAP", "intervals": len(commands), **compare_path(states, independent)})
            full_done = True
        for i in sorted(set(int(v) for v in np.linspace(0, len(commands)-1, min(8, len(commands))))):
            independent = independent_loaded_path(states[i], times[i:i+2]-times[i], commands[i:i+1], CAR, AERO)
            checks.append({"case_id": key, "scope": "REPRESENTATIVE_INTERVAL", "interval_index": i, **compare_path(states[i:i+2], independent)})
    return {"passed": bool(full_done and checks and all(r["passed"] for r in checks)), "complete_laps_checked": int(full_done),
            "checks": checks, "primary_rhs_reused": False, "method": "SCALAR_TYRE_LOAD_BISECTION_DOP853"}
