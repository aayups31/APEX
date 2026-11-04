"""R041 matched short-horizon cohort and causal pace-proxy baselines."""
from __future__ import annotations

from collections import Counter
from itertools import combinations, groupby

import numpy as np
from confirm_compound_crossover import stint_rows, timestamp

COMPOUNDS = ("SOFT", "MEDIUM", "HARD")


def build_cases(tables: dict, session: int, horizon: int) -> tuple[list[dict], dict]:
    """Keep disjoint age windows, completed reference times and future labels apart."""
    if horizon not in (3, 6, 9):
        raise ValueError("Unsupported research horizon")
    native = {(r["driver_number"], r["lap_number"]): r for r in tables["laps"]}
    if len(native) != len(tables["laps"]):
        raise ValueError("Duplicate native driver/lap")
    meta = {(r["driver_number"], r["stint_number"]): r for r in tables["stints"]}

    def end(driver, stint, age):
        m = meta[(driver, stint)]
        r = native[(driver, age-m["tyre_age_at_start"]+m["lap_start"]-1)]
        return timestamp(r["date_start"])+r["lap_duration"]

    cases, unsupported, unavailable = [], 0, 0
    for driver, stints in sorted(stint_rows(tables).items()):
        for (i, a, x), (j, b, y) in combinations(sorted(stints), 2):
            if a == b:
                continue
            count, width = 0, horizon+3
            for _, group in groupby(enumerate(sorted(x.keys() & y.keys())), lambda row: row[1]-row[0]):
                ages = [age for _, age in group]
                for offset in range(0, len(ages)-width+1, width):
                    block = ages[offset:offset+width]
                    first, last = block[:3], block[-3:]
                    reference_end = max(end(driver, i, k) for k in first+last)
                    forecast_at = max(end(driver, j, k) for k in first)
                    if reference_end > forecast_at:
                        unavailable += 1
                        continue
                    xp, yp, xt, yt = ([v[k] for k in window] for v, window in
                                      ((x, first), (y, first), (x, last), (y, last)))
                    cases.append({"session": session, "driver": driver, "stints": [i, j],
                                  "compounds": [a, b], "ages": block, "horizon_laps": horizon,
                                  "reference_target_s": xt, "current_prefix_s": yp, "current_target_s": yt,
                                  "reference_end_s": reference_end, "forecast_at_s": forecast_at,
                                  "prefix_s": float(np.median(xp)-np.median(yp)),
                                  "actual_s": float(np.median(xt)-np.median(yt)),
                                  "pairwise_prefix_s": float(np.median(np.asarray(xp)-yp)),
                                  "pairwise_actual_s": float(np.median(np.asarray(xt)-yt))})
                    count += 1
            unsupported += count == 0
    return cases, {"unsupported_pairs": unsupported, "unavailable_reference_blocks": unavailable}


def vector(row: dict) -> list[float]:
    """Six forecast-time covariates with local slope in horizon-matched seconds."""
    prefix = row["current_prefix_s"]
    return [float(row["compounds"][1] == c) for c in COMPOUNDS]+[
        float(np.median(row["reference_target_s"])-np.median(prefix)-row["prefix_s"]),
        row["horizon_laps"]*.5*(prefix[2]-prefix[0]), row["prefix_s"]]


def fit(rows: list[dict], kind: str, alpha: float = 10.) -> dict:
    """Fit signed current-stint drift without duplicated target-window influence."""
    counts = Counter((r["session"], r["driver"], r["stints"][1], tuple(r["ages"])) for r in rows)
    weights = np.asarray([1/counts[(r["session"], r["driver"], r["stints"][1], tuple(r["ages"]))] for r in rows])
    y = np.asarray([float(np.median(r["current_target_s"])-np.median(r["current_prefix_s"])) for r in rows])
    if kind == "ridge":
        x = np.asarray([vector(r) for r in rows])
        beta = np.linalg.solve(x.T@(weights[:, None]*x)+alpha*np.eye(6), x.T@(weights*y))
        model = {"kind": kind, "alpha": alpha, "coefficients": beta.tolist()}
    else:
        changes = {}
        for c in COMPOUNDS:
            values = {tuple([r["session"], r["driver"], r["stints"][1], *r["ages"]]): y[i]
                      for i, r in enumerate(rows) if r["compounds"][1] == c}
            if len(values) < 3:
                raise ValueError("Insufficient short-horizon compound support")
            changes[c] = float(np.median(list(values.values()))) if kind == "median" else 0.
        model = {"kind": kind, "changes": changes}
    return model


def predict(model: dict, row: dict) -> float:
    """Forecast from a completed earlier curve and the current prefix only."""
    if row["reference_end_s"] > row["forecast_at_s"]:
        raise ValueError("Reference unavailable at forecast time")
    delta = (float(np.asarray(vector(row))@model["coefficients"]) if model["kind"] == "ridge"
             else model["changes"][row["compounds"][1]])
    return float(np.median(row["reference_target_s"])-np.median(row["current_prefix_s"]))-delta
