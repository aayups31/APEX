"""Development-only R041 three-season training expansion and event-safe comparison."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from apexsim.provenance import file_sha256, write_manifest
from apexsim.data import tyre_dataset
from apexsim.research.compound_conditioned import fit_conditioned, predict_conditioned
from apexsim.research.compound_crossover_head import fit_event, predict_event
from apexsim.research.evidence import check_seal, read_json, seal
from compound_multiseason import ARCHIVES, fastf1_cases
from confirm_compound_event import DEVELOPMENT, HELDOUT, event_counts
from confirm_compound_reference import build_cases, tables_from_archive


def prepare() -> dict:
    rows, sources = [], {}
    for session, identity in {**DEVELOPMENT, **HELDOUT}.items():
        folder = ("r041-openf1-confirmation" if session in (9912, 9839) else
                  "r041-traffic-holdout" if session in (10014, 9971) else
                  "r041-reference-holdout" if session in (9963, 9955) else
                  "r041-conditioned-holdout" if session in (9998, 9928) else "r041-event-holdout")
        tables, digest = tables_from_archive(Path(".cache")/folder, session, identity)
        cases, _ = build_cases(tables, session)
        rows.extend(cases)
        sources[str(session)] = {"archive_sha256": digest, "blocks": len(cases), "provider": "OPENF1"}
    for archive in ARCHIVES:
        cases, metadata = fastf1_cases(archive)
        rows.extend(cases)
        sources[metadata["event_id"]] = {**metadata, "provider": "FASTF1"}
    dependencies = (Path(__file__), Path(__file__).with_name("compound_multiseason.py"), Path(tyre_dataset.__file__))
    return seal({"scope": "OPENED_NINETEEN_EVENT_THREE_SEASON_DEVELOPMENT_ONLY", "sources": sources,
                 "implementation": {p.name: file_sha256(p) for p in dependencies},
                 "truth_labels": {"native_times": "PROVIDER_PARSED_SOURCE", "pace_s": "FUEL_PRIOR_CORRECTED_PROXY",
                                  "forecast_clock": "NATIVE_UTC_LAP_END", "physical_wear": "UNKNOWN"}, "cases": rows})


def compare(data: dict) -> dict:
    check_seal(data)
    rows = data["cases"]
    events = list(dict.fromkeys(r["session"] for r in rows))
    comparisons, point_folds = [], []
    for c in (.1, 1., 10.):
        validation, scores = [], []
        for event in events:
            training = [r for r in rows if r["session"] != event]
            testing = [r for r in rows if r["session"] == event]
            event_model = fit_event(training, c)
            validation.extend(testing)
            scores.extend(predict_event(event_model, r)["crossover_score"] for r in testing)
            if c == .1:
                pace = fit_conditioned(training)
                predictions = [predict_conditioned(pace, r) for r in testing]
                labels = []
                for prefix, actual in (("prefix_s", "actual_s"), ("pairwise_prefix_s", "pairwise_actual_s")):
                    labels.append({"mae_s": float(np.mean([abs(p["predicted_s"]-r[actual])
                                                          for r, p in zip(testing, predictions, strict=True)])),
                                   "contrast_persistence_mae_s": float(np.mean([abs(r[prefix]-r[actual]) for r in testing])),
                                   "reference_persistence_mae_s": float(np.mean([abs(p["reference_persistence_s"]-r[actual])
                                                                               for r, p in zip(testing, predictions, strict=True)]))})
                point_folds.append({"event": event, "blocks": len(testing), "labels": labels})
        for threshold in np.linspace(.35, .65, 31).tolist():
            decisions = [s >= threshold for s in scores]
            counts = [event_counts(validation, decisions, pairwise=p) for p in (False, True)]
            comparisons.append({"c": c, "threshold": threshold, "counts": counts,
                                 "selection_score": min(r["min_precision_recall"] for r in counts)})
    return seal({"scope": "NINETEEN_EVENT_DEVELOPMENT_NOT_CONFIRMATION", "dataset_sha256": data["content_sha256"],
                 "cases": len(rows), "event_count": len(events), "comparisons": comparisons, "point_folds": point_folds})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "compare"))
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, prepare() if args.stage == "prepare" else compare(read_json(args.dataset)))
