"""Independent scalar audit of sealed R041 nested forecasts and reported gates.

Does not import candidate feature, prediction, fit, selection or metric code.
Scope is all nested forecasts from sealed development cases, not independent
native-cohort enumeration or refitting of the inner training procedure.
"""
from __future__ import annotations

import argparse
from math import ceil, exp, isclose, isfinite, log1p, sqrt
from pathlib import Path
from statistics import mean, median

from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal

COMPOUNDS = ("SOFT", "MEDIUM", "HARD")
BASELINES = ("reference", "contrast", "midpoint")
LABELS = (("prefix_s", "actual_s"), ("pairwise_prefix_s", "pairwise_actual_s"))


def close(actual: float, expected: float, field: str) -> None:
    if not isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError(f"Independent bounded audit mismatch: {field}")


def crossing(start: float, end: float) -> bool:
    return start*end < 0 and min(abs(start), abs(end)) > .15


def scalar_forecast(model: dict, event_model: dict, row: dict) -> dict:
    if row["reference_end_s"] > row["forecast_at_s"]:
        raise ValueError("Independent audit future reference")
    current = row["compounds"][1]
    prefix = row["current_prefix_s"]
    reference = median(row["reference_target_s"])-median(prefix)
    start = row["prefix_s"]
    features = [float(current == c) for c in COMPOUNDS]+[
        reference-start, 4.5*(prefix[2]-prefix[0]), start]
    event_features = features+[
        abs(start), start*reference, float(crossing(start, reference)), abs(row["pairwise_prefix_s"])]
    if model["feature_group"] == "context":
        ctx = row.get("context", {})
        time, temperature, change = (ctx.get(k) for k in ("weather_at_s", "track_temperature_c", "track_change_c"))
        if (time is not None and not 0 <= row["forecast_at_s"]-time <= 120.
                or time is None and (temperature is not None or change is not None)):
            raise ValueError("Independent audit invalid weather availability")
        windows = ctx.get("field_windows", [])
        if any(w["available_at_s"] > row["forecast_at_s"] for w in windows):
            raise ValueError("Independent audit future field context")
        age = row["ages"][0]
        features += [age, *[float(age*(current == c)) for c in COMPOUNDS],
                     float(temperature is not None), temperature if temperature is not None else 0.,
                     float(change is not None), change if change is not None else 0.,
                     float(bool(windows)), log1p(len(windows)), median([w["change_s"] for w in windows]) if windows else 0.]
    if not all(isfinite(x) for x in features):
        raise ValueError("Independent audit nonfinite features")
    raw = model["coefficients"][0]+sum((x-m)/s*b for x, m, s, b in
        zip(features, model["mean"], model["scale"], model["coefficients"][1:], strict=True))
    support = model["support"][current]
    reasons = []
    if support["events"] < 3:
        reasons.append("FEWER_THAN_THREE_COMPOUND_EVENTS")
    elif any(x < lo-1e-10 or x > hi+1e-10 for x, lo, hi in
             zip(features, support["minimum"], support["maximum"], strict=True)):
        reasons.append("OUTSIDE_TRAINING_FEATURE_RANGE")
    baseline = {"reference": reference, "contrast": start, "midpoint": .5*(reference+start)}[model["baseline"]]
    correction = 0. if reasons else min(model["bound_s"], max(-model["bound_s"], raw))
    prediction, radius = baseline+correction, model["radius_s"]
    logit = event_model["intercept"]+sum((x-m)/s*b for x, m, s, b in
        zip(event_features, event_model["mean"], event_model["scale"], event_model["coefficients"], strict=True))
    score = 1/(1+exp(-logit)) if logit >= 0 else exp(logit)/(1+exp(logit))
    return {"predicted_s": prediction, "baseline_s": baseline, "raw_correction_s": raw,
            "applied_correction_s": correction, "reference_persistence_s": reference,
            "lower_s": prediction-radius, "upper_s": prediction+radius, "fallback": bool(reasons),
            "fallback_reasons": reasons, "correction_bounded": not reasons and abs(raw) > model["bound_s"],
            "crossover_score": score, "predicted_crossover": score >= event_model["threshold"]}


