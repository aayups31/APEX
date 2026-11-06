"""R041 v12: score both definitions using the same forecast of three lap times."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from statistics import median

from apexsim.provenance import write_manifest
from apexsim.research.compound_readiness import LABELS, assess_event, crossing
from apexsim.research.evidence import check_seal, read_json, seal

ROOT = Path(__file__).resolve().parents[2]


def contrasts(reference: list, current: list) -> tuple[float, float]:
    """Difference of medians and median of paired differences, in seconds."""
    if len(reference) != 3 or len(current) != 3:
        raise ValueError("Both windows require three age-matched laps")
    return median(reference) - median(current), median(
        a - b for a, b in zip(reference, current, strict=True)
    )


def calibration(rows: list[dict], held_event: str, compound: str) -> tuple[float, int]:
    """Each race and each unique current window contribute once."""
    changes = defaultdict(dict)
    for row in rows:
        event = str(row["session"])
        if event == held_event or row["compounds"][1] != compound:
            continue
        key = row["driver"], row["stints"][1], tuple(row["ages"])
        delta = median(row["current_target_s"]) - median(row["current_prefix_s"])
        if key in changes[event] and changes[event][key] != delta:
            raise ValueError("Conflicting current window")
        changes[event][key] = delta
    if len(changes) < 3:
        return 0.0, len(changes)
    raw = median(median(group.values()) for group in changes.values())
    return min(2.0, max(-2.0, raw)), len(changes)


def study(data: dict) -> dict:
    check_seal(data)
    rows = data["cases"]
    predictions, folds, contradictions = [], [], []
    for event in sorted(data["sources"]):
        cases = [r for r in rows if str(r["session"]) == event]
        if len(cases) != data["sources"][event]["blocks"]:
            raise ValueError("Source support mismatch")
        observed = [sum(crossing(r[p], r[t]) for r in cases) for p, t in LABELS]
        if min(observed) == 0 and max(observed) > 0:
            contradictions.append(
                {"event": event, "observed": observed, "cases": len(cases)}
            )
        fold = {"event": event, "cases": len(cases)}
        for method in ("candidate", "persistence", "oracle"):
            scored = [[], []]
            for row in cases:
                if row["reference_end_s"] > row["forecast_at_s"]:
                    raise ValueError("Reference unavailable")
                drift, support = (
                    calibration(rows, event, row["compounds"][1])
                    if method == "candidate"
                    else (0.0, None)
                )
                current = (
                    [p + drift for p in row["current_prefix_s"]]
                    if method != "oracle"
                    else row["current_target_s"]
                )
                values = contrasts(row["reference_target_s"], current)
                baseline = contrasts(row["reference_target_s"], row["current_prefix_s"])
                decisions = []
                for i, (prefix, target) in enumerate(LABELS):
                    decision = crossing(row[prefix], values[i])
                    decisions.append(decision)
                    if method == "oracle" and abs(values[i] - row[target]) > 1e-12:
                        raise ValueError("Oracle failed to reconstruct native target")
                    scored[i].append(
                        {
                            "prefix_s": row[prefix],
                            "pairwise_prefix_s": row[prefix],
                            "actual_s": row[target],
                            "pairwise_actual_s": row[target],
                            "reference_persistence_s": baseline[0],
                            "predicted_s": values[i],
                            "predicted_crossover": decision,
                            "own_baseline_error_s": abs(row[target] - baseline[i]),
                        }
                    )
                if method == "candidate":
                    predictions.append(
                        {
                            "event": event,
                            "driver": row["driver"],
                            "stints": row["stints"],
                            "ages": row["ages"],
                            "drift_s": drift,
                            "training_races": support,
                            "fallback": support < 3,
                            "forecast_laps_s": current,
                            "contrasts_s": values,
                            "crossings": decisions,
                        }
                    )
            metrics = []
            for i, items in enumerate(scored):
                if items:
                    m = assess_event(items)["labels"][0]
                    m["prefix"], m["target"] = LABELS[i]
                    m["label_reference_mae_s"] = sum(
                        r["own_baseline_error_s"] for r in items
                    ) / len(items)
                    if m["mae_s"] > m["label_reference_mae_s"] + 1e-12:
                        m["failure_codes"].append("PACE_WORSE_THAN_LABEL_REFERENCE")
                        m["passed"] = False
                    metrics.append(m)
            fold[method] = metrics
        folds.append(fold)
    supported = [f for f in folds if f["cases"]]
    informative = sum(all(m["observed"] for m in f["candidate"]) for f in supported)
    failures = [
        f["event"] for f in supported if not all(m["passed"] for m in f["candidate"])
    ]
    if any(not m["passed"] for f in supported for m in f["oracle"]):
        raise ValueError(
            "Corrected contract failed the perfect-forecast feasibility check"
        )
    qualified = not failures and informative >= 2
    return seal(
        {
            "schema": "compound-decision-feasibility-v12",
            "dataset_sha256": data["content_sha256"],
            "impossible_shared_decision_events": contradictions,
            "informative_events": informative,
            "events": folds,
            "predictions": predictions,
            "failed_supported_events": failures,
            "oracle_is_diagnostic_only": True,
            "development_qualified": qualified,
            "new_holdout_acquisition_allowed": qualified,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    write_manifest(
        args.output,
        study(read_json(ROOT / "docs/verification/compound-v10-development-data.json")),
    )
