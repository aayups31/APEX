"""Independent R030 KKT, DOP853 integration and hierarchical speed-score audit."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from apexsim.examples.longitudinal_dataset import read_json, verify_inventory
from apexsim.examples.longitudinal_study import VERSION, load_inputs


def _independent_path(section, method: str, models: dict) -> np.ndarray:
    t = section.time_s
    initial = float(section.speed_mps[0])
    if method == "constant_speed":
        return np.full(len(t), initial)
    if method == "constant_acceleration":
        times = section.warmup_time_s
        centered = times-np.mean(times)
        slope = float(sum(centered*section.warmup_speed_mps)/sum(centered*centered))
        return initial+slope*(t-t[0])
    if method == "legacy_huber":
        fit = models["legacy"][section.cell]

        def acceleration(v, u, z):
            return -fit["rolling_accel"]+fit["throttle_accel_gain"]*u-fit["drag_accel_coeff"]*v*v
    else:
        if method == "physical_prior":
            closed = .5*1.225*1.05/900
            p, d, extra, rolling = 740000*.92/900, closed*.84, closed*.16, .015*9.81
        else:
            fit = models["candidates"][method]["cells"][section.cell]["parameters"]
            p, d, extra, rolling = (fit[k] for k in ("power_per_mass", "open_drag_per_mass", "extra_closed_drag_per_mass", "rolling_acceleration"))

        def acceleration(v, u, z):
            return p*u/v-(d+extra*(1-z))*v*v-rolling
    result = [initial]
    for i, dt in enumerate(np.diff(t)):
        u, z = float(section.throttle[i]), int(section.drs_open[i])
        solved = solve_ivp(lambda time, state, u=u, z=z: [acceleration(float(state[0]), u, z)],
                           (0., float(dt)), [result[-1]], method="DOP853", rtol=1e-11, atol=1e-12)
        if not solved.success:
            raise ValueError("R030 independent DOP853 integration failed")
        result.append(float(solved.y[0, -1]))
    return np.array(result)


def independent_longitudinal_audit(output: Path) -> dict:
    """Audit convex-fit KKT signs and saved held-out trajectories without RK4/helper metrics."""
    source, sections = load_inputs(output/"development/dataset")
    verify_inventory(output, VERSION+"-study-manifest")
    verify_inventory(output/"development", VERSION+"-development-manifest")
    models = read_json(output/"development/models.json")
    result = read_json(output/"results.json")
    training = [s for s in sections if s.metadata["role"] == "train"]
    test = [s for s in sections if s.metadata["role"] == "test"]
    kkt_maximum, checked_fits = 0., 0
    for kind, candidate in models["candidates"].items():
        for cell, fit in candidate["cells"].items():
            design, actual = [], []
            for section in training:
                if section.cell != cell:
                    continue
                for i in range(len(section.time_s)-1):
                    dt = section.time_s[i+1]-section.time_s[i]
                    v, u, z = section.speed_mps[i], section.throttle[i], section.drs_open[i]
                    row = [dt*u/v, -dt*v*v]
                    if kind == "drs_drag":
                        row.append(-dt*(1-z)*v*v)
                    design.append(row)
                    actual.append(section.speed_mps[i+1]-v+fit["parameters"]["rolling_acceleration"]*dt)
            x, y = np.array(design), np.array(actual)
            coefficients = np.array([fit["parameters"][k] for k in
                                     ("power_per_mass", "open_drag_per_mass", "extra_closed_drag_per_mass")[:x.shape[1]]])
            scales = np.sqrt(np.mean(x*x, axis=0))
            gradient = (x/scales).T@(x@coefficients-y)
            lower, upper = [100., *([0.]*(len(coefficients)-1))], [2000., *([.005]*(len(coefficients)-1))]
            for j, value in enumerate(coefficients):
                if not lower[j]-1e-12 <= value <= upper[j]+1e-12:
                    raise ValueError("R030 independent coefficient bound violation")
                working = value*scales[j]
                if abs(working-lower[j]*scales[j]) <= 1e-7:
                    violation = max(0., -gradient[j])
                elif abs(working-upper[j]*scales[j]) <= 1e-7:
                    violation = max(0., gradient[j])
                else:
                    violation = abs(gradient[j])
                kkt_maximum = max(kkt_maximum, float(violation))
            checked_fits += 1
    if kkt_maximum > 1e-5:
        raise ValueError("R030 independent normalized KKT optimality failed")
    maximum = 0.
    comparisons = 0
    with np.load(output/"predictions.npz", allow_pickle=False) as saved:
        for method, metrics in result["metrics"].items():
            by_driver: dict[str, dict[str, list[float]]] = {}
            for i, section in enumerate(test):
                predicted = _independent_path(section, method, models)
                stored = saved[method+f"__s{i}"]
                if not np.allclose(predicted, stored, rtol=1e-6, atol=1e-7):
                    raise ValueError("R030 independent DOP853/saved speed comparison failed")
                maximum = max(maximum, float(np.max(abs(predicted-stored))))
                error = sum((predicted[1:]-section.speed_mps[1:])**2)/(len(predicted)-1)
                by_driver.setdefault(section.metadata["driver_id"], {}).setdefault(section.metadata["lap_id"], []).append(float(error))
                comparisons += 1
            mse = np.mean([np.mean([np.mean(values) for values in laps.values()]) for laps in by_driver.values()])
            if not np.isclose(mse, metrics["mse_m2ps2"], rtol=1e-6, atol=1e-7):
                raise ValueError("R030 independent hierarchical speed-error audit failed")
    return {"verified": True, "profile": source["profile"], "checked_convex_fits": checked_fits,
            "maximum_normalized_kkt_violation": kkt_maximum, "method_section_comparisons": comparisons,
            "maximum_dop853_difference_mps": maximum, "decision": result["decision"], "promotion": False}