def audit(data: dict, results: dict) -> dict:
    for document in (data, results):
        check_seal(document)
    if (results["dataset_sha256"] != data["content_sha256"]
            or results["implementation_sha256_lf"] != data["implementation_sha256_lf"]):
        raise ValueError("Independent audit source/data binding mismatch")
    def key(row: dict) -> tuple:
        return str(row["session"]), row["driver"], tuple(row["stints"]), tuple(row["ages"])
    original = {key(r): r for r in data["cases"]}
    published = {key(r): r for r in results["nested_predictions"]}
    if (len(original) != len(data["cases"]) or len(published) != len(results["nested_predictions"])
            or set(original) != set(published)):
        raise ValueError("Independent audit missing or duplicated nested cases")
    events = {r["session"] for r in original.values()}
    folds = results["outer_folds"]
    if len(folds) != len(events) or {f["event"] for f in folds} != events:
        raise ValueError("Independent audit missing or duplicated outer event")
    reconstructed, labels_by_event = [], []
    for fold in folds:
        if set(fold["training_events"]) != events-{fold["event"]}:
            raise ValueError("Independent audit outer training overlap or omission")
        errors = sorted(fold["inner_cv_errors_s"])
        radius = errors[min(len(errors), ceil((len(errors)+1)*.9))-1]
        close(fold["radius_s"], radius, "cross-event radius")
        close(fold["pace_head"]["radius_s"], radius, "model radius")
        chosen = min(fold["inner_grid"], key=lambda g: (g["macro_mae_s"], g["setting"]["bound_s"],
                     g["setting"]["group"] != "pace", -g["setting"]["alpha"], BASELINES.index(g["setting"]["baseline"])))
        event_choice = min(fold["inner_event_grid"], key=lambda g: (-g["selection_score"], g["c"], abs(g["threshold"]-.5)))
        if (chosen["setting"] != fold["setting"] or event_choice["c"] != fold["event_head"]["c"]
                or event_choice["threshold"] != fold["event_head"]["threshold"]):
            raise ValueError("Independent audit inner selection mismatch")
        rows = [r for r in original.values() if r["session"] == fold["event"]]
        predictions = []
        for row in rows:
            p = scalar_forecast(fold["pace_head"], fold["event_head_parameters"], row)
            case = published[key(row)]
            if any(case.get(k) != v for k, v in row.items()):
                raise ValueError("Independent audit changed source case or context")
            for field, value in p.items():
                if isinstance(value, (bool, list)):
                    if case[field] != value:
                        raise ValueError(f"Independent bounded audit mismatch: {field}")
                else:
                    close(case[field], value, field)
            predictions.append({**row, **p})
        reconstructed.extend(predictions)
        labels, counts, gates = [], [], []
        for index, (prefix, target) in enumerate(LABELS):
            residuals = [p["predicted_s"]-p[target] for p in predictions]
            observed = sum(crossing(p[prefix], p[target]) for p in predictions)
            predicted = sum(p["predicted_crossover"] for p in predictions)
            matched = sum(crossing(p[prefix], p[target]) and p["predicted_crossover"] for p in predictions)
            metric = {"mae_s": mean(abs(e) for e in residuals), "rmse_s": sqrt(mean(e*e for e in residuals)),
                      "reference_mae_s": mean(abs(p["reference_persistence_s"]-p[target]) for p in predictions),
                      "contrast_mae_s": mean(abs(p[prefix]-p[target]) for p in predictions),
                      "coverage": mean(p["lower_s"] <= p[target] <= p["upper_s"] for p in predictions),
                      "mean_width_s": 2*radius}
            for field, value in metric.items():
                close(fold["pace"][index][field], value, "pace/"+field)
            count = {"observed": observed, "predicted": predicted, "matched": matched,
                     "recall": matched/observed if observed else None,
                     "precision": matched/predicted if predicted else None,
                     "min_precision_recall": matched/max(observed, predicted, 1)}
            for field, value in count.items():
                if value is None:
                    if fold["events"][index][field] is not None:
                        raise ValueError("Independent audit undefined event rate")
                else:
                    close(fold["events"][index][field], value, "events/"+field)
            gate = observed > 0 and predicted > 0 and count["min_precision_recall"] >= .5 and metric["mae_s"] <= min(metric["reference_mae_s"], metric["contrast_mae_s"])
            gates.append(gate)
            labels.append(metric)
            counts.append(count)
        for field, value in (("cases", len(rows)), ("fallback_cases", sum(p["fallback"] for p in predictions)),
                             ("bounded_cases", sum(p["correction_bounded"] for p in predictions))):
            close(fold[field], value, field)
        if gates != fold["passed_labels"]:
            raise ValueError("Independent audit per-event acceptance mismatch")
        labels_by_event.append(labels)
    macro = [{field: mean(labels[index][field] for labels in labels_by_event)
              for field in results["nested_macro_pace"][index]} for index in (0, 1)]
    pooled = []
    for index, (prefix, target) in enumerate(LABELS):
        for field, value in macro[index].items():
            close(results["nested_macro_pace"][index][field], value, "macro/"+field)
        observed = sum(crossing(p[prefix], p[target]) for p in reconstructed)
        predicted = sum(p["predicted_crossover"] for p in reconstructed)
        matched = sum(crossing(p[prefix], p[target]) and p["predicted_crossover"] for p in reconstructed)
        count = {"observed": observed, "predicted": predicted, "matched": matched,
                 "recall": matched/observed if observed else None,
                 "precision": matched/predicted if predicted else None,
                 "min_precision_recall": matched/max(observed, predicted, 1)}
        for field, value in count.items():
            if value is None:
                if results["nested_pooled_events"][index][field] is not None:
                    raise ValueError("Independent audit invalid pooled zero support")
            else:
                close(results["nested_pooled_events"][index][field], value, "pooled/"+field)
        pooled.append(count)
    qualified = (all(m["mae_s"] <= min(m["reference_mae_s"], m["contrast_mae_s"]) for m in macro)
                 and all(p["min_precision_recall"] >= .5 for p in pooled))
    if results["development_qualified"] != qualified or results["candidate_accepted"] or results["production_promotion"]:
        raise ValueError("Independent audit invalid development/acceptance disposition")
    return seal({"schema_version": "apex-compound-bounded-scalar-audit-v9", "results_sha256": results["content_sha256"],
                 "dataset_sha256": data["content_sha256"], "audit_source_sha256": file_sha256(Path(__file__)),
                 "cases_audited": len(reconstructed), "events_audited": len(events), "audit_passed": True,
                 "development_qualified": qualified, "candidate_accepted": False,
                 "scope": "ALL_NESTED_FORECASTS_AND_SUMMARIES_NOT_NATIVE_COHORT_OR_INNER_REFIT"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("dataset", "results", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, audit(read_json(args.dataset), read_json(args.results)))
