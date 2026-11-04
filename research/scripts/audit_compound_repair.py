"""Independent scalar reconstruction of every R041 v10 setting and nested gate."""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
from math import ceil, isclose
from pathlib import Path
from statistics import mean, median

from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal

LABELS = (("prefix_s", "actual_s"), ("pairwise_prefix_s", "pairwise_actual_s"))


def crossing(a: float, b: float, margin: float = .15) -> bool:
    return a < -margin and b > margin or a > margin and b < -margin


def scalar(row: dict, config: dict, radius: float | None = None) -> dict:
    if row["reference_end_s"] > row["forecast_at_s"]:
        raise ValueError("Independent repair audit future reference")
    drivers, identities, own = defaultdict(list), set(), 0
    for w in row["context"]["field_windows"]:
        if w["available_at_s"] > row["forecast_at_s"]:
            raise ValueError("Independent repair audit future field")
        key = w["driver"], w["stint"]
        if key in identities:
            raise ValueError("Independent repair audit duplicate field window")
        identities.add(key)
        if str(w["driver"]) == str(row["driver"]):
            own += 1
        else:
            drivers[str(w["driver"])].append(w["change_s"])
    drift = median([median(v) for v in drivers.values()]) if drivers else None
    fallback = len(drivers) < config["minimum_drivers"] and config["shrinkage"] > 0
    raw = -config["shrinkage"]*drift if not fallback and config["shrinkage"] else 0.
    correction = max(-config["bound_s"], min(config["bound_s"], raw))
    reference = median(row["reference_target_s"])-median(row["current_prefix_s"])
    value = reference+correction
    return {"predicted_s": value, "reference_persistence_s": reference, "raw_correction_s": raw,
            "applied_correction_s": correction, "correction_bounded": abs(raw) > config["bound_s"],
            "fallback": fallback, "fallback_reasons": ["INSUFFICIENT_OTHER_DRIVER_SUPPORT"] if fallback else [],
            "field_drivers": len(drivers), "excluded_self_windows": own, "field_drift_s": drift,
            "predicted_crossover": all(crossing(row[p], value, config["decision_margin_s"]) for p, _ in LABELS),
            "lower_s": value-radius if radius is not None else None, "upper_s": value+radius if radius is not None else None,
            "truth": "FUEL_CORRECTED_PACE_PROXY_NOT_PHYSICAL_WEAR"}


def event_report(rows: list[dict]) -> dict:
    if not rows:
        return {"cases": 0, "labels": [], "passed": False, "informative": False, "failure_codes": ["NO_ELIGIBLE_COMPARISONS"]}
    labels = []
    for prefix, target in LABELS:
        observed = sum(crossing(r[prefix], r[target]) for r in rows)
        predicted = sum(r["predicted_crossover"] for r in rows)
        matched = sum(crossing(r[prefix], r[target]) and r["predicted_crossover"] for r in rows)
        mae = mean(abs(r["predicted_s"]-r[target]) for r in rows)
        reference = mean(abs(r["reference_persistence_s"]-r[target]) for r in rows)
        contrast = mean(abs(r[prefix]-r[target]) for r in rows)
        failures = []
        if mae > reference+1e-12:
            failures.append("PACE_WORSE_THAN_REFERENCE")
        if mae > contrast+1e-12:
            failures.append("PACE_WORSE_THAN_CONTRAST")
        if observed:
            if 2*matched < observed:
                failures.append("CROSSOVER_RECALL_BELOW_HALF")
            if not predicted or 2*matched < predicted:
                failures.append("CROSSOVER_PRECISION_BELOW_HALF")
        elif predicted:
            failures.append("FALSE_ALARM_ON_NEGATIVE_CONTROL")
        labels.append({"prefix": prefix, "target": target, "observed": observed, "predicted": predicted,
                       "matched": matched, "mae_s": mae, "reference_mae_s": reference, "contrast_mae_s": contrast,
                       "recall": matched/observed if observed else None, "precision": matched/predicted if predicted else None,
                       "failure_codes": failures, "passed": not failures})
    return {"cases": len(rows), "labels": labels, "passed": all(m["passed"] for m in labels),
            "informative": all(m["observed"] for m in labels),
            "failure_codes": sorted({code for m in labels for code in m["failure_codes"]}),
            "fallback_cases": sum(bool(r.get("fallback")) for r in rows)}


def panel(rows: list[dict], events: list) -> dict:
    folds = [{"event": str(e), **event_report([r for r in rows if str(r["session"]) == str(e)])} for e in events]
    supported = [f for f in folds if f["cases"]]
    informative = [f["event"] for f in supported if f["informative"]]
    failed = [f["event"] for f in supported if not f["passed"]]
    ready = len(informative) >= 2 and not failed
    return {"events": folds, "supported_events": len(supported), "informative_events": informative,
            "unsupported_events": [f["event"] for f in folds if not f["cases"]], "failed_supported_events": failed,
            "required_informative_events": 2, "development_qualified": ready,
            "new_holdout_acquisition_allowed": ready, "production_promotion": False}


