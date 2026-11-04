"""Nested whole-event R041 development; no fresh confirmation acquisition."""
from __future__ import annotations

import argparse
from copy import deepcopy
from itertools import product
from pathlib import Path

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.compound_bounded import (
    BASELINES,
    bounded_features,
    cross_event_radius,
    fit_bounded,
    predict_bounded,
    training_weights,
)
from apexsim.research.compound_conditioned import fit_conditioned, predict_conditioned
from apexsim.research.compound_crossover_head import crossover, fit_event, predict_event
from apexsim.research.evidence import check_seal, read_json, seal
from compound_bounded_common import environment, source_hashes
from confirm_compound_multiseason import canonical_file_sha
from sklearn.ensemble import RandomForestRegressor

SETTINGS = [{"baseline": b, "group": g, "alpha": a, "bound_s": cap} for b, g, a, cap in
            product(BASELINES, ("pace", "context"), (10., 100.), (0., .25, .5))]
LABELS = (("prefix_s", "actual_s"), ("pairwise_prefix_s", "pairwise_actual_s"))


def pace_metrics(rows: list[dict], predictions: list[dict]) -> list[dict]:
    """Both definitions, same denominator, including fallback and bounded cases."""
    result = []
    for prefix, target in LABELS:
        errors = [p["predicted_s"]-r[target] for r, p in zip(rows, predictions, strict=True)]
        reference = [abs(p["reference_persistence_s"]-r[target]) for r, p in zip(rows, predictions, strict=True)]
        contrast = [abs(r[prefix]-r[target]) for r in rows]
        intervals = all(p.get("lower_s") is not None for p in predictions)
        result.append({"mae_s": float(np.mean(np.abs(errors))), "rmse_s": float(np.sqrt(np.mean(np.square(errors)))),
                       "reference_mae_s": float(np.mean(reference)), "contrast_mae_s": float(np.mean(contrast)),
                       "coverage": float(np.mean([p["lower_s"] <= r[target] <= p["upper_s"]
                           for r, p in zip(rows, predictions, strict=True)])) if intervals else None,
                       "mean_width_s": float(np.mean([p["upper_s"]-p["lower_s"] for p in predictions])) if intervals else None})
    return result


def event_metrics(rows: list[dict], decisions: list[bool]) -> list[dict]:
    result = []
    for prefix, target in LABELS:
        observed = [crossover(r[prefix], r[target]) for r in rows]
        matched = sum(a and b for a, b in zip(observed, decisions, strict=True))
        count, predicted = sum(observed), sum(decisions)
        result.append({"observed": count, "predicted": predicted, "matched": matched,
                       "recall": matched/count if count else None, "precision": matched/predicted if predicted else None,
                       "min_precision_recall": matched/max(count, predicted, 1)})
    return result


