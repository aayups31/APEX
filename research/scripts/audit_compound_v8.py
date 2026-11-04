"""Independently audit R041 native labels, timing, both forecast heads and gates.

Uses statistics and scalar arithmetic rather than the candidate's preprocessing,
feature, regression, prediction or metric functions. Audits every published case;
it is not an independent reconstruction of the full eligibility denominator.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from math import exp, isclose, sqrt
from pathlib import Path
from statistics import mean, median

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal

EVENTS = {10033: (6, 1259), 9987: (7, 1260)}
COMPOUNDS = ("SOFT", "MEDIUM", "HARD")


def close(actual: float, expected: float, name: str) -> None:
    if not isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10):
        raise ValueError(f"Independent reference audit mismatch: {name}")


def crossover(a: float, b: float) -> bool:
    return a*b < 0 and min(abs(a), abs(b)) > .15


def audit(frozen: dict, results: dict, root: Path) -> dict:
    """Audit source integrity and all case/aggregate claims without candidate code."""
    for document in (frozen, results):
        check_seal(document)
    if results["calibration_sha256"] != frozen["content_sha256"]:
        raise ValueError("Audit calibration/result binding mismatch")
    manifest = read_json(root/"manifest.json")
    check_seal(manifest)
    if set(results["sources"]) != {str(s) for s in EVENTS}:
        raise ValueError("Audit confirmation session mismatch")
    if (len(results["metrics"]) != len(EVENTS)
            or {m["session"] for m in results["metrics"]} != set(EVENTS)):
        raise ValueError("Audit event metrics missing or duplicated")
    records, seen = {}, set()
    for session, (round_number, meeting) in EVENTS.items():
        assert_development_event(2025, round_number)
        if results["sources"][str(session)] != manifest["content_sha256"]:
            raise ValueError("Audit source manifest binding mismatch")
        tables = {}
        for endpoint in ("sessions", "laps", "stints", "weather", "race_control"):
            name = f"{session}-{endpoint}.json"
            if file_sha256(root/name) != manifest["files"][name]:
                raise ValueError("Audit native file hash mismatch")
            tables[endpoint] = read_json(root/name)
            if any(r.get("session_key") != session for r in tables[endpoint]):
                raise ValueError("Audit native session mismatch")
        identity, = tables["sessions"]
        if (identity["year"], identity["meeting_key"], identity["session_name"]) != (2025, meeting, "Race"):
            raise ValueError("Audit native race mismatch")
        records[session] = tables
    reconstructed = []
    for case in results["cases"]:
        session, driver = case["session"], case["driver"]
        key = (session, driver, tuple(case["stints"]), tuple(case["ages"]))
        if key in seen:
            raise ValueError("Duplicate published forecast case")
        seen.add(key)
        tables = records[session]
        stints = {s["stint_number"]: s for s in tables["stints"] if s["driver_number"] == driver}
        laps = {r["lap_number"]: r for r in tables["laps"] if r["driver_number"] == driver}

        def values(stint: int, ages: list[int]) -> tuple[list[float], list[float]]:
            meta = stints[stint]
            pace, end = [], []
            for age in ages:
                number = age-meta["tyre_age_at_start"]+meta["lap_start"]-1
                row = laps[number]
                if not meta["lap_start"] < number < meta["lap_end"] or row["is_pit_out_lap"]:
                    raise ValueError("Audit found unsupported stint-interior lap")
                pace.append(row["lap_duration"]-max(0., 105.-1.4*(number-1))*.03)
                end.append(datetime.fromisoformat(row["date_start"]).timestamp()+row["lap_duration"])
            return pace, end

        first, last = case["ages"][:3], case["ages"][-3:]
        if len(case["ages"]) != 12 or any(b-a != 1 for a, b in zip(case["ages"], case["ages"][1:])):
            raise ValueError("Audit invalid forecast age support")
        i, j = case["stints"]
        xp, txp = values(i, first)
        xt, txt = values(i, last)
        yp, typ = values(j, first)
        yt, _ = values(j, last)
        compound = stints[j]["compound"]
        if case["compounds"] != [stints[i]["compound"], compound] or stints[i]["compound"] == compound:
            raise ValueError("Audit compound identity mismatch")
        reference_end, forecast_at = max(txp+txt), max(typ)
        if reference_end > forecast_at:
            raise ValueError("Audit reference information occurs after forecast")
        close(case["reference_end_s"], reference_end, "reference availability")
        close(case["forecast_at_s"], forecast_at, "forecast time")
        for field, native in (("reference_target_s", xt), ("current_prefix_s", yp), ("current_target_s", yt)):
            for actual, expected in zip(case[field], native, strict=True):
                close(actual, expected, field)
        start, actual = median(xp)-median(yp), median(xt)-median(yt)
        features = [float(compound == c) for c in COMPOUNDS]+[
            median(xt)-median(xp), 4.5*(yp[2]-yp[0]), start]
        delta = sum(a*b for a, b in zip(features, frozen["pace_head"]["coefficients"], strict=True))
        reference = median(xt)-median(yp)
        predicted = reference-delta
        radius = frozen["pace_head"]["support"][compound]["radius_s"]
        pair_start = median([a-b for a, b in zip(xp, yp, strict=True)])
        pair_actual = median([a-b for a, b in zip(xt, yt, strict=True)])
        expected = {"prefix_s": start, "actual_s": actual, "predicted_s": predicted,
                    "pairwise_prefix_s": pair_start, "pairwise_actual_s": pair_actual,
                    "reference_persistence_s": reference, "lower_s": predicted-radius, "upper_s": predicted+radius,
                    "prior_prediction_s": reference-9*frozen["prior_slopes"][compound]}
        event_features = features+[
            abs(start), start*reference, float(crossover(start, reference)), abs(pair_start)]
        head = frozen["event_head"]
        logit = head["intercept"]+sum((x-m)/scale*b for x, m, scale, b in
            zip(event_features, head["mean"], head["scale"], head["coefficients"], strict=True))
        event_score = 1/(1+exp(-logit)) if logit >= 0 else exp(logit)/(1+exp(logit))
        expected["crossover_score"] = event_score
        expected["predicted_crossover"] = event_score >= head["threshold"]
        for field, value in expected.items():
            close(case[field], value, field)
        reconstructed.append({"session": session, **expected})
    audited = []
    for metric in results["metrics"]:
        rows = [r for r in reconstructed if r["session"] == metric["session"]]
        if not rows:
            for label in ("primary", "pairwise_sensitivity"):
                item = metric[label]
                if (any(item[k] != 0 for k in ("blocks", "observed", "predicted", "matched"))
                        or any(item[k] is not None for k in ("mae_s", "rmse_s", "contrast_persistence_mae_s",
                                                             "reference_persistence_mae_s")) or item["passed"]):
                    raise ValueError("Independent audit invalid empty-cohort disposition")
            if metric["passed"]:
                raise ValueError("Independent audit cannot pass an empty event")
            audited.append({"session": metric["session"], "blocks": 0, "gate_passed": False})
            continue
        gates = []
        for label, prefix, target in (("primary", "prefix_s", "actual_s"),
                                      ("pairwise_sensitivity", "pairwise_prefix_s", "pairwise_actual_s")):
            observed = sum(crossover(r[prefix], r[target]) for r in rows)
            predicted = sum(r["predicted_crossover"] for r in rows)
            matched = sum(crossover(r[prefix], r[target]) and r["predicted_crossover"] for r in rows)
            mae = mean(abs(r["predicted_s"]-r[target]) for r in rows)
            old = mean(abs(r[prefix]-r[target]) for r in rows)
            reference = mean(abs(r["reference_persistence_s"]-r[target]) for r in rows)
            expected = {"blocks": len(rows), "observed": observed, "predicted": predicted, "matched": matched,
                        "mae_s": mae, "rmse_s": sqrt(mean((r["predicted_s"]-r[target])**2 for r in rows)),
                        "contrast_persistence_mae_s": old, "reference_persistence_mae_s": reference,
                        "point_predicted": sum(crossover(r[prefix], r["predicted_s"]) for r in rows),
                        "point_matched": sum(crossover(r[prefix], r[target]) and
                                             crossover(r[prefix], r["predicted_s"]) for r in rows),
                        "event_point_disagreements": sum(r["predicted_crossover"] !=
                                             crossover(r[prefix], r["predicted_s"]) for r in rows)}
            for field, value in expected.items():
                close(metric[label][field], value, label+"/"+field)
            passed = observed > 0 and predicted > 0 and 2*matched >= max(observed, predicted) and mae <= min(old, reference)
            if passed != metric[label]["passed"]:
                raise ValueError("Independent audit acceptance gate mismatch")
            gates.append(passed)
        if metric["passed"] != all(gates):
            raise ValueError("Independent audit event disposition mismatch")
        audited.append({"session": metric["session"], "blocks": len(rows), "gate_passed": all(gates)})
    if results["passed"] != all(m["gate_passed"] for m in audited):
        raise ValueError("Independent audit overall disposition mismatch")
    return seal({"schema_version": "apex-compound-extended-v8-audit", "results_sha256": results["content_sha256"],
                 "calibration_sha256": frozen["content_sha256"], "audit_source_sha256": file_sha256(Path(__file__)),
                 "cases_audited": len(reconstructed), "metrics": audited, "audit_passed": True,
                 "candidate_passed": results["passed"], "scope": "ALL_PUBLISHED_CASES_NOT_FULL_COHORT_ENUMERATION"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("frozen", "results", "archive", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, audit(read_json(args.frozen), read_json(args.results), args.archive))
