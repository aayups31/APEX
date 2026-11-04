"""R041 event-level readiness gates; pooled success cannot hide failed races."""
from __future__ import annotations

from collections import defaultdict
from math import isfinite
from statistics import mean

LABELS = (("prefix_s", "actual_s"), ("pairwise_prefix_s", "pairwise_actual_s"))


def crossing(start: float, end: float, margin_s: float = .15) -> bool:
    return (start < -margin_s and end > margin_s) or (start > margin_s and end < -margin_s)


def assess_event(rows: list[dict]) -> dict:
    """Keep every case/fallback in both baseline and event denominators."""
    if not rows:
        return {"cases": 0, "labels": [], "passed": False, "informative": False,
                "failure_codes": ["NO_ELIGIBLE_COMPARISONS"]}
    labels, codes = [], []
    for prefix, target in LABELS:
        try:
            invalid = any(not all(isfinite(r[k]) for k in (prefix, target, "predicted_s", "reference_persistence_s"))
                          or type(r["predicted_crossover"]) is not bool for r in rows)
        except (TypeError, OverflowError) as error:
            raise ValueError("Invalid numeric R041 metric input") from error
        if invalid:
            raise ValueError("Invalid finite R041 metric input or event decision")
        observed = [crossing(r[prefix], r[target]) for r in rows]
        count = sum(observed)
        predicted = sum(r["predicted_crossover"] for r in rows)
        matched = sum(a and r["predicted_crossover"] for a, r in zip(observed, rows, strict=True))
        mae = mean(abs(r["predicted_s"]-r[target]) for r in rows)
        reference = mean(abs(r["reference_persistence_s"]-r[target]) for r in rows)
        contrast = mean(abs(r[prefix]-r[target]) for r in rows)
        if not all(isfinite(v) for v in (mae, reference, contrast)):
            raise ValueError("Nonfinite R041 error arithmetic")
        failures = []
        if mae > reference+1e-12:
            failures.append("PACE_WORSE_THAN_REFERENCE")
        if mae > contrast+1e-12:
            failures.append("PACE_WORSE_THAN_CONTRAST")
        if count:
            if 2*matched < count:
                failures.append("CROSSOVER_RECALL_BELOW_HALF")
            if not predicted or 2*matched < predicted:
                failures.append("CROSSOVER_PRECISION_BELOW_HALF")
        elif predicted:
            failures.append("FALSE_ALARM_ON_NEGATIVE_CONTROL")
        labels.append({"prefix": prefix, "target": target, "observed": count, "predicted": predicted,
                       "matched": matched, "mae_s": mae, "reference_mae_s": reference, "contrast_mae_s": contrast,
                       "recall": matched/count if count else None, "precision": matched/predicted if predicted else None,
                       "failure_codes": failures, "passed": not failures})
        codes.extend(failures)
    return {"cases": len(rows), "labels": labels, "passed": all(r["passed"] for r in labels),
            "informative": all(r["observed"] for r in labels), "failure_codes": sorted(set(codes)),
            "fallback_cases": sum(bool(r.get("fallback")) for r in rows)}


def assess_panel(rows: list[dict], source_events: list[str | int]) -> dict:
    """Require two informative races and every supported event/label to pass."""
    keys = [str(e) for e in source_events]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate source event identity")
    groups = defaultdict(list)
    seen = set()
    for row in rows:
        event = str(row["session"])
        if event not in keys:
            raise ValueError("Forecast event missing from source inventory")
        key = event, row["driver"], tuple(row["stints"]), tuple(row["ages"])
        if key in seen:
            raise ValueError("Duplicate comparison in readiness denominator")
        seen.add(key)
        groups[event].append(row)
    events = [{"event": e, **assess_event(groups[e])} for e in keys]
    supported = [e for e in events if e["cases"]]
    informative = [e["event"] for e in supported if e["informative"]]
    failed = [e["event"] for e in supported if not e["passed"]]
    qualified = len(informative) >= 2 and not failed
    return {"events": events, "supported_events": len(supported), "informative_events": informative,
            "unsupported_events": [e["event"] for e in events if not e["cases"]], "failed_supported_events": failed,
            "required_informative_events": 2, "development_qualified": qualified,
            "new_holdout_acquisition_allowed": qualified, "production_promotion": False}