def summary(predictions: list[dict], setting: dict, events: list) -> dict:
    report = panel(predictions, events)
    labels = [m for f in report["events"] for m in f["labels"]]
    return {"setting": setting, "failed_event_labels": sum(not m["passed"] for m in labels),
            "negative_control_false_alarms": sum(m["predicted"] for m in labels if not m["observed"]),
            "macro_mae_s": mean(m["mae_s"] for m in labels), "folds": report["events"], "readiness": report}


def choice(item: dict) -> tuple:
    setting = item["setting"]
    return (item["failed_event_labels"], item["negative_control_false_alarms"], item["macro_mae_s"],
            setting["shrinkage"], -setting["minimum_drivers"], setting["decision_margin_s"])


def compare(actual: object, expected: object, path: str = "root") -> None:
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ValueError(f"Independent repair keys mismatch: {path}")
        for key in expected:
            compare(actual[key], expected[key], path+"/"+key)
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            raise ValueError(f"Independent repair denominator mismatch: {path}")
        for i, (a, b) in enumerate(zip(actual, expected, strict=True)):
            compare(a, b, path+f"/{i}")
    elif isinstance(expected, float):
        if not isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError(f"Independent repair numeric mismatch: {path}")
    elif actual != expected:
        raise ValueError(f"Independent repair value mismatch: {path}")


def audit(data: dict, result: dict) -> dict:
    for item in (data, result):
        check_seal(item)
    if result["dataset_sha256"] != data["content_sha256"]:
        raise ValueError("Independent repair data binding mismatch")
    root = Path(__file__).resolve().parents[2]
    for name, digest in result["hashes"].items():
        if sha256((root/name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != digest:
            raise ValueError("Independent repair implementation binding mismatch")
    rows = data["cases"]
    events = list(dict.fromkeys(r["session"] for r in rows))
    scalar_settings, full_grid = [], []
    for entry in result["grid"]:
        predictions = [{**r, **scalar(r, entry["setting"])} for r in rows]
        expected = summary(predictions, entry["setting"], events)
        compare(entry, expected, "full_grid")
        scalar_settings.append(predictions)
        full_grid.append(expected)
    compare(result["selected_setting"], min(full_grid, key=choice)["setting"], "selected_setting")
    if len(result["nested_selections"]) != len(events):
        raise ValueError("Independent repair outer-event denominator mismatch")
    nested = []
    for outer, selection in zip(events, result["nested_selections"], strict=True):
        inner_events = [e for e in events if e != outer]
        inner_grid = [summary([r for r in ps if r["session"] != outer], item["setting"], inner_events)
                      for item, ps in zip(full_grid, scalar_settings, strict=True)]
        compare(selection["inner_grid"], inner_grid, "inner_grid")
        chosen = min(range(len(inner_grid)), key=lambda i: choice(inner_grid[i]))
        errors = sorted(max(abs(r["predicted_s"]-r[t]) for _, t in LABELS) for r in scalar_settings[chosen] if r["session"] != outer)
        radius = errors[min(len(errors), ceil((len(errors)+1)*.9))-1]
        test = [{**r, **scalar(r, full_grid[chosen]["setting"], radius)} for r in rows if r["session"] == outer]
        compare(selection, {"outer_event": str(outer), "setting": full_grid[chosen]["setting"], "radius_s": radius,
                            "training_events": [str(e) for e in inner_events], "inner_grid": inner_grid,
                            "outer_metrics": event_report(test)}, "outer_selection")
        nested.extend(test)
    compare(result["nested_predictions"], nested, "nested_predictions")
    readiness = panel(nested, sorted(data.get("sources", dict.fromkeys(str(e) for e in events))))
    compare(result["readiness"], readiness, "readiness")
    if result["candidate_accepted"] or result["production_promotion"]:
        raise ValueError("Independent repair development cannot promote or accept a candidate")
    return seal({"schema_version": "apex-compound-repair-scalar-audit-v10", "dataset_sha256": data["content_sha256"],
                 "result_sha256": result["content_sha256"], "audit_source_sha256": file_sha256(Path(__file__)),
                 "settings_audited": len(full_grid), "outer_events_audited": len(events), "cases_audited": len(nested),
                 "audit_passed": True, "development_qualified": readiness["development_qualified"], "candidate_accepted": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("dataset", "results", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, audit(read_json(args.dataset), read_json(args.results)))
