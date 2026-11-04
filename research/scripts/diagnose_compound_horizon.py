"""Development-only R041 matched-horizon model comparison."""
import argparse
from pathlib import Path

import numpy as np
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import seal
from compound_horizon_common import build_cases, fit, predict
from confirm_compound_conditioned import HELDOUT as V5
from confirm_compound_conditioned import TRAIN
from confirm_compound_crossover import sign_change
from confirm_compound_reference import tables_from_archive


def development():
    all_cases, sources = {}, {}
    events = {**TRAIN, **V5}
    for horizon in (3, 6, 9):
        rows = []
        for session, identity in events.items():
            folder = ("r041-openf1-confirmation" if session in (9912, 9839) else
                      "r041-traffic-holdout" if session in (10014, 9971) else
                      "r041-reference-holdout" if session in (9963, 9955) else "r041-conditioned-holdout")
            tables, digest = tables_from_archive(Path(".cache")/folder, session, identity)
            cases, _ = build_cases(tables, session, horizon)
            rows.extend(cases)
            sources[str(session)] = digest
        all_cases[horizon] = rows
    comparisons = []
    for horizon, rows in all_cases.items():
        for kind, alpha in (("persistence", 10.), ("median", 10.), ("ridge", 1.), ("ridge", 10.), ("ridge", 100.)):
            folds = []
            for session in events:
                training = [r for r in rows if r["session"] != session]
                validation = [r for r in rows if r["session"] == session]
                model = fit(training, kind, alpha)
                predictions = [predict(model, r) for r in validation]
                scores = []
                for prefix, target in (("prefix_s", "actual_s"), ("pairwise_prefix_s", "pairwise_actual_s")):
                    observed = sum(sign_change(r[prefix], r[target]) for r in validation)
                    predicted = sum(sign_change(r[prefix], p) for r, p in zip(validation, predictions, strict=True))
                    matched = sum(sign_change(r[prefix], r[target]) and sign_change(r[prefix], p)
                                  for r, p in zip(validation, predictions, strict=True))
                    mae = float(np.mean([abs(p-r[target]) for r, p in zip(validation, predictions, strict=True)]))
                    scores.append({"observed": observed, "predicted": predicted, "matched": matched, "mae_s": mae})
                folds.append({"session": session, "blocks": len(validation), "scores": scores})
            comparisons.append({"horizon_laps": horizon, "kind": kind, "alpha": alpha, "folds": folds,
                                 "macro_mae_s": float(np.mean([s["mae_s"] for f in folds for s in f["scores"]]))})
    return seal({"scope": "OPENED_EIGHT_EVENT_HORIZON_DEVELOPMENT_ONLY", "sources": sources,
                 "source_sha256": file_sha256(Path(__file__)), "comparisons": comparisons})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, development())
