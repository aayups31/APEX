"""Fixed R041 v11 trajectory experiment; no tuning, acquisition or promotion."""
from __future__ import annotations

import argparse
from pathlib import Path
from statistics import mean

from apexsim.provenance import write_manifest
from apexsim.research.compound_readiness import LABELS, assess_panel
from apexsim.research.compound_trajectory import fit_trajectory, predict_trajectory
from apexsim.research.evidence import check_seal, read_json, seal
from compound_bounded_common import environment
from confirm_compound_multiseason import BASE, canonical_file_sha

RECIPES = [("pace_boost", "pace", "boost"), ("history_boost", "history", "boost"),
           ("full_boost", "full", "boost"), ("full_ridge", "full", "ridge")]
PRIMARY = "full_boost"


def export_model(model: dict) -> dict:
    """Plain numerical checkpoint; no pickle and no estimator loading required."""
    result = {k: v for k, v in model.items() if k not in ("estimator", "scaler")}
    result.update(mean=model["scaler"].mean_.tolist(), scale=model["scaler"].scale_.tolist())
    estimator = model["estimator"]
    if model["family"] == "ridge":
        result.update(coefficients=estimator.coef_.tolist(), intercept=float(estimator.intercept_))
    else:
        trees = []
        for stage in estimator.estimators_:
            tree = stage[0].tree_
            trees.append({"left": tree.children_left.tolist(), "right": tree.children_right.tolist(),
                          "feature": tree.feature.tolist(), "threshold": tree.threshold.tolist(),
                          "value": tree.value[:, 0, 0].tolist()})
        result.update(initial=float(estimator.init_.constant_[0, 0]), learning_rate=estimator.learning_rate, trees=trees)
    return result


def metrics(rows: list[dict]) -> dict:
    result = {}
    for _, label in LABELS:
        errors = [abs(r["predicted_s"]-r[label]) for r in rows]
        ordered = sorted(errors)
        result[label] = {"mae_s": mean(errors), "rmse_s": mean(v*v for v in errors)**.5,
                         "p90_absolute_error_s": ordered[min(len(ordered)-1, int(.9*len(ordered)))],
                         "maximum_absolute_error_s": max(errors)}
    return result


def hashes() -> dict:
    paths = [Path(__file__), Path(__file__).with_name("prepare_compound_trajectory.py"),
             BASE/"research/protocols/COMPOUND_TRAJECTORY_V11.md"]
    paths += [BASE/"apex_engine/src/apexsim/research"/name for name in (
        "compound_trajectory.py", "compound_adaptive.py", "compound_conditioned.py", "compound_bounded.py", "compound_readiness.py")]
    return {p.relative_to(BASE).as_posix(): canonical_file_sha(p) for p in paths}


def compare(data: dict, *, recipes: list | None = None) -> dict:
    """Every fold excludes the complete outer event; fixed primary is immutable."""
    check_seal(data)
    rows = data["cases"]
    events = sorted({str(r["session"]) for r in rows})
    if len(events) < 4:
        raise ValueError("Trajectory evaluation requires at least four supported events")
    recipes = RECIPES if recipes is None else recipes
    reports, mutations = {}, 0
    for name, group, family in recipes:
        predictions, models = {}, []
        for event in events:
            training = [r for r in rows if str(r["session"]) != event]
            model = fit_trajectory(training, group=group, family=family)
            models.append({"outer_event": event, "model": export_model(model)})
            for i, row in enumerate(rows):
                if str(row["session"]) != event:
                    continue
                forecast = predict_trajectory(model, row)
                corrupted = {**row, "actual_s": 999., "pairwise_actual_s": -999., "current_target_s": [999.]*3}
                if predict_trajectory(model, corrupted) != forecast:
                    raise ValueError("Trajectory prediction reads a future target")
                mutations += 1
                predictions[i] = forecast
        forecast_rows = [{**r, **predictions[i]} for i, r in enumerate(rows)]
        readiness = assess_panel(forecast_rows, sorted(data["sources"]))
        supported = [e for e in readiness["events"] if e["cases"]]
        reports[name] = {"group": group, "family": family, "models": models,
                         "predictions": [{"case_index": i, **predictions[i]} for i in range(len(rows))],
                         "readiness": readiness, "metrics": metrics(forecast_rows),
                         "macro_mae_s": mean(l["mae_s"] for e in supported for l in e["labels"]),
                         "bound_hits": sum(p["correction_bounded"] for p in predictions.values()),
                         "fallback_cases": sum(p["fallback"] for p in predictions.values()),
                         "by_current_compound": {c: metrics([r for r in forecast_rows if r["compounds"][1] == c])
                                                 for c in sorted({r["compounds"][1] for r in rows})}}
    primary = reports.get(PRIMARY)
    qualified = primary is not None and primary["readiness"]["development_qualified"]
    return seal({"schema_version": "apex-compound-trajectory-development-v11", "dataset_sha256": data["content_sha256"],
                 "hashes": hashes(), "environment": environment(), "primary": PRIMARY, "recipes": reports,
                 "future_target_mutations": mutations, "development_qualified": qualified,
                 "decision": "READY_FOR_SEPARATE_FRESH_PROTOCOL" if qualified else "REJECT_TRAJECTORY_HYPOTHESIS",
                 "candidate_accepted": False, "production_promotion": False,
                 "uncertainty": "DESCRIPTIVE_HELD_OUT_ERRORS_NOT_CALIBRATED_PREDICTIVE_INTERVALS"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, compare(read_json(args.dataset)))
