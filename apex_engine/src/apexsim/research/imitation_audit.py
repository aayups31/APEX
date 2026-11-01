"""Independent scalar observations/labels, QR ridge and held-action physics for R036."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from scipy.linalg import lstsq

from apexsim.research.aero_audit import independent_loaded_path
from apexsim.research.bicycle import BicycleControl
from apexsim.research.driver_audit import compare_path
from apexsim.research.evidence import compare_numeric
from apexsim.research.transparent_driver import AERO, CAR


def scalar_observation(state, track, station, lateral, previous, lead):
    """Independent scalar linear map interpolation and local error equations."""
    def interpolate(values, distance):
        phase = (distance % track.length_m)/(track.length_m/len(track.xy))
        index = math.floor(phase)
        f = phase-index
        return values[index]*(1-f)+values[(index+1) % len(values)]*f

    speed = math.hypot(state[3], state[4])
    tangent = interpolate(track.tangent, station)
    heading = math.atan2(tangent[1], tangent[0])
    curvature = float(interpolate(track.curvature, station))
    preview = float(interpolate(track.curvature, station+lead*speed))
    beta = math.atan2(state[4], state[3])
    error = heading-state[2]-beta
    return [speed*speed/3600, 50*curvature, 50*preview, math.atan2(math.sin(error), math.cos(error)),
            math.atan(.8*lateral/(speed+5)), speed*curvature-state[5], beta, previous]


def scalar_label(row):
    length = CAR.front_distance_m+CAR.rear_distance_m
    k = CAR.mass_kg/length*(CAR.rear_distance_m/CAR.front_stiffness_nprad-CAR.front_distance_m/CAR.rear_stiffness_nprad)
    return (length+k*3600*row[0])*(row[2]-row[1])/50


def independent_fit(x, y, weights, model):
    weights = weights/sum(weights)
    means = np.array([sum(w*v for w, v in zip(weights, x[:, i], strict=True)) for i in range(8)])
    scales = np.array([math.sqrt(sum(w*(v-m)**2 for w, v in zip(weights, x[:, i], strict=True))) for i, m in enumerate(means)])
    scales[scales < 1e-12] = 1.
    compare_numeric(means.tolist(), model["mean"], "independent training means", atol=1e-10, rtol=1e-8)
    compare_numeric(scales.tolist(), model["scale"], "independent training scales", atol=1e-10, rtol=1e-8)
    normalized = (x-means)/scales
    columns = [np.ones(len(x)), *normalized.T]
    if model["degree"] == 2:
        columns += [normalized[:, i]*normalized[:, j] for i in range(8) for j in range(i, 8)]
    matrix = np.column_stack(columns)
    penalty = np.diag([0., *([math.sqrt(model["alpha"])]*(matrix.shape[1]-1))])
    augmented = np.concatenate([matrix*np.sqrt(weights[:, None]), penalty])
    target = np.r_[y*np.sqrt(weights), np.zeros(matrix.shape[1])]
    coefficients = lstsq(augmented, target, lapack_driver="gelsy")[0]  # pivoted QR, primary is NumPy SVD
    difference = float(np.max(abs(matrix@coefficients-matrix@np.asarray(model["coefficients"]))))
    if difference > 1e-7:
        raise ValueError("R036 independent QR ridge prediction disagreement")
    mse = float(weights@((matrix@coefficients-y)**2))
    compare_numeric(mse, model["training_weighted_mse_rad2"], "independent ridge loss", atol=1e-12, rtol=1e-6)
    return difference


def audit_development(root: Path, summary: dict, result: dict, header: dict, maps: dict, *, replay_dynamics=True, progress=None):
    from apexsim.examples.imitation_study import execute, load_dataset, training_arrays, validation_score
    from apexsim.research.imitation_driver import ALPHAS, LEADS

    _, _, _, pace = load_dataset(root/"dataset")
    catalog = {r["lap_id"]: r for r in header["cases"]}
    trial_lookup = {r["case_id"]: r for r in result["trials"]}
    expected = set()
    actors = [*("expert"+str(lead) for lead in LEADS), *(f"bc_d{d}_a{a}" for d in (1, 2) for a in ALPHAS), "aggregated"]
    for case in header["cases"]:
        if case["role"] == "validation":
            expected.update(actor+"__"+case["lap_id"]+"__nominal__0.02" for actor in actors)
        if case["role"] == "train":
            expected.update(actor+"__"+case["lap_id"]+"__"+scenario+"__0.02" for actor in ("expert_train", "collection_learner") for scenario in ("nominal", "disturbed"))
    if len(trial_lookup) != len(result["trials"]) or set(trial_lookup) != expected:
        raise ValueError("R036 development trial catalog is incomplete or changed")
    model_keys = {f"bc_d{d}_a{a}" for d in (1, 2) for a in ALPHAS} | {"aggregated"}
    if set(result["models"]) != model_keys:
        raise ValueError("R036 candidate model catalog changed")
    for name, model in result["models"].items():
        expected_name = f"bc_d{model['degree']}_a{model['alpha']}"
        if name != "aggregated" and name != expected_name:
            raise ValueError("R036 candidate class/penalty binding changed")
    episodes, all_arrays = [], set()
    maximum_feature_error, maximum_dynamic_difference = 0., 0.
    with np.load(root/"rollouts.npz", allow_pickle=False) as arrays:
        for trial in result["trials"]:
            key = trial["case_id"]
            saved = {k: arrays[key+"__"+k] for k in ("time_s", "states", "station_m", "lateral_m", "controls", "features", "diagnostics")}
            all_arrays.update(key+"__"+k for k in saved)
            case = catalog[trial["lap_id"]]
            if trial["event_id"] != case["event_id"] or trial["role"] != case["role"] or trial["driver_id"] != case["driver_id"] or trial["role"] == "test":
                raise ValueError("R036 leakage or condition identity in development")
            previous = np.r_[0., saved["controls"][:-1, 0]]
            rebuilt = np.array([scalar_observation(state, maps[case["track_id"]], station, lateral, old, trial["lead_s"])
                                for state, station, lateral, old in zip(saved["states"][:-1], saved["station_m"][:-1], saved["lateral_m"][:-1], previous, strict=True)])
            difference = float(np.max(abs(rebuilt-saved["features"])))
            if difference > 1e-10:
                raise ValueError("R036 independent causal feature disagreement")
            maximum_feature_error = max(maximum_feature_error, difference)
            if trial["actor"] in ("expert_train", "collection_learner"):
                episodes.append((trial, saved))
            if replay_dynamics:
                actor = trial["actor"]
                checkpoint = result["best_bc"] if actor == "collection_learner" else actor
                model = result["models"].get(checkpoint)
                regenerated, values = execute(root/"dataset", header, maps, pace, case, actor, trial["lead_s"], model,
                                              disturbed=trial["scenario"] == "disturbed", allowed_roles=(case["role"],), progress=progress)
                if actor in ("expert_train", "collection_learner"):
                    regenerated["collection_round"] = 0 if actor == "expert_train" else 1
                compare_numeric(regenerated, trial, "development physical replay")
                for name, value in values.items():
                    if saved[name].shape != value.shape or not np.allclose(saved[name], value, atol=1e-8, rtol=1e-7):
                        raise ValueError("R036 development trajectory replay mismatch: "+key+"/"+name)
                    maximum_dynamic_difference = max(maximum_dynamic_difference, float(np.max(abs(saved[name]-value))))
        if set(arrays.files) != all_arrays:
            raise ValueError("R036 unbound development trajectory arrays")
    base = [(r, a) for r, a in episodes if r["collection_round"] == 0]
    base_data, base_ledger = training_arrays(base)
    aggregate, ledger = training_arrays(episodes)
    compare_numeric(base_ledger, result["base_episode_ledger"])
    compare_numeric(ledger, result["episode_ledger"])
    for data in (base_data, aggregate):
        independent_labels = np.array([scalar_label(row) for row in data["x"]])
        if not np.allclose(independent_labels, data["y"], atol=1e-12, rtol=1e-10):
            raise ValueError("R036 independent expert label disagreement")
    with np.load(root/"training.npz", allow_pickle=False) as stored:
        expected_keys = {prefix+"_"+key for prefix, data in (("base", base_data), ("aggregate", aggregate)) for key in data}
        if set(stored.files) != expected_keys:
            raise ValueError("R036 training array catalog changed")
        for prefix, data in (("base", base_data), ("aggregate", aggregate)):
            for key, value in data.items():
                if stored[prefix+"_"+key].shape != value.shape or not np.allclose(stored[prefix+"_"+key], value, atol=1e-12, rtol=1e-10):
                    raise ValueError("R036 training data/weight binding mismatch")
    maximum_fit = 0.
    for name, model in result["models"].items():
        data = aggregate if name == "aggregated" else base_data
        maximum_fit = max(maximum_fit, independent_fit(data["x"], data["y"], data["weights"], model))
    # Selection is reconstructed from the complete validation catalog, never trusted as metadata.
    expert_scores = {str(lead): validation_score([r for r in result["trials"] if r["actor"] == "expert"+str(lead)]) for lead in LEADS}
    compare_numeric(expert_scores, result["expert_validation_scores"])
    lead = min((v for v in LEADS if expert_scores[str(v)] is not None), key=lambda v: (expert_scores[str(v)], v))
    if lead != result["selected_lead_s"] or any(r["lead_s"] != lead for r in result["trials"] if r["actor"] not in {"expert"+str(v) for v in LEADS}):
        raise ValueError("R036 expert choice or collection preview changed")
    scores = {name: validation_score([r for r in result["trials"] if r["actor"] == name]) for name in result["models"]}
    compare_numeric(scores, result["validation_scores"])
    bc = [n for n, v in scores.items() if n != "aggregated" and v is not None]
    best = min(bc, key=lambda n: (scores[n], result["models"][n]["parameters"], -result["models"][n]["alpha"]))
    linear = [n for n in bc if result["models"][n]["degree"] == 1]
    best_linear = min(linear, key=lambda n: (scores[n], -result["models"][n]["alpha"])) if linear else None
    selected = "aggregated" if scores["aggregated"] is not None and scores["aggregated"] < scores[best] else best
    if (result["best_bc"], result["best_linear"], result["selected"]) != (best, best_linear, selected):
        raise ValueError("R036 false frozen model choice")
    return {"verified": True, "summary_sha256": summary["content_sha256"], "profile": header["profile"], "test_outcomes_used": False,
            "replay_dynamics": replay_dynamics, "trials_checked": len(result["trials"]), "training_rows": len(aggregate["y"]),
            "maximum_independent_feature_difference": maximum_feature_error, "maximum_independent_ridge_prediction_difference_rad": maximum_fit,
            "maximum_physical_replay_difference": maximum_dynamic_difference, "selected": selected, "selected_lead_s": lead,
            "task_closure_eligible": False}


def audit_final_paths(result: dict, arrays: dict, progress=None):
    full, checks = False, []
    for case in result["cases"]:
        if case["actor"] != "final" or case["scenario"] != "nominal" or case["max_step_s"] != .02:
            continue
        key = case["case_id"]
        states, times, controls = (arrays[key+"__"+k] for k in ("states", "time_s", "controls"))
        commands = [BicycleControl(*row) for row in controls]
        if not full and case["completed"]:
            if progress:
                progress("Independent complete final-policy lap: "+key)
            other = independent_loaded_path(states[0], times, commands, CAR, AERO)
            checks.append({"case_id": key, "scope": "COMPLETE_LAP", "intervals": len(commands), **compare_path(states, other)})
            full = True
        for index in sorted(set(int(v) for v in np.linspace(0, len(commands)-1, min(8, len(commands))))):
            other = independent_loaded_path(states[index], times[index:index+2]-times[index], commands[index:index+1], CAR, AERO)
            checks.append({"case_id": key, "scope": "REPRESENTATIVE_INTERVAL", "interval_index": index, **compare_path(states[index:index+2], other)})
    return {"passed": bool(full and checks and all(r["passed"] for r in checks)), "complete_laps": int(full), "checks": checks,
            "primary_rhs_reused": False, "method": "SCALAR_BISECTION_DOP853"}
