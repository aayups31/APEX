"""Opened-event R041 diagnostic: nine known laps before a three-lap forecast."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import seal
from confirm_compound_crossover import sign_change, stint_rows, timestamp
from confirm_compound_event import DEVELOPMENT, HELDOUT
from confirm_compound_reference import build_cases, tables_from_archive
from scipy.stats import theilslopes

COMPOUNDS = ("SOFT", "MEDIUM", "HARD")


def build_history(tables: dict, session: int) -> list[dict]:
    rows, _ = build_cases(tables, session)
    values = {(d, i): v for d, stints in stint_rows(tables).items() for i, _, v in stints}
    native = {(r["driver_number"], r["lap_number"]): r for r in tables["laps"]}
    meta = {(r["driver_number"], r["stint_number"]): r for r in tables["stints"]}
    result = []
    for row in rows:
        d, (i, j), ages = row["driver"], row["stints"], row["ages"]
        x, y = values[(d, i)], values[(d, j)]
        first, last = ages[6:9], ages[-3:]
        xp, yp, xt, yt = ([v[k] for k in window] for v, window in
                          ((x, first), (y, first), (x, last), (y, last)))
        history = [y[k] for k in ages[:9]]
        current = meta[(d, j)]
        lap = ages[8]-current["tyre_age_at_start"]+current["lap_start"]-1
        r = native[(d, lap)]
        result.append({**row, "current_history_s": history, "current_prefix_s": yp,
                       "prefix_s": float(np.median(xp)-np.median(yp)),
                       "actual_s": float(np.median(xt)-np.median(yt)),
                       "pairwise_prefix_s": float(np.median(np.asarray(xp)-yp)),
                       "pairwise_actual_s": float(np.median(np.asarray(xt)-yt)),
                       "forecast_at_s": timestamp(r["date_start"])+r["lap_duration"],
                       "slope9_delta_s": 3*float(theilslopes(history, range(9)).slope),
                       "slope6_delta_s": 3*float(theilslopes(history[-6:], range(6)).slope),
                       "observed_change_s": float(np.median(yt)-np.median(yp)),
                       "reference_persistence_s": float(np.median(xt)-np.median(yp)), "horizon_laps": 3})
    return result


def vector(row: dict) -> list[float]:
    return [float(row["compounds"][1] == c) for c in COMPOUNDS]+[
        row["reference_persistence_s"]-row["prefix_s"], row["slope9_delta_s"], row["slope6_delta_s"],
        float(np.median(row["current_prefix_s"])-np.median(row["current_history_s"][:3])), row["prefix_s"]]


def development() -> dict:
    events = {**DEVELOPMENT, **HELDOUT}
    cases, sources = [], {}
    for session, identity in events.items():
        folder = ("r041-openf1-confirmation" if session in (9912, 9839) else
                  "r041-traffic-holdout" if session in (10014, 9971) else
                  "r041-reference-holdout" if session in (9963, 9955) else
                  "r041-conditioned-holdout" if session in (9998, 9928) else "r041-event-holdout")
        tables, digest = tables_from_archive(Path(".cache")/folder, session, identity)
        cases.extend(build_history(tables, session))
        sources[str(session)] = digest
    settings = ([{"kind": "blend", "lambda": v} for v in (0., .25, .5, .75, 1.)]
                + [{"kind": "ridge", "alpha": v} for v in (.1, 1., 10., 100.)])
    comparisons = []
    for setting in settings:
        predictions, folds = [], []
        for session in events:
            tr = [r for r in cases if r["session"] != session]
            te = [r for r in cases if r["session"] == session]
            counts = Counter((r["session"], r["driver"], r["stints"][1], tuple(r["ages"])) for r in tr)
            weights = np.asarray([1/counts[(r["session"], r["driver"], r["stints"][1], tuple(r["ages"]))] for r in tr])
            if setting["kind"] == "ridge":
                x = np.asarray([vector(r) for r in tr]); y = np.asarray([r["observed_change_s"] for r in tr])
                beta = np.linalg.solve(x.T@(weights[:, None]*x)+setting["alpha"]*np.eye(x.shape[1]), x.T@(weights*y))
                pred = [r["reference_persistence_s"]-float(np.asarray(vector(r))@beta) for r in te]
            else:
                prior = {c: float(np.median([r["observed_change_s"] for r in tr if r["compounds"][1] == c])) for c in COMPOUNDS}
                pred = [r["reference_persistence_s"]-setting["lambda"]*r["slope6_delta_s"]
                        -(1-setting["lambda"])*prior[r["compounds"][1]] for r in te]
            predictions.extend(zip(te, pred, strict=True))
            folds.append({"session": session, "mae_s": float(np.mean([abs(p-r[t]) for r, p in zip(te, pred, strict=True)
                                                                      for t in ("actual_s", "pairwise_actual_s")]))})
        metrics = []
        for prefix, actual in (("prefix_s", "actual_s"), ("pairwise_prefix_s", "pairwise_actual_s")):
            observed = sum(sign_change(r[prefix], r[actual]) for r, p in predictions)
            predicted = sum(sign_change(r[prefix], p) for r, p in predictions)
            matched = sum(sign_change(r[prefix], r[actual]) and sign_change(r[prefix], p) for r, p in predictions)
            metrics.append({"observed": observed, "predicted": predicted, "matched": matched,
                            "min_precision_recall": matched/max(observed, predicted, 1)})
        comparisons.append({**setting, "folds": folds, "metrics": metrics,
                             "macro_mae_s": float(np.mean([r["mae_s"] for r in folds]))})
    return seal({"scope": "OPENED_TEN_EVENT_LONG_PREFIX_DEVELOPMENT_ONLY", "sources": sources,
                 "source_sha256": file_sha256(Path(__file__)), "comparisons": comparisons, "cases": len(cases)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, development())
