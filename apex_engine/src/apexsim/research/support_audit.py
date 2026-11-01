"""Independent sorted-array quantiles and scalar box scores for R038."""
from __future__ import annotations

import math

import numpy as np

from apexsim.research.aero_audit import independent_loaded_path
from apexsim.research.bicycle import BicycleControl
from apexsim.research.driver_audit import compare_path
from apexsim.research.transparent_driver import AERO, CAR


def quantile(values, probability):
    values = sorted(float(v) for v in values)
    point = probability*(len(values)-1)
    left = math.floor(point)
    fraction = point-left
    return values[left]*(1-fraction)+values[min(left+1, len(values)-1)]*fraction


def audit_detector(training: np.ndarray, validation: np.ndarray, model: dict) -> dict:
    floors = [.05, .02, .02, .005, .005, .02, .01, .01]
    pairs = [(quantile(training[:, j], .005), quantile(training[:, j], .995)) for j in range(8)]
    centers = [(a+b)/2 for a, b in pairs]
    widths = [max((b-a)/2, floor) for (a, b), floor in zip(pairs, floors, strict=True)]
    scores = [max(abs((float(row[j])-centers[j])/widths[j]) for j in range(8)) for row in validation]
    cutoff = max(1.25, 1.1*quantile(scores, .995))
    independent = np.r_[centers, widths, cutoff]
    primary = np.r_[model["center"], model["half_range"], model["cutoff"]]
    difference = float(np.max(abs(independent-primary)))
    if not np.allclose(independent, primary, atol=1e-12, rtol=1e-10):
        raise ValueError("R038 independent detector fit disagreement")
    return {"verified": True, "method": "INDEPENDENT_SORTED_LINEAR_QUANTILES_SCALAR_BOX", "maximum_parameter_difference": difference,
            "validation_exceedance_fraction": sum(v > cutoff for v in scores)/len(scores)}


def audit_switches(cases: list[dict], arrays: dict, progress=None) -> dict:
    """Independently integrate immediately before AND after every guarded handover."""
    checks, switches = [], 0
    for case in cases:
        if case["actor"] != "guarded" or case["max_step_s"] != .02:
            continue
        key = case["case_id"]
        states, times, actions = (arrays[key+"__"+k] for k in ("states", "time_s", "controls"))
        decisions = case["decisions"][:len(actions)]
        changed = [i for i in range(1, len(decisions)) if decisions[i]["mode"] != decisions[i-1]["mode"]]
        switches += len(changed)
        indices = {i for change in changed for i in (change-1, change)}
        if indices and progress:
            progress("Independent before/after switch intervals: "+key)
        for index in sorted(indices):
            command = BicycleControl(*actions[index])
            other = independent_loaded_path(states[index], times[index:index+2]-times[index], [command], CAR, AERO)
            checks.append({"case_id": key, "interval_index": index, **compare_path(states[index:index+2], other)})
    return {"passed": bool(checks and all(r["passed"] for r in checks)), "switches_checked": switches,
            "intervals_checked": len(checks), "checks": checks, "method": "INDEPENDENT_SCALAR_LOAD_BISECTION_DOP853",
            "scope": "IMMEDIATELY_BEFORE_AND_AFTER_EVERY_GUARDED_COARSE_STEP_HANDOVER", "primary_rhs_reused": False}
