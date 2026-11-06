"""Replay the two fixed R041 nomination recipes on the full opened cohort."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
from statistics import mean

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.compound_allocation import features, fit, forecast_laps, inventory
from apexsim.research.compound_readiness import LABELS, assess_event, crossing
from apexsim.research.evidence import check_seal, read_json, seal
from compound_bounded_common import environment
from diagnose_compound_decision import ROOT, contrasts

FOLDER = ROOT / "docs/verification"


def run_recipe(rows: list[dict], allocations: dict, include_allocation: bool) -> dict:
    matrix = np.asarray([features(r, allocations, include_allocation) for r in rows])
    models, predictions, folds = {}, [], []
    for event in sorted(allocations):
        train = [i for i, r in enumerate(rows) if str(r["session"]) != event]
        test = [i for i, r in enumerate(rows) if str(r["session"]) == event]
        scores = [[], []]
        if test:
            model = fit([rows[i] for i in train], matrix[train])
            models[event] = model
        for index in test:
            row = rows[index]
            prefix = row["current_prefix_s"]
            laps, hits = forecast_laps(model, matrix[index], prefix)
            values = contrasts(row["reference_target_s"], laps)
            baseline = contrasts(row["reference_target_s"], prefix)
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
                    "index": index,
                    "event": event,
                    "laps_s": laps,
                    "contrasts_s": values,
                    "crossings": decisions,
                    "bounded_laps": hits,
                }
            )
        metrics = []
        for j, items in enumerate(scores):
            if items:
                metric = assess_event(items)["labels"][j]
                metric["label_reference_mae_s"] = mean(
                    item["own_error"] for item in items
                )
                if metric["mae_s"] > metric["label_reference_mae_s"] + 1e-12:
                    metric["passed"] = False
                    metric["failure_codes"].append("PACE_WORSE_THAN_LABEL_REFERENCE")
                metrics.append(metric)
        folds.append({"event": event, "cases": len(test), "labels": metrics})
    if sorted(p["index"] for p in predictions) != list(range(len(rows))):
        raise ValueError("Allocation study lost forecast cases")
    supported = [f for f in folds if f["cases"]]
    failed = [
        f["event"] for f in supported if any(not m["passed"] for m in f["labels"])
    ]
    informative = sum(all(m["observed"] for m in f["labels"]) for f in supported)
    return {
        "models": models,
        "folds": folds,
        "predictions": predictions,
        "failed_events": failed,
        "informative_events": informative,
        "qualified": not failed and informative >= 2,
        "macro_mae_s": mean(m["mae_s"] for f in supported for m in f["labels"]),
    }


def study() -> dict:
    paths = [
        FOLDER / name
        for name in (
            "compound-nomination-inventory.json",
            "compound-v13-nomination-additions.json",
        )
    ]
    sources = [s for path in paths for s in read_json(path)["sources"]]
    data = read_json(FOLDER / "compound-v11-development-data.json")
    check_seal(data)
    allocations = inventory(sources, set(data["sources"]))
    rows = data["cases"]
    for event, meta in data["sources"].items():
        if sum(str(r["session"]) == event for r in rows) != meta["blocks"]:
            raise ValueError("Allocation source count mismatch")
    recipes = {
        name: run_recipe(rows, allocations, flag)
        for name, flag in (("relative", False), ("nominated", True))
    }
    paths += [
        Path(__file__),
        ROOT / "apex_engine/src/apexsim/research/compound_allocation.py",
        ROOT / "research/protocols/COMPOUND_ALLOCATION_V13.md",
    ]
    hashes = {
        p.relative_to(ROOT).as_posix(): sha256(
            p.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for p in paths
    }
    qualified = recipes["nominated"]["qualified"]
    return seal(
        {
            "schema": "compound-allocation-v13",
            "dataset_sha256": data["content_sha256"],
            "hashes": hashes,
            "environment": environment(),
            "recipes": recipes,
            "development_qualified": qualified,
            "new_holdout_acquisition_allowed": qualified,
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, study())