def compare(data: dict, *, settings: list[dict] | None = None,
            cs: tuple[float, ...] = (.1, 1., 10.), thresholds: tuple[float, ...] | None = None,
            tree: bool = True) -> dict:
    """Choose every outer forecast using only its other whole events.

    Inner fits exclude both outer and inner events. Prediction caches share
    parameters only when their entire training-event set is identical.
    """
    check_seal(data)
    if data["implementation_sha256_lf"] != source_hashes():
        raise ValueError("Bounded development source binding changed; rebuild in a fresh output")
    rows = data["cases"]
    training_weights(rows)  # Validate repeated targets before any fold selection.
    events = list(dict.fromkeys(r["session"] for r in rows))
    if len(events) < 4:
        raise ValueError("Nested compound development needs at least four supported events")
    settings = SETTINGS if settings is None else settings
    thresholds = tuple(np.linspace(.35, .65, 31).tolist()) if thresholds is None else thresholds
    indices = {e: [i for i, r in enumerate(rows) if r["session"] == e] for e in events}
    models, pace_cache, event_cache, event_models = {}, {}, {}, {}

    def pace(excluded: frozenset, test: object, setting: dict) -> list[dict]:
        model_key = (excluded, setting["baseline"], setting["group"], setting["alpha"])
        prediction_key = (model_key, test)
        if model_key not in models:
            train = [r for r in rows if r["session"] not in excluded]
            models[model_key] = fit_bounded(train, **{**setting, "bound_s": 0.})
        if prediction_key not in pace_cache:
            pace_cache[prediction_key] = [predict_bounded(models[model_key], rows[i]) for i in indices[test]]
        result = []
        for cached in pace_cache[prediction_key]:
            p = dict(cached)
            correction = 0. if p["fallback"] else float(np.clip(p["raw_correction_s"], -setting["bound_s"], setting["bound_s"]))
            p.update(applied_correction_s=correction, predicted_s=p["baseline_s"]+correction,
                     correction_bounded=not p["fallback"] and abs(p["raw_correction_s"]) > setting["bound_s"])
            result.append(p)
        return result

    def event_scores(excluded: frozenset, test: object, c: float) -> list[float]:
        key = excluded, test, c
        if key not in event_cache:
            model_key = excluded, c
            if model_key not in event_models:
                train = [r for r in rows if r["session"] not in excluded]
                event_models[model_key] = fit_event(train, c)
            model = event_models[model_key]
            event_cache[key] = [predict_event(model, rows[i])["crossover_score"] for i in indices[test]]
        return event_cache[key]

    def selection(outer: object | None) -> tuple[dict, dict, list[dict], list[dict], list[dict]]:
        held = [e for e in events if e != outer]
        validation = [rows[i] for e in held for i in indices[e]]
        grid = []
        for setting in settings:
            folds, predictions = [], []
            for e in held:
                excluded = frozenset((e,)) if outer is None else frozenset((e, outer))
                forecast = pace(excluded, e, setting)
                predictions.extend(forecast)
                folds.append({"event": e, "cases": len(indices[e]),
                              "labels": pace_metrics([rows[i] for i in indices[e]], forecast),
                              "fallback_cases": sum(p["fallback"] for p in forecast)})
            grid.append({"setting": setting, "macro_mae_s": float(np.mean([label["mae_s"] for f in folds for label in f["labels"]])),
                         "folds": folds})
        chosen = min(grid, key=lambda g: (g["macro_mae_s"], g["setting"]["bound_s"],
                     g["setting"]["group"] != "pace", -g["setting"]["alpha"], BASELINES.index(g["setting"]["baseline"])))
        event_grid = []
        for c in cs:
            scores = []
            for e in held:
                excluded = frozenset((e,)) if outer is None else frozenset((e, outer))
                scores.extend(event_scores(excluded, e, c))
            for threshold in thresholds:
                counts = event_metrics(validation, [score >= threshold for score in scores])
                event_grid.append({"c": c, "threshold": threshold, "labels": counts,
                                   "selection_score": min(m["min_precision_recall"] for m in counts)})
        event_choice = min(event_grid, key=lambda g: (-g["selection_score"], g["c"], abs(g["threshold"]-.5)))
        residuals = []
        for e in held:
            excluded = frozenset((e,)) if outer is None else frozenset((e, outer))
            ps = pace(excluded, e, chosen["setting"])
            residuals.extend(max(abs(p["predicted_s"]-rows[i][target]) for _, target in LABELS)
                             for i, p in zip(indices[e], ps, strict=True))
        return chosen, event_choice, grid, event_grid, residuals

    full_choice, full_event, full_grid, full_event_grid, full_errors = selection(None)
    nested_rows, outer_folds = [], []
    for outer in events:
        chosen, event_choice, inner_grid, inner_event_grid, residuals = selection(outer)
        forecast = pace(frozenset((outer,)), outer, chosen["setting"])
        scores = event_scores(frozenset((outer,)), outer, event_choice["c"])
        radius = cross_event_radius(residuals)
        setting = chosen["setting"]
        outer_pace = deepcopy(models[(frozenset((outer,)), setting["baseline"], setting["group"], setting["alpha"])])
        outer_pace.update(bound_s=setting["bound_s"], radius_s=radius)
        outer_event = {**event_models[(frozenset((outer,)), event_choice["c"])], "threshold": event_choice["threshold"]}
        for index, p, score in zip(indices[outer], forecast, scores, strict=True):
            p.update(lower_s=p["predicted_s"]-radius, upper_s=p["predicted_s"]+radius)
            nested_rows.append({**rows[index], **p, "crossover_score": score,
                                "predicted_crossover": score >= event_choice["threshold"]})
        test = [r for r in nested_rows if r["session"] == outer]
        labels = pace_metrics(test, test)
        counts = event_metrics(test, [r["predicted_crossover"] for r in test])
        outer_folds.append({"event": outer, "cases": len(test), "setting": chosen["setting"],
                            "event_head": {"c": event_choice["c"], "threshold": event_choice["threshold"]},
                            "training_events": [e for e in events if e != outer], "radius_s": radius,
                            "radius_source": "INNER_EVENT_ERRORS_OUTER_EVENT_EXCLUDED",
                            "pace_head": outer_pace, "event_head_parameters": outer_event,
                            "inner_cv_errors_s": residuals,
                            "pace": labels, "events": counts, "inner_grid": inner_grid, "inner_event_grid": inner_event_grid,
                            "fallback_cases": sum(p["fallback"] for p in test),
                            "bounded_cases": sum(p["correction_bounded"] for p in test),
                            "passed_labels": [m["mae_s"] <= min(m["reference_mae_s"], m["contrast_mae_s"])
                                and c["observed"] > 0 and c["predicted"] > 0 and c["min_precision_recall"] >= .5
                                for m, c in zip(labels, counts, strict=True)]})
    macro = [{k: float(np.mean([f["pace"][label][k] for f in outer_folds]))
              for k in ("mae_s", "reference_mae_s", "contrast_mae_s", "coverage", "mean_width_s")} for label in (0, 1)]
    counts = event_metrics(nested_rows, [r["predicted_crossover"] for r in nested_rows])
    qualified = (all(m["mae_s"] <= min(m["reference_mae_s"], m["contrast_mae_s"]) for m in macro)
                 and all(c["min_precision_recall"] >= .5 for c in counts))
    comparators = []
    for e in events:
        train, test = [r for r in rows if r["session"] != e], [rows[i] for i in indices[e]]
        old = fit_conditioned(train)
        predictions = [predict_conditioned(old, r) for r in test]
        entry = {"event": e, "unbounded_ridge": pace_metrics(test, predictions)}
        if tree:
            forest = RandomForestRegressor(n_estimators=128, max_depth=3, min_samples_leaf=8, random_state=41, n_jobs=1)
            forest.fit([bounded_features(r, "context") for r in train],
                       [.5*(r["actual_s"]+r["pairwise_actual_s"]) for r in train], sample_weight=training_weights(train))
            values = forest.predict([bounded_features(r, "context") for r in test])
            entry["tree"] = pace_metrics(test, [{"predicted_s": float(value),
                "reference_persistence_s": p["reference_persistence_s"]} for value, p in zip(values, predictions, strict=True)])
        comparators.append(entry)
    model = fit_bounded(rows, **full_choice["setting"])
    model["radius_s"] = cross_event_radius(full_errors)
    event_model = fit_event(rows, full_event["c"])
    event_model["threshold"] = full_event["threshold"]
    return seal({"schema_version": "apex-compound-bounded-nested-development-v9", "dataset_sha256": data["content_sha256"],
                 "scope": "NESTED_DEVELOPMENT_NOT_FRESH_CONFIRMATION", "source_sha256_lf": canonical_file_sha(Path(__file__)),
                 "implementation_sha256_lf": source_hashes(), "environment": environment(),
                 "cases": len(rows), "supported_events": len(events), "full_grid": full_grid, "full_event_grid": full_event_grid,
                 "selected_setting": full_choice["setting"], "selected_event_head": {"c": full_event["c"], "threshold": full_event["threshold"]},
                 "pace_head": model, "event_head": event_model, "outer_folds": outer_folds, "nested_predictions": nested_rows,
                 "nested_macro_pace": macro, "nested_pooled_events": counts, "comparators": comparators,
                 "development_qualified": qualified, "candidate_accepted": False,
                 "decision": "REQUIRES_SEPARATE_PROSPECTIVE_CONFIRMATION" if qualified else "REJECT_DEVELOPMENT_QUALIFICATION",
                 "uncertainty": "EMPIRICAL_CROSS_EVENT_RADIUS_NOT_A_COVERAGE_GUARANTEE",
                 "production_promotion": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, compare(read_json(args.dataset)))
