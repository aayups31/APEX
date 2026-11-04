"""R041 failure inventory and nested event-adaptive diagnostic; no acquisition."""
from __future__ import annotations

import argparse
from itertools import product
from math import ceil
from pathlib import Path
from statistics import mean

from apexsim.provenance import write_manifest
from apexsim.research.compound_adaptive import predict_adaptive
from apexsim.research.compound_bounded import bounded_features, training_weights
from apexsim.research.compound_conditioned import fit_conditioned, predict_conditioned
from apexsim.research.compound_readiness import LABELS, assess_event, assess_panel
from apexsim.research.evidence import check_seal, seal
from compound_bounded_common import environment
from compound_repair_data import opened_data
from confirm_compound_multiseason import BASE, canonical_file_sha
from sklearn.ensemble import RandomForestRegressor

SETTINGS = [{"shrinkage": weight, "minimum_drivers": support, "decision_margin_s": margin, "bound_s": .5}
            for weight, support, margin in product((0., .5, 1.), (1, 3, 5), (.15, .30))]


def hashes() -> dict:
    paths = [Path(__file__), Path(__file__).with_name("compound_repair_data.py"),
             BASE/"research/protocols/COMPOUND_FAILURE_REPAIR_V10.md"]
    paths += [BASE/"apex_engine/src/apexsim/research"/name for name in (
        "compound_adaptive.py", "compound_readiness.py", "compound_bounded.py", "compound_conditioned.py")]
    return {str(p.relative_to(BASE)).replace("\\", "/"): canonical_file_sha(p) for p in paths}


def selection_key(item: dict) -> tuple:
    config = item["setting"]
    return (item["failed_event_labels"], item["negative_control_false_alarms"], item["macro_mae_s"],
            config["shrinkage"], -config["minimum_drivers"], config["decision_margin_s"])


def summary(rows: list[dict], settings: dict, predictions: list[dict], events: list) -> dict:
    folds = [{"event": str(e), **assess_event([p for p in predictions if p["session"] == e])} for e in events]
    supported = [f for f in folds if f["cases"]]
    labels = [label for f in supported for label in f["labels"]]
    return {"setting": settings, "failed_event_labels": sum(not r["passed"] for r in labels),
            "negative_control_false_alarms": sum(r["predicted"] for r in labels if not r["observed"]),
            "macro_mae_s": mean(r["mae_s"] for r in labels), "folds": folds,
            "readiness": assess_panel(predictions, events)}


def compare(data: dict, *, settings: list[dict] | None = None, comparators: bool = True) -> dict:
    """Nested parameter selection excludes outer event from metrics and radii."""
    check_seal(data)
    rows = data["cases"]
    events = list(dict.fromkeys(r["session"] for r in rows))
    if len(events) < 4:
        raise ValueError("Nested repair evaluation needs at least four supported events")
    settings = SETTINGS if settings is None else settings
    predictions = [[{**r, **predict_adaptive(r, **setting)} for r in rows] for setting in settings]
    grid = [summary(rows, setting, pred, events) for setting, pred in zip(settings, predictions, strict=True)]
    selected = min(range(len(grid)), key=lambda i: selection_key(grid[i]))
    nested, selections = [], []
    for outer in events:
        inner_events = [e for e in events if e != outer]
        inner_grid = [summary(rows, setting, [r for r in pred if r["session"] != outer], inner_events)
                      for setting, pred in zip(settings, predictions, strict=True)]
        chosen = min(range(len(inner_grid)), key=lambda i: selection_key(inner_grid[i]))
        errors = sorted(max(abs(r["predicted_s"]-r[t]) for _, t in LABELS)
                        for r in predictions[chosen] if r["session"] != outer)
        radius = errors[min(len(errors), ceil((len(errors)+1)*.9))-1]
        test = [{**r, **predict_adaptive(r, **settings[chosen], radius_s=radius)} for r in rows if r["session"] == outer]
        nested.extend(test)
        selections.append({"outer_event": str(outer), "setting": settings[chosen], "radius_s": radius,
                           "training_events": [str(e) for e in inner_events], "inner_grid": inner_grid,
                           "outer_metrics": assess_event(test)})
    comparators_out = []
    if comparators:
        for event in events:
            train, test = [r for r in rows if r["session"] != event], [r for r in rows if r["session"] == event]
            ridge = fit_conditioned(train)
            forest = RandomForestRegressor(n_estimators=128, max_depth=3, min_samples_leaf=8, random_state=41, n_jobs=1)
            forest.fit([bounded_features(r, "context") for r in train],
                       [.5*(r["actual_s"]+r["pairwise_actual_s"]) for r in train], sample_weight=training_weights(train))
            tree = forest.predict([bounded_features(r, "context") for r in test])
            ridge_predictions = [predict_conditioned(ridge, r)["predicted_s"] for r in test]
            baselines = {"ridge": ridge_predictions, "tree": tree, "contrast": [r["prefix_s"] for r in test],
                         "midpoint": [.5*(p["reference_persistence_s"]+r["prefix_s"]) for r, p in
                                      zip(test, (predict_adaptive(r, shrinkage=0.) for r in test), strict=True)]}
            comparators_out.append({"event": str(event), "mae_s": {name: [mean(abs(float(p)-r[target]) for r, p in
                    zip(test, values, strict=True)) for _, target in LABELS] for name, values in baselines.items()}})
    panel = assess_panel(nested, sorted(data.get("sources", dict.fromkeys(str(e) for e in events))))
    return seal({"schema_version": "apex-compound-repair-nested-development-v10", "dataset_sha256": data["content_sha256"],
                 "hashes": hashes(), "environment": environment(), "grid": grid, "selected_setting": settings[selected],
                 "nested_selections": selections, "nested_predictions": nested, "readiness": panel,
                 "comparators": comparators_out, "candidate_accepted": False, "production_promotion": False,
                 "decision": "READY_FOR_SEPARATE_FRESH_PROTOCOL" if panel["development_qualified"] else "REJECT_REPAIR_HYPOTHESIS",
                 "uncertainty": "EMPIRICAL_CROSS_EVENT_ERRORS_NOT_GUARANTEED_COVERAGE"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, compare(opened_data()))
