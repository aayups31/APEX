"""Forecast three future laps with pre-cutoff timing-line context in each race fold."""

import argparse
from pathlib import Path
from statistics import mean

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.compound_allocation import features, fit, forecast_laps, inventory
from apexsim.research.compound_readiness import LABELS, assess_event, crossing
from apexsim.research.evidence import check_seal, read_json, seal
from compound_line_proximity import proximity_features
from diagnose_compound_decision import ROOT, contrasts

FOLDER = ROOT / "docs/verification"


def evaluate(rows, sources, matrix):
    forecasts, models = {}, {}
    for event in sorted(sources):
        train = [i for i, row in enumerate(rows) if str(row["session"]) != event]
        test = [i for i, row in enumerate(rows) if str(row["session"]) == event]
        if test:
            model = fit([rows[i] for i in train], matrix[train])
            models[event] = model
            for i in test:
                forecasts[i] = forecast_laps(
                    model, matrix[i], rows[i]["current_prefix_s"]
                )
    return {**score_forecasts(rows, sources, forecasts), "models": models}


def score_forecasts(rows, sources, forecasts):
    """Apply the original paired-label race gates to a complete indexed forecast set."""
    if set(forecasts) != set(range(len(rows))):
        raise ValueError("Missing or unexpected forecast")
    folds, predictions = [], []
    for event, source in sorted(sources.items()):
        test = [i for i, row in enumerate(rows) if str(row["session"]) == event]
        if len(test) != source["blocks"]:
            raise ValueError("Changed race denominator")
        scores = [[], []]
        for i in test:
            row = rows[i]
            ref, prefix = row["reference_target_s"], row["current_prefix_s"]
            laps, hits = forecasts[i]
            values, baseline = contrasts(ref, laps), contrasts(ref, prefix)
            decisions = []
            for j, (start, target) in enumerate(LABELS):
                decision = crossing(row[start], values[j])
                decisions.append(decision)
                scores[j].append(
                    {
                        **row,
                        "predicted_s": values[j],
                        "predicted_crossover": decision,
                        "reference_persistence_s": baseline[0],
                        "own_error": abs(baseline[j] - row[target]),
                    }
                )
            predictions.append(
                {
                    "index": i,
                    "event": event,
                    "laps_s": laps,
                    "contrasts_s": values,
                    "crossings": decisions,
                    "bounded_laps": hits,
                }
            )
        labels = []
        for j, items in enumerate(scores):
            if items:
                metric = assess_event(items)["labels"][j]
                metric["label_reference_mae_s"] = mean(r["own_error"] for r in items)
                if metric["mae_s"] > metric["label_reference_mae_s"] + 1e-12:
                    metric["passed"] = False
                    metric["failure_codes"].append("PACE_WORSE_THAN_LABEL_REFERENCE")
                labels.append(metric)
        folds.append({"event": event, "cases": len(test), "labels": labels})
    if sorted(p["index"] for p in predictions) != list(range(len(rows))):
        raise ValueError("Forecast inventory mismatch")
    failed = [f["event"] for f in folds if any(not m["passed"] for m in f["labels"])]
    informative = sum(
        bool(f["labels"]) and all(m["observed"] for m in f["labels"]) for f in folds
    )
    return {
        "qualified": not failed and informative >= 2,
        "informative_events": informative,
        "failed_events": failed,
        "macro_mae_s": mean(m["mae_s"] for f in folds for m in f["labels"]),
        "folds": folds,
        "predictions": predictions,
    }


def study():
    data, linked, control = [
        read_json(FOLDER / name)
        for name in (
            "compound-v11-development-data.json",
            "compound-v15-timing-lines.json",
            "compound-v13-development.json",
        )
    ]
    for item in (data, linked, control):
        check_seal(item)
    if (
        not data["content_sha256"]
        == linked["parent_sha256"]
        == control["dataset_sha256"]
    ):
        raise ValueError("Source cohort mismatch")
    sources = [
        s
        for name in (
            "compound-nomination-inventory.json",
            "compound-v13-nomination-additions.json",
        )
        for s in read_json(FOLDER / name)["sources"]
    ]
    allocations = inventory(sources, set(data["sources"]))
    rows = data["cases"]
    matrix = np.asarray(
        [
            features(r, allocations, True) + proximity_features(r, links)
            for r, links in zip(rows, linked["joins"], strict=True)
        ]
    )
    result = evaluate(rows, data["sources"], matrix)
    previous = set(control["recipes"]["nominated"]["failed_events"])
    failed = set(result["failed_events"])
    return seal(
        {
            "schema": "compound-line-proximity-v15",
            "result": result,
            "control_sha256": control["content_sha256"],
            "links_sha256": linked["content_sha256"],
            "gained_events": sorted(previous - failed),
            "lost_events": sorted(failed - previous),
            "development_qualified": result["qualified"],
            "new_holdout_acquisition_allowed": result["qualified"],
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, study())
