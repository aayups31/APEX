"""Independent R027/R028 numerical audit, separate from the experiment algorithms.

This deliberately restates the frozen equations and scans scalar candidate
scores. It uses the older checkpoint loader, not the new cached predictor.
"""
from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import numpy as np
import torch
from scipy.stats import spearmanr

from apexsim.examples.forecast_explanation_study import VERSION, _input_metadata, _verify_inventory
from apexsim.examples.tyre_forecast_benchmark import checkpoint_prediction
from apexsim.research.forecast_benchmark import EVENTS, ForecastScaler, ForecastWindows, flat_features
from apexsim.research.tyre_energy import TyreEnergyInputs, estimate_wheel_tyre_energy


def independent_scenarios(history: np.ndarray, minimum: np.ndarray, maximum: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Restate all55 transformations and constraints without the scenario implementation."""
    candidates = list(product([.8, .85, .9, .95, .975, 1., 1.025, 1.05, 1.1, 1.15, 1.2], [-.2, -.1, 0., .1, .2]))

    def valid(x: np.ndarray) -> bool:
        if not np.isfinite(x).all():
            return False
        for row in x:
            v, throttle, brake, ax, ay, steer, omega, geom, dt, lag, *energy = map(float, row)
            if (not 5 <= v <= 105 or not 0 <= throttle <= 1 or brake not in (0., 1.)
                    or abs(ax) > 30 or abs(ay) > 60 or abs(steer) > .6 or abs(omega) > 1.5
                    or geom <= 0 or not .5 <= geom/v <= 1.5 or not 0 < dt <= .5 or not 0 <= lag <= .35):
                return False
            if (not np.isclose(ay, -v*omega, rtol=5e-5, atol=5e-6)
                    or not np.isclose(steer, np.arctan(3.6*omega/geom), rtol=5e-5, atol=5e-6)):
                return False
            front = 900*9.81*.46-900*ax*.32/3.6
            rear = 900*9.81*.54+900*ax*.32/3.6
            lateral = 900*ay*.32/2
            loads = [front/2+lateral*.46/2, front/2-lateral*.46/2,
                     rear/2+lateral*.54/2, rear/2-lateral*.54/2]
            expected = estimate_wheel_tyre_energy(TyreEnergyInputs(v, ax, ay, steer, throttle, brake, dt)).as_array()
            if min(loads) < 50 or not np.allclose(energy, expected, rtol=5e-5, atol=5e-6):
                return False
        return bool(np.all(x >= minimum-(5e-6+5e-5*abs(minimum)))
                    and np.all(x <= maximum+(5e-6+5e-5*abs(maximum))))

    values = np.repeat(history[None], 55, axis=0)
    mask = np.zeros(55, dtype=bool)
    if not valid(history):
        return values, mask
    for i, (a, b) in enumerate(candidates):
        if (a, b) == (1., 0.):
            mask[i] = True
            continue
        x = history.astype(float).copy()
        for row in x:
            row[0], row[3], row[6], row[7] = a*row[0], a*row[3], a*row[6], a*row[7]
            row[4], row[1] = a*a*row[4], row[1]+b
            if 0 <= row[1] <= 1:
                row[10:] = estimate_wheel_tyre_energy(TyreEnergyInputs(
                    float(row[0]), float(row[3]), float(row[4]), float(row[5]),
                    float(row[1]), float(row[2]), float(row[8]),
                )).as_array()
        values[i] = x.astype(np.float32)
        mask[i] = valid(values[i])
        if not np.array_equal(values[i, :, [2, 5, 8, 9]], history[:, [2, 5, 8, 9]].T):
            raise ValueError("Independent scenario immutable-field audit failed")
    return values, mask


def _winner(raw: np.ndarray, baseline: np.ndarray, valid: np.ndarray) -> int | None:
    parameters = list(product([.8, .85, .9, .95, .975, 1., 1.025, 1.05, 1.1, 1.15, 1.2], [-.2, -.1, 0., .1, .2]))
    choices = []
    for i, (factor, offset) in enumerate(parameters):
        if not valid[i]:
            continue
        passed = True
        for seed in range(len(baseline)):
            initial = float(np.mean(np.maximum(baseline[seed], 0)))
            candidate = float(np.mean(np.maximum(raw[seed, i], 0)))
            if candidate > initial-max(.1*initial, .01):
                passed = False
        if passed:
            cost = round(abs(factor-1)/.2+abs(offset)/.2, 12)
            choices.append((cost, factor, offset, i))
    return min(choices)[-1] if choices else None


def independent_explanation_audit(output: Path) -> dict:
    """Check source feasibility, every CF winner, local gates and selected reloads."""
    def read(name: str):
        return json.loads((output/name).read_text(encoding="utf-8"))
    cohort = read("cohort.json")
    ref, _, _, _, _, _ = _input_metadata(output/"reference", output/"evaluation", cohort["profile"], payloads=False)
    _verify_inventory(output, VERSION+"-manifest")
    stored = read("results.json")
    metadata = read("reference/window_metadata.json")
    train_rows = [i for i, m in enumerate(metadata) if m["event_id"] in EVENTS[:2]]
    with np.load(output/"reference/windows.npz", allow_pickle=False) as data:
        train = data["dynamic"][train_rows]
    minimum, maximum = train.min(axis=(0, 1)).astype(float), train.max(axis=(0, 1)).astype(float)
    with np.load(output/"evaluation/windows.npz", allow_pickle=False) as data:
        indices = [c["origin_index"] for c in cohort["cases"]]
        x, static = data["dynamic"][indices], data["static"][indices]
    independent = [independent_scenarios(history, minimum, maximum) for history in x]
    records = {r["name"]: r for r in ref["records"]}
    scaler_payload = read("reference/scaler.json")
    scaler = ForecastScaler(*(np.array(scaler_payload[k]) for k in ("input_mean", "input_std", "target_mean", "target_std")))
    cf_successes, reliable, reloads, max_difference = 0, 0, 0, 0.
    primary_raw, primary_base = [], []
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        for name, method in stored["models"].items():
            with np.load(output/(name+".npz"), allow_pickle=False) as raw:
                baseline, predictions = raw["baseline_raw"], raw["counterfactual_raw"]
                if name in stored["primary_frozen_seeds"]:
                    primary_raw.append(predictions)
                    primary_base.append(baseline)
                chosen_x, chosen_static, expected = [], [], []
                for i, case in enumerate(method["cases"]):
                    histories, valid = independent[i]
                    winner = _winner(predictions[i:i+1], baseline[i:i+1], valid)
                    if case["counterfactual"]["selected_index"] != winner:
                        raise ValueError("Independent source-feasibility/counterfactual-minimum audit failed")
                    if winner is not None:
                        cf_successes += 1
                        chosen_x.append(histories[winner])
                        chosen_static.append(static[i])
                        expected.append(predictions[i, winner])
                for slot, i in enumerate(raw["temporal_origin_indices"]):
                    base = np.maximum(raw["temporal_base_raw"][slot, 0], 0)
                    perturb = np.maximum(raw["temporal_perturb_raw"][slot], 0)
                    score = abs(perturb[:4]-base).mean(axis=0)
                    audit = abs(perturb[4:]-base).mean(axis=0)
                    rank = np.argsort(-score.mean(axis=(1, 2)), kind="stable")
                    a, b = score.mean(axis=(1, 2)), audit.mean(axis=(1, 2))
                    correlation = float(spearmanr(a, b).statistic) if np.ptp(a) and np.ptp(b) else None
                    joint = np.maximum(raw["temporal_joint_raw"][slot], 0)
                    effects = abs(joint-base).mean(axis=(2, 3))
                    passed = (score.max() > 1e-6 and correlation is not None and correlation >= .5
                              and b[rank[:3]].mean() > b.mean()+1e-6 and effects[:, 1].mean() >= effects[:, 3::2].mean())
                    explanation = method["cases"][int(i)]["explanation"]
                    if (explanation["ranking"] != rank.tolist()
                            or (explanation["status"] == "RELIABLE_MODEL_DIAGNOSTIC") != passed):
                        raise ValueError("Independent temporal faithfulness audit failed")
                    reliable += int(passed)
                if chosen_x and name in records:
                    data = ForecastWindows(np.array(chosen_x), np.array(chosen_static), np.zeros((len(chosen_x), 3, 4)),
                                           [{} for _ in chosen_x], ref["vocabulary"])
                    record = records[name]
                    checkpoint = output/"reference"/record["checkpoint"]
                    if record["kind"] in ("linear", "ridge"):
                        # Independent high-precision coefficient evaluation; old FP32
                        # SGEMM is retained unchanged in historical R025/R026 code.
                        with np.load(checkpoint, allow_pickle=False) as weights:
                            features = flat_features(data, scaler).astype(float)
                            loaded = scaler.inverse((features @ weights["coef"].astype(float).T+
                                                     weights["intercept"].astype(float)).reshape(-1, 3, 4))
                    elif record["kind"] in ("gru", "lstm", "tft"):
                        parts = []
                        for start in range(0, len(chosen_x), 32):
                            rows = np.arange(start, min(start+32, len(chosen_x)))
                            count = len(rows)
                            rows = np.pad(rows, (0, 32-count), mode="edge")
                            chunk = ForecastWindows(data.dynamic[rows], data.static[rows], np.zeros((32, 3, 4)),
                                                    [{} for _ in range(32)], ref["vocabulary"])
                            parts.append(checkpoint_prediction(checkpoint, record, chunk, scaler)[:count])
                        loaded = np.concatenate(parts)
                    else:
                        loaded = checkpoint_prediction(checkpoint, record, data, scaler)
                    if not np.allclose(loaded, expected, rtol=1e-6, atol=1e-7):
                        raise ValueError("Independent selected-scenario checkpoint reload failed")
                    max_difference = max(max_difference, float(np.max(abs(loaded-expected))))
                    reloads += len(chosen_x)
        primary_raw, primary_base = np.array(primary_raw), np.array(primary_base)
        for i, case in enumerate(stored["robust_primary_counterfactuals"]):
            winner = _winner(primary_raw[:, i], primary_base[:, i], independent[i][1])
            if case["selected_index"] != winner:
                raise ValueError("Independent joint-seed counterfactual audit failed")
    finally:
        torch.set_num_threads(old_threads)
    return {"verified": True, "audit": "INDEPENDENT_EQUATIONS_SCALAR_CATALOGUE_OLDER_NATIVE_LOADER_AND_FP64_LINEAR_COEFFICIENTS",
            "origins": len(x), "methods": len(stored["models"]), "valid_counterfactual_successes": cf_successes,
            "reliable_model_diagnostics": reliable, "selected_learned_scenario_reloads": reloads,
            "maximum_selected_reload_difference_kj": max_difference, "promotion": False}
