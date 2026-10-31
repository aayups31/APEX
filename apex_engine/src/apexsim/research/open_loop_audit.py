"""Independent scalar-law/DOP853 and scalar error audit for R034 saved paths."""
from __future__ import annotations

import math
from itertools import pairwise
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from apexsim.research.evidence import compare_numeric


def scalar_path(section, horizon, method, models):
    native = section.time_s-section.time_s[0]
    times = [0.]+[float(t) for t in native if 0 < t < horizon-1e-9]+[horizon]
    value, path = float(section.speed_mps[0]), [float(section.speed_mps[0])]
    wt, wv = section.warmup_time_s, section.warmup_speed_mps
    mean_t = sum(wt)/5
    slope = sum((t-mean_t)*v for t, v in zip(wt, wv, strict=True))/sum((t-mean_t)**2 for t in wt)
    for start, end in pairwise(times):
        parent = max(i for i, t in enumerate(native) if t <= start+1e-10)
        u, z = float(section.throttle[parent]), int(section.drs_open[parent])
        if method == "constant_speed":
            value = path[0]
        elif method == "constant_acceleration":
            value = path[0]+slope*end
        else:
            p, power, drag, extra, rolling = {}, 0., 0., 0., 0.
            if method == "shared_drag":
                p = models["candidates"]["shared_drag"]["cells"][section.cell]["parameters"]
                power, drag, extra, rolling = (p[k] for k in ("power_per_mass", "open_drag_per_mass", "extra_closed_drag_per_mass", "rolling_acceleration"))
            elif method == "physical_prior":
                power, drag, extra, rolling = 740000*.92/900, .5*1.225*1.05*.84/900, .5*1.225*1.05*.16/900, .015*9.81
            else:
                p = models["legacy"][section.cell]

            def rhs(_, y, p=p, power=power, drag=drag, extra=extra, rolling=rolling, u=u, z=z):
                v = y[0]
                if method == "legacy_huber":
                    return [-p["rolling_accel"]+p["throttle_accel_gain"]*u-p["drag_accel_coeff"]*v*v]
                return [power*u/v-(drag+extra*(1-z))*v*v-rolling]

            solution = solve_ivp(rhs, (start, end), [value], method="DOP853", rtol=1e-12, atol=1e-12, max_step=.05)
            if not solution.success:
                raise ValueError("R034 independent integration failed")
            value = float(solution.y[0, -1])
        path.append(value)
    return np.array(times), np.array(path)


def scalar_metrics(times, targets, predictions):
    errors = [float(p-y) for p, y in zip(predictions[1:], targets[1:], strict=True)]
    integral = sum(float((predictions[i-1]-targets[i-1]+predictions[i]-targets[i])*(times[i]-times[i-1])/2) for i in range(1, len(times)))
    return {"mse_m2ps2": sum(e*e for e in errors)/len(errors), "mae_mps": sum(abs(e) for e in errors)/len(errors),
            "absolute_endpoint_error_mps": abs(errors[-1]), "absolute_speed_integral_error_m": abs(integral),
            "endpoint_error_mps": errors[-1], "speed_integral_error_m": integral, "future_nodes": len(errors),
            "raw_nonphysical_nodes": sum(float(p) <= 0 or float(p) > 120 for p in predictions)}


def audit_open_loop_study(root: Path) -> dict:
    from apexsim.examples.open_loop_study import inputs, load_study

    summary, result = load_study(root)
    _, sections, models = inputs(root)
    by_id = {s.metadata["section_id"]: s for s in sections}
    maximum = 0.
    with np.load(root/"predictions.npz", allow_pickle=False) as arrays:
        for record in result["records"]:
            section = by_id[record["section_id"]]
            key = record["section_id"]+"_h"+str(record["horizon_s"])
            t, path = scalar_path(section, record["horizon_s"], record["method"], models)
            saved = arrays[key+"_"+record["method"]]
            difference = float(np.max(abs(path-saved)))
            if difference > 1e-6 or not np.allclose(t, arrays[key+"_time"], atol=1e-10, rtol=0):
                raise ValueError("R034 independent path disagreement")
            maximum = max(maximum, difference)
            target = np.interp(t, section.time_s-section.time_s[0], section.speed_mps)
            compare_numeric(arrays[key+"_target"].tolist(), target.tolist())
            for name, value in scalar_metrics(t, target, path).items():
                compare_numeric(record[name], value, name, atol=1e-7, rtol=1e-6)
    # Independently reconstruct the hierarchy from scalar records, not the primary score helper.
    for role, horizons in result["scores"].items():
        for horizon, methods in horizons.items():
            for method, scores in methods.items():
                rows = [r for r in result["records"] if r["role"] == role and r["horizon_s"] == float(horizon) and r["method"] == method]
                if not rows:
                    if scores is not None:
                        raise ValueError("R034 invented unsupported score")
                    continue
                for field in ("mse_m2ps2", "mae_mps", "absolute_endpoint_error_mps", "absolute_speed_integral_error_m"):
                    events = []
                    for event in sorted({r["event_id"] for r in rows}):
                        drivers = []
                        for driver in sorted({r["driver_id"] for r in rows if r["event_id"] == event}):
                            selected = [r for r in rows if r["event_id"] == event and r["driver_id"] == driver]
                            lap_means = []
                            for lap in sorted({r["lap_id"] for r in selected}):
                                values = [r[field] for r in selected if r["lap_id"] == lap]
                                lap_means.append(sum(values)/len(values))
                            drivers.append(sum(lap_means)/len(lap_means))
                        events.append(sum(drivers)/len(drivers))
                    compare_numeric(scores[field], sum(events)/len(events), field, atol=1e-7, rtol=1e-6)
                compare_numeric(scores["rmse_mps"], math.sqrt(scores["mse_m2ps2"]))
    return {"verified": True, "summary_sha256": summary["content_sha256"], "paths_checked": len(result["records"]),
            "maximum_independent_speed_difference_mps": maximum, "task_closure_eligible": result["task_closure_eligible"]}
