"""Independent held-action physics across complete horizons, seams and recovery."""
from __future__ import annotations

import numpy as np

from apexsim.research.aero_audit import independent_loaded_path
from apexsim.research.bicycle import BicycleControl
from apexsim.research.driver_audit import compare_path
from apexsim.research.transparent_driver import AERO, CAR


def audit_continuous(cases: list[dict], arrays: dict, *, actor: str, full_scenario: str, progress=None) -> dict:
    checks, complete = [], False
    for case in cases:
        if case["actor"] != actor or case["max_step_s"] != .02:
            continue
        key = case["case_id"]
        states, times, controls, station = (arrays[key+"__"+k] for k in ("states", "time_s", "controls", "station_m"))
        commands = [BicycleControl(*row) for row in controls]
        if not commands:
            continue
        if not complete and case["scenario"] == full_scenario and case["completed"]:
            if progress:
                progress("Independent full continuous horizon: "+key)
            other = independent_loaded_path(states[0], times, commands, CAR, AERO)
            checks.append({"case_id": key, "scope": "COMPLETE_CONTINUOUS_HORIZON", "intervals": len(commands), **compare_path(states, other)})
            complete = True
        indices = {int(i) for i in np.linspace(0, len(commands)-1, min(8, len(commands)))}
        for lap in range(1, case["requested_laps"]):
            index = int(np.searchsorted(station, lap*case["track_length_m"]))
            indices.update(i for i in (index-1, index) if 0 <= i < len(commands))
        for event in case["events"]:
            indices.update(i for i in (event["start_index"], event["end_index"]) if i < len(commands))
        for index in sorted(indices):
            other = independent_loaded_path(states[index], times[index:index+2]-times[index], commands[index:index+1], CAR, AERO)
            checks.append({"case_id": key, "scope": "SEAM_PULSE_OR_REPRESENTATIVE_INTERVAL", "interval_index": index,
                           **compare_path(states[index:index+2], other)})
    return {"passed": bool(complete and checks and all(r["passed"] for r in checks)), "complete_horizons": int(complete),
            "checks": checks, "method": "INDEPENDENT_SCALAR_LOAD_BISECTION_DOP853", "primary_rhs_reused": False}
