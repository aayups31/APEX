"""Development-only R041 comparison of time-bounded in-race compound context."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.compound_conditioned import feature_vector, window_key
from apexsim.research.evidence import seal
from confirm_compound_conditioned import HELDOUT as V5
from confirm_compound_conditioned import TRAIN
from confirm_compound_crossover import stint_rows, timestamp
from confirm_compound_reference import build_cases, tables_from_archive
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge


def field_stints(tables: dict) -> list[dict]:
    """Index retained native pace and lap-end availability by driver/stint/age."""
    native = {(r["driver_number"], r["lap_number"]): r for r in tables["laps"]}
    metadata = {(r["driver_number"], r["stint_number"]): r for r in tables["stints"]}
    result = []
    for driver, stints in stint_rows(tables).items():
        for stint, compound, values in stints:
            meta = metadata[(driver, stint)]
            ends = {}
            for age in values:
                lap = age-meta["tyre_age_at_start"]+meta["lap_start"]-1
                row = native[(driver, lap)]
                ends[age] = timestamp(row["date_start"])+row["lap_duration"]
            result.append({"driver": driver, "stint": stint, "compound": compound, "values": values, "ends": ends})
    return result


def context(case: dict, field: list[dict]) -> list[dict]:
    """Expose only completed matching-age windows of the current compound."""
    ages, cutoff, compound = case["ages"], case["forecast_at_s"], case["compounds"][1]
    result = []
    for row in field:
        if row["compound"] != compound or not set(ages).issubset(row["values"]):
            continue
        available = max(row["ends"][k] for k in ages)
        if available > cutoff:
            continue
        result.append({"driver": row["driver"], "stint": row["stint"], "available_at_s": available,
                       "prefix_s": float(np.median([row["values"][k] for k in ages[:3]])),
                       "target_s": float(np.median([row["values"][k] for k in ages[-3:]]))})
    return result


def vector(case: dict, extended: bool) -> list[float]:
    values = feature_vector(case)
    if extended:
        observed = case["field_context"]
        center = float(np.median(case["current_prefix_s"]))
        values += [float(bool(observed)), float(np.log1p(len(observed))),
                   float(np.median([r["target_s"]-r["prefix_s"] for r in observed])) if observed else 0.,
                   float(np.median([r["target_s"] for r in observed]))-center if observed else 0.]
    return values


def development() -> dict:
    """Inspect only the eight opened events; preserve every model/fold result."""
    cases, sources = [], {}
    for session, identity in {**TRAIN, **V5}.items():
        folder = ("r041-openf1-confirmation" if session in (9912, 9839) else
                  "r041-traffic-holdout" if session in (10014, 9971) else
                  "r041-reference-holdout" if session in (9963, 9955) else "r041-conditioned-holdout")
        tables, digest = tables_from_archive(Path(".cache")/folder, session, identity)
        rows, _ = build_cases(tables, session)
        field = field_stints(tables)
        for row in rows:
            row["field_context"] = context(row, field)
        cases.extend(rows)
        sources[str(session)] = digest
    comparisons = []
    settings = ([{"family": "ridge", "alpha": a, "extended": e} for e in (False, True) for a in (1., 10., 100.)]
                + [{"family": "forest", "leaf": leaf, "depth": depth, "extended": e}
                   for e in (False, True) for leaf in (3, 8) for depth in (3, None)])
    for setting in settings:
        folds = []
        for session in {**TRAIN, **V5}:
            training = [r for r in cases if r["session"] != session]
            validation = [r for r in cases if r["session"] == session]
            counts = Counter(window_key(r) for r in training)
            weights = [1/counts[window_key(r)] for r in training]
            x = [vector(r, setting["extended"]) for r in training]
            y = [float(np.median(r["current_target_s"])-np.median(r["current_prefix_s"])) for r in training]
            model = (Ridge(alpha=setting["alpha"], fit_intercept=False) if setting["family"] == "ridge" else
                     RandomForestRegressor(n_estimators=128, max_depth=setting["depth"],
                                           min_samples_leaf=setting["leaf"], random_state=41, n_jobs=1))
            model.fit(x, y, sample_weight=weights)
            delta = model.predict([vector(r, setting["extended"]) for r in validation])
            pred = [float(np.median(r["reference_target_s"])-np.median(r["current_prefix_s"]))-d
                    for r, d in zip(validation, delta, strict=True)]
            errors = [abs(p-r[key]) for r, p in zip(validation, pred, strict=True)
                      for key in ("actual_s", "pairwise_actual_s")]
            folds.append({"session": session, "mae_s": float(np.mean(errors))})
        comparisons.append({**setting, "folds": folds, "macro_mae_s": float(np.mean([r["mae_s"] for r in folds]))})
    return seal({"scope": "OPENED_EIGHT_EVENT_DEVELOPMENT_ONLY", "sources": sources,
                 "source_sha256": file_sha256(Path(__file__)), "comparisons": comparisons, "cases": cases})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, development())
