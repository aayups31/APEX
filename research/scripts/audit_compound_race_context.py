"""Independently reconstruct R041 v15-v17 race gates from saved three-lap forecasts."""

import argparse
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_repair import LABELS, compare, crossing, event_report
from diagnose_compound_decision import ROOT


def check_result(data, doc):
    check_seal(doc)
    result, rows = doc["result"], data["cases"]
    compare(
        sorted(p["index"] for p in result["predictions"]),
        list(range(len(rows))),
        "cases",
    )
    compare(
        [f["event"] for f in result["folds"]], sorted(data["sources"]), "fold inventory"
    )
    groups = defaultdict(list)
    for p in result["predictions"]:
        row, laps = rows[p["index"]], p["laps_s"]
        event = str(row["session"])
        compare(p["event"], event, "case event")
        ref, prefix = row["reference_target_s"], row["current_prefix_s"]
        if (
            len(laps) != 3
            or max(abs(a - b) for a, b in zip(laps, prefix, strict=True)) > 2.0 + 1e-12
        ):
            raise ValueError("Forecast outside registered bounds")
        values = [
            median(ref) - median(laps),
            median(r - l for r, l in zip(ref, laps, strict=True)),
        ]
        refs = [
            median(ref) - median(prefix),
            median(r - l for r, l in zip(ref, prefix, strict=True)),
        ]
        compare(p["contrasts_s"], values, "pace contrasts")
        for label, (start, target) in enumerate(LABELS):
            decision = crossing(row[start], values[label])
            compare(p["crossings"][label], decision, "label decision")
            groups[event, label].append(
                {
                    **row,
                    "predicted_s": values[label],
                    "predicted_crossover": decision,
                    "reference_persistence_s": refs[0],
                    "own": abs(refs[label] - row[target]),
                }
            )
    failed, errors, informative = [], [], 0
    for fold in result["folds"]:
        event = fold["event"]
        compare(fold["cases"], data["sources"][event]["blocks"], "race support")
        labels = []
        for j in range(2):
            items = groups[event, j]
            compare(len(items), fold["cases"], "label support")
            if items:
                metric = event_report(items)["labels"][j]
                metric["label_reference_mae_s"] = mean(item["own"] for item in items)
                if metric["mae_s"] > metric["label_reference_mae_s"] + 1e-12:
                    metric["failure_codes"].append("PACE_WORSE_THAN_LABEL_REFERENCE")
                    metric["passed"] = False
                errors.append(metric["mae_s"])
                labels.append(metric)
        compare(fold["labels"], labels, "independent race gates")
        if any(not m["passed"] for m in labels):
            failed.append(event)
        informative += bool(labels) and all(m["observed"] for m in labels)
    qualified = not failed and informative >= 2
    compare(result["failed_events"], failed, "failed races")
    compare(result["informative_events"], informative, "informative races")
    compare(result["macro_mae_s"], mean(errors), "mean error")
    for flag in (
        result["qualified"],
        doc["development_qualified"],
        doc["new_holdout_acquisition_allowed"],
    ):
        compare(flag, qualified, "qualification")
    return {
        "result_sha256": doc["content_sha256"],
        "forecasts": len(rows),
        "event_labels": len(errors),
        "failed_races": len(failed),
        "qualified": qualified,
        "macro_mae_s": mean(errors),
    }


def audit():
    folder = ROOT / "docs/verification"
    data = read_json(folder / "compound-v11-development-data.json")
    check_seal(data)
    return seal(
        {
            "schema": "compound-race-context-scalar-audit",
            "dataset_sha256": data["content_sha256"],
            "studies": {
                v: check_result(
                    data, read_json(folder / f"compound-{v}-development.json")
                )
                for v in ("v15", "v16", "v17")
            },
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, audit())
