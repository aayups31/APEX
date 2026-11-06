"""R041 fixed expanded training comparison at unchanged forecast times."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.compound_allocation import (
    ORDER,
    SEASONS,
    fit,
    forecast_laps,
    inventory,
)
from apexsim.research.compound_readiness import LABELS, assess_event, crossing
from apexsim.research.evidence import check_seal, read_json, seal
from diagnose_compound_decision import ROOT, contrasts

FOLDER = ROOT / "docs/verification"


def current_features(row: dict, nominations: dict) -> list:
    when = datetime.fromtimestamp(row["forecast_at_s"], tz=timezone.utc)
    issued, nomination = nominations[str(row["session"])]
    if issued >= when.date() or when.year not in SEASONS:
        raise ValueError("Window lacks a supported pre-race nomination")
    compound = row["compounds"][1]
    prefix = row["current_prefix_s"]
    center = median(prefix)
    return [
        *[p - center for p in prefix],
        center,
        row["ages"][0],
        *[int(compound == c) for c in ORDER],
        *[int(nomination[compound] == n) for n in range(1, 7)],
        *[int(when.year == y) for y in SEASONS],
    ]


def unique_rows(cases: list[dict]) -> list:
    windows = {}
    for r in cases:
        key = str(r["session"]), r["driver"], r["stints"][1], tuple(r["ages"])
        item = {
            "session": key[0],
            "driver": key[1],
            "stints": [None, key[2]],
            "ages": r["ages"],
            "compounds": [None, r["compounds"][1]],
            "forecast_at_s": r["forecast_at_s"],
            "current_prefix_s": r["current_prefix_s"],
            "current_target_s": r["current_target_s"],
        }
        if key in windows and windows[key] != item:
            raise ValueError("Conflicting duplicate current window")
        windows[key] = item
    return list(windows.values())


def evaluate(train_pool: list, cases: list, nominations: dict, base: dict) -> dict:
    matrix = np.asarray([current_features(r, nominations) for r in train_pool])
    folds, models, predictions = [], {}, []
    for event in sorted(nominations):
        outer = [(i, r) for i, r in enumerate(cases) if str(r["session"]) == event]
        training = [i for i, r in enumerate(train_pool) if r["session"] != event]
        if outer:
            model = fit([train_pool[i] for i in training], matrix[training])
            models[event] = model
        scored = [[], []]
        for i, row in outer:
            previous = base[i]
            if previous["event"] != event:
                raise ValueError("V13 case/fold mismatch")
            auxiliary, hits = forecast_laps(
                model, current_features(row, nominations), row["current_prefix_s"]
            )
            laps = [
                (a + b) / 2 for a, b in zip(previous["laps_s"], auxiliary, strict=True)
            ]
            values = contrasts(row["reference_target_s"], laps)
            reference = contrasts(row["reference_target_s"], row["current_prefix_s"])
            decisions = []
            for j, (start, target) in enumerate(LABELS):
                decision = crossing(row[start], values[j])
                decisions.append(decision)
                scored[j].append(
                    {
                        **row,
                        "predicted_crossover": decision,
                        "predicted_s": values[j],
                        "reference_persistence_s": reference[0],
                        "own_error": abs(reference[j] - row[target]),
                    }
                )
            predictions.append(
                {
                    "index": i,
                    "event": event,
                    "laps_s": laps,
                    "auxiliary_laps_s": auxiliary,
                    "auxiliary_bound_hits": hits,
                    "contrasts_s": values,
                    "crossings": decisions,
                }
            )
        labels = []
        for j, items in enumerate(scored):
            if items:
                metric = assess_event(items)["labels"][j]
                metric["label_reference_mae_s"] = mean(r["own_error"] for r in items)
                if metric["mae_s"] > metric["label_reference_mae_s"] + 1e-12:
                    metric["passed"] = False
                    metric["failure_codes"].append("PACE_WORSE_THAN_LABEL_REFERENCE")
                labels.append(metric)
        folds.append(
            {
                "event": event,
                "cases": len(outer),
                "training_windows": len(training),
                "labels": labels,
            }
        )
    if sorted(p["index"] for p in predictions) != list(range(len(cases))):
        raise ValueError("Missing evaluation case")
    informative = sum(
        bool(f["labels"]) and all(m["observed"] for m in f["labels"]) for f in folds
    )
    failures = [f["event"] for f in folds if any(not m["passed"] for m in f["labels"])]
    return {
        "folds": folds,
        "models": models,
        "predictions": predictions,
        "failed_events": failures,
        "informative_events": informative,
        "qualified": informative >= 2 and not failures,
        "macro_mae_s": mean(m["mae_s"] for f in folds for m in f["labels"]),
    }


def study() -> dict:
    data, extra, v13 = (
        read_json(FOLDER / name)
        for name in (
            "compound-v11-development-data.json",
            "compound-v14-training-windows.json",
            "compound-v13-development.json",
        )
    )
    for obj in (data, extra, v13):
        check_seal(obj)
    if (
        extra["parent_sha256"] != data["content_sha256"]
        or v13["dataset_sha256"] != data["content_sha256"]
    ):
        raise ValueError("Input cohort mismatch")
    docs = [
        read_json(FOLDER / name)
        for name in (
            "compound-nomination-inventory.json",
            "compound-v13-nomination-additions.json",
        )
    ]
    nominations = inventory(
        [s for d in docs for s in d["sources"]], set(data["sources"])
    )
    cases = data["cases"]
    paired = unique_rows(cases)
    expanded = unique_rows([*paired, *extra["additional_windows"]])
    if len(expanded) != len(paired) + len(extra["additional_windows"]):
        raise ValueError("Overlapping training identities")
    base = {p["index"]: p for p in v13["recipes"]["nominated"]["predictions"]}
    recipes = {
        name: evaluate(pool, cases, nominations, base)
        for name, pool in (("paired", paired), ("expanded", expanded))
    }
    qualified = recipes["expanded"]["qualified"]
    return seal(
        {
            "schema": "compound-unpaired-v14",
            "additional_sha256": extra["content_sha256"],
            "v13_result_sha256": v13["content_sha256"],
            "paired_windows": len(paired),
            "expanded_windows": len(expanded),
            "recipes": recipes,
            "development_qualified": qualified,
            "new_holdout_acquisition_allowed": qualified,
            "production_promotion": False,
            "candidate_accepted": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, study())
