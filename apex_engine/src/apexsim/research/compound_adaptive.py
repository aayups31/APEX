"""R041 transparent event adaptation; completed observations are pace proxies."""
from __future__ import annotations

from collections import defaultdict
from math import isfinite
from numbers import Real
from statistics import median

from apexsim.research.compound_readiness import crossing

COMPOUNDS = ("SOFT", "MEDIUM", "HARD")


def number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"Expected finite numeric {name}")
    return float(value)


def predict_adaptive(row: dict, *, shrinkage: float = 1., minimum_drivers: int = 3,
                     bound_s: float = .5, decision_margin_s: float = .15, radius_s: float | None = None) -> dict:
    """Predict reference contrast minus a causal, equal-driver field drift.

    Other drivers only; repeated stints of one driver do not inflate support.
    Insufficient field support yields reference persistence, never case deletion.
    The event decision agrees with both prefix definitions at the chosen margin.
    """
    shrinkage, bound_s, margin = (number(v, k) for v, k in
                                ((shrinkage, "shrinkage"), (bound_s, "bound"), (decision_margin_s, "margin")))
    if (not 0 <= shrinkage <= 1 or bound_s < 0 or margin < .15
            or type(minimum_drivers) is not int or minimum_drivers < 1):
        raise ValueError("Invalid adaptive forecast configuration")
    if radius_s is not None and number(radius_s, "radius") < 0:
        raise ValueError("Negative adaptive error radius")
    ages = [number(a, "tyre age") for a in row["ages"]]
    if len(ages) != 12 or ages[0] <= 0 or any(a != ages[0]+i or a % 1 for i, a in enumerate(ages)):
        raise ValueError("Expected twelve consecutive positive integer ages")
    compounds = row["compounds"]
    if len(compounds) != 2 or any(c not in COMPOUNDS for c in compounds) or compounds[0] == compounds[1]:
        raise ValueError("Invalid reference/current compound pair")
    cutoff = number(row["forecast_at_s"], "forecast clock")
    if number(row["reference_end_s"], "reference clock") > cutoff:
        raise ValueError("Reference unavailable at forecast time")
    values = []
    for key in ("reference_target_s", "current_prefix_s"):
        sample = [number(v, key) for v in row[key]]
        if len(sample) != 3 or min(sample) <= 0:
            raise ValueError("Expected three positive lap times")
        values.append(sample)
    reference = median(values[0])-median(values[1])
    prefixes = [number(row[k], k) for k in ("prefix_s", "pairwise_prefix_s")]
    by_driver, seen, excluded_self = defaultdict(list), set(), 0
    for item in row.get("context", {}).get("field_windows", []):
        key = item["driver"], item["stint"]
        if key in seen:
            raise ValueError("Duplicate adaptive field contributor")
        seen.add(key)
        if number(item["available_at_s"], "field clock") > cutoff:
            raise ValueError("Field observation unavailable at forecast time")
        change = number(item["change_s"], "field change")
        if str(item["driver"]) == str(row["driver"]):
            excluded_self += 1
        else:
            by_driver[str(item["driver"])].append(change)
    centers = [median(v) for v in by_driver.values()]
    fallback = len(centers) < minimum_drivers and shrinkage > 0
    drift = median(centers) if centers else None
    if drift is not None and not isfinite(drift):
        raise ValueError("Nonfinite adaptive field aggregation")
    raw = 0. if fallback or not shrinkage else -shrinkage*drift
    correction = min(bound_s, max(-bound_s, raw))
    predicted = reference+correction
    outputs = [reference, raw, correction, predicted]
    if radius_s is not None:
        outputs += [predicted-radius_s, predicted+radius_s]
    if not all(isfinite(v) for v in outputs):
        raise ValueError("Nonfinite adaptive forecast arithmetic")
    return {"predicted_s": predicted, "reference_persistence_s": reference, "raw_correction_s": raw,
            "applied_correction_s": correction, "correction_bounded": abs(raw) > bound_s,
            "fallback": fallback, "fallback_reasons": ["INSUFFICIENT_OTHER_DRIVER_SUPPORT"] if fallback else [],
            "field_drivers": len(centers), "excluded_self_windows": excluded_self, "field_drift_s": drift,
            "predicted_crossover": all(crossing(p, predicted, margin) for p in prefixes),
            "lower_s": predicted-radius_s if radius_s is not None else None,
            "upper_s": predicted+radius_s if radius_s is not None else None,
            "truth": "FUEL_CORRECTED_PACE_PROXY_NOT_PHYSICAL_WEAR"}
