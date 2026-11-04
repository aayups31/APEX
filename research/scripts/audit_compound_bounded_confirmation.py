"""Independent native/scalar audit for the prospectively frozen R041 v9 panel."""
from __future__ import annotations

import argparse
from math import isclose, sqrt
from pathlib import Path
from statistics import mean, median

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_bounded import LABELS, crossing, scalar_forecast
from audit_compound_context import audit_case, utc

EVENTS = {10006: (3, 1256), 10022: (5, 1258), 9947: (12, 1277), 9858: (22, 1274)}


def close(actual: float, expected: float, field: str) -> None:
    if not isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError(f"Independent bounded confirmation mismatch: {field}")


def audit(frozen: dict, results: dict, root: Path) -> dict:
    """Rebuild native labels/context and every scalar forecast/acceptance claim."""
    for document in (frozen, results):
        check_seal(document)
    if (results["calibration_sha256"] != frozen["content_sha256"] or frozen["heldout_events"] != list(EVENTS)
            or results["hashes"] != frozen["hashes"] or set(results["sources"]) != {str(e) for e in EVENTS}):
        raise ValueError("Independent bounded confirmation binding/split mismatch")
    manifest = read_json(root/"manifest.json")
    check_seal(manifest)
    if len(results["metrics"]) != len(EVENTS) or {m["session"] for m in results["metrics"]} != set(EVENTS):
        raise ValueError("Independent bounded confirmation missing or duplicated event")
    seen, reconstructed, contribution_count = set(), [], 0
    for session, (round_number, meeting) in EVENTS.items():
        assert_development_event(2025, round_number)
        if results["sources"][str(session)] != manifest["content_sha256"]:
            raise ValueError("Independent bounded confirmation source manifest mismatch")
        tables = {}
        for endpoint in ("sessions", "laps", "stints", "weather", "race_control"):
            name = f"{session}-{endpoint}.json"
            if file_sha256(root/name) != manifest["files"][name]:
                raise ValueError("Independent bounded confirmation native hash mismatch")
            tables[endpoint] = read_json(root/name)
            if not tables[endpoint] or any(r.get("session_key") != session for r in tables[endpoint]):
                raise ValueError("Independent bounded confirmation native session mismatch")
        identity, = tables["sessions"]
        if (identity["year"], identity["meeting_key"], identity["session_name"]) != (2025, meeting, "Race"):
            raise ValueError("Independent bounded confirmation native race mismatch")
        laps = {(r["driver_number"], r["lap_number"]): r for r in tables["laps"]}
        stints = {(r["driver_number"], r["stint_number"]): r for r in tables["stints"]}
        for case in [r for r in results["cases"] if r["session"] == session]:
            key = session, case["driver"], tuple(case["stints"]), tuple(case["ages"])
            if key in seen:
                raise ValueError("Independent bounded confirmation duplicate case")
            seen.add(key)
            def values(stint: int, ages: list, *, native_stints=stints, native_laps=laps, driver=case["driver"]) -> tuple[list, list]:
                meta = native_stints[(driver, stint)]
                native_values, ends = [], []
                for age in ages:
                    number = age-meta["tyre_age_at_start"]+meta["lap_start"]-1
                    raw = native_laps[(driver, number)]
                    native_values.append(raw["lap_duration"]-max(0., 105.-1.4*(number-1))*.03)
                    ends.append(utc(raw["date_start"])+raw["lap_duration"])
                return native_values, ends
            i, j = case["stints"]
            first, last = case["ages"][:3], case["ages"][-3:]
            if len(case["ages"]) != 12 or any(b-a != 1 for a, b in zip(case["ages"][:-1], case["ages"][1:], strict=True)):
                raise ValueError("Independent bounded confirmation invalid age window")
            xp, xpt = values(i, first)
            xt, xtt = values(i, last)
            yp, ypt = values(j, first)
            yt, _ = values(j, last)
            reference_end, cutoff = max(xpt+xtt), max(ypt)
            if reference_end > cutoff:
                raise ValueError("Independent bounded confirmation future reference")
            expected = {"prefix_s": median(xp)-median(yp), "actual_s": median(xt)-median(yt),
                        "pairwise_prefix_s": median(a-b for a, b in zip(xp, yp, strict=True)),
                        "pairwise_actual_s": median(a-b for a, b in zip(xt, yt, strict=True)),
                        "forecast_at_s": cutoff, "reference_end_s": reference_end}
            for field, value in expected.items():
                close(case[field], value, field)
            for field, native in (("reference_target_s", xt), ("current_prefix_s", yp), ("current_target_s", yt)):
                for a, b in zip(case[field], native, strict=True):
                    close(a, b, field)
            if case["compounds"] != [stints[(case["driver"], k)]["compound"] for k in (i, j)]:
                raise ValueError("Independent bounded confirmation compound mismatch")
            contribution_count += audit_case(case, tables, "OPENF1")
            prediction = scalar_forecast(frozen["pace_head"], frozen["event_head"], case)
            reference = median(xt)-median(yp)
            features = [float(case["compounds"][1] == c) for c in ("SOFT", "MEDIUM", "HARD")]+[
                median(xt)-median(xp), 4.5*(yp[2]-yp[0]), median(xp)-median(yp)]
            unbounded = reference-sum(a*b for a, b in zip(features, frozen["unbounded_head"]["coefficients"], strict=True))
            prediction["unbounded_prediction_s"] = unbounded
            for field, value in prediction.items():
                if isinstance(value, (bool, list)):
                    if case[field] != value:
                        raise ValueError(f"Independent bounded confirmation mismatch: {field}")
                else:
                    close(case[field], value, field)
            reconstructed.append({**case, **expected, **prediction})
    if len(reconstructed) != len(results["cases"]):
        raise ValueError("Independent bounded confirmation unresolved case session")
    informative, unsupported, failed = [], [], []
    for report in results["metrics"]:
        rows = [r for r in reconstructed if r["session"] == report["session"]]
        close(report["cases"], len(rows), "case denominator")
        if not rows:
            unsupported.append(report["session"])
            if (report["pace"] is not None or report["events"] is not None or report["passed"]
                    or report["informative"] or report["disposition"] != "INCONCLUSIVE_FOR_SUPPORT"):
                raise ValueError("Independent bounded confirmation invalid empty cohort")
            continue
        gates, positive = [], []
        for index, (prefix, target) in enumerate(LABELS):
            errors = [r["predicted_s"]-r[target] for r in rows]
            pace = {"mae_s": mean(abs(e) for e in errors), "rmse_s": sqrt(mean(e*e for e in errors)),
                    "reference_mae_s": mean(abs(r["reference_persistence_s"]-r[target]) for r in rows),
                    "contrast_mae_s": mean(abs(r[prefix]-r[target]) for r in rows),
                    "coverage": mean(r["lower_s"] <= r[target] <= r["upper_s"] for r in rows),
                    "mean_width_s": mean(r["upper_s"]-r["lower_s"] for r in rows)}
            for field, value in pace.items():
                close(report["pace"][index][field], value, field)
            close(report["unbounded_ridge_mae_s"][index], mean(abs(r["unbounded_prediction_s"]-r[target]) for r in rows), "unbounded ridge MAE")
            observed = sum(crossing(r[prefix], r[target]) for r in rows)
            predicted = sum(r["predicted_crossover"] for r in rows)
            matched = sum(crossing(r[prefix], r[target]) and r["predicted_crossover"] for r in rows)
            counts = {"observed": observed, "predicted": predicted, "matched": matched,
                      "precision": matched/predicted if predicted else None, "recall": matched/observed if observed else None,
                      "min_precision_recall": matched/max(observed, predicted, 1)}
            for field, value in counts.items():
                if value is None:
                    if report["events"][index][field] is not None:
                        raise ValueError("Independent bounded confirmation invalid undefined rate")
                else:
                    close(report["events"][index][field], value, field)
            gates.append(pace["mae_s"] <= min(pace["reference_mae_s"], pace["contrast_mae_s"])
                         and (predicted == 0 if observed == 0 else predicted > 0 and counts["min_precision_recall"] >= .5))
            positive.append(observed > 0)
        if report["informative"] != all(positive) or report["passed"] != all(gates) or report["passed_labels"] != gates:
            raise ValueError("Independent bounded confirmation per-event gate mismatch")
        if all(positive):
            informative.append(report["session"])
        if not all(gates):
            failed.append(report["session"])
    passed = len(informative) >= 2 and not failed
    if (results["required_informative_events"] != 2 or results["informative_events"] != informative
            or results["unsupported_events"] != unsupported or results["failed_supported_events"] != failed
            or results["passed"] != passed or results["production_promotion"]):
        raise ValueError("Independent bounded confirmation overall enrollment/gate mismatch")
    return seal({"schema_version": "apex-compound-bounded-confirmation-native-scalar-audit-v9",
                 "results_sha256": results["content_sha256"], "calibration_sha256": frozen["content_sha256"],
                 "audit_source_sha256": file_sha256(Path(__file__)), "cases_audited": len(reconstructed),
                 "field_contributions_audited": contribution_count, "audit_passed": True, "candidate_passed": passed,
                 "scope": "ALL_PUBLISHED_NATIVE_CASES_CONTEXT_AND_SCALAR_GATES_NOT_FULL_COHORT_ENUMERATION"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("frozen", "results", "archive", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, audit(read_json(args.frozen), read_json(args.results), args.archive))
