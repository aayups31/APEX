"""Report every saved R041 rejection and the current per-event failure ledger."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from confirm_compound_multiseason import BASE, canonical_file_sha


def legacy_failures(metric: dict) -> list[str]:
    """Explain historical gates without changing their original dispositions."""
    codes = []
    cases = metric.get("blocks", metric.get("cases", metric.get("contrasts", 0)))
    if not cases:
        return ["NO_ELIGIBLE_COMPARISONS"]
    observed = metric.get("observed", metric.get("observed_crossovers", 0))
    predicted, matched = metric.get("predicted"), metric.get("matched", 0)
    if not observed:
        codes.append("NO_POSITIVE_CROSSOVER_EVIDENCE")
    elif 2*matched < observed:
        codes.append("CROSSOVER_RECALL_BELOW_HALF")
    if predicted and not observed:
        codes.append("FALSE_ALARM_ON_NEGATIVE_CONTROL")
    if observed and (predicted == 0 or predicted is not None and 2*matched < predicted):
        codes.append("CROSSOVER_PRECISION_BELOW_HALF")
    mae = metric.get("mae_s")
    for key in ("persistence_mae_s", "reference_persistence_mae_s", "contrast_persistence_mae_s", "shared_slope_mae_s"):
        if mae is not None and metric.get(key) is not None and mae > metric[key]:
            codes.append("PACE_WORSE_THAN_"+key.upper())
    return codes


def inventory(repair: dict, cohort: dict) -> dict:
    for item in (repair, cohort):
        check_seal(item)
    if repair["dataset_sha256"] != cohort["dataset_sha256"]:
        raise ValueError("Failure inventory dataset/cohort binding mismatch")
    root = BASE/"docs/verification"
    paths = [root/"compound-primary-results.json", *sorted(root.glob("compound-v*-*results.json"))]
    # Include simple v2-v7 filenames as well as named preliminary/coverage runs.
    paths += sorted(root.glob("compound-v*-results.json"))
    experiments = []
    for path in dict.fromkeys(paths):
        data = read_json(path)
        if "content_sha256" in data:
            check_seal(data)
        reports = []
        for metric in data.get("metrics", data.get("events", [])):
            if not isinstance(metric, dict):
                continue
            identity = metric.get("session", metric.get("round"))
            labels = []
            if "primary" in metric:
                labels = [(name, metric[name]) for name in ("primary", "pairwise_sensitivity")]
            elif "pace" in metric:
                if metric["pace"] is not None:
                    labels = [(str(i), {**p, **metric["events"][i], "cases": metric["cases"],
                               "reference_persistence_mae_s": p["reference_mae_s"],
                               "contrast_persistence_mae_s": p["contrast_mae_s"]}) for i, p in enumerate(metric["pace"])]
                else:
                    labels = [("both", {"cases": 0})]
            else:
                labels = [("original", metric)]
            reports.append({"event": identity, "original_passed": metric["passed"],
                            "labels": [{"label": name, "failure_codes": legacy_failures(m)} for name, m in labels]})
        experiments.append({"path": path.relative_to(BASE).as_posix(), "file_sha256_lf": canonical_file_sha(path),
                            "original_passed": data.get("passed"), "events": reports})
    current = repair["readiness"]
    counts = Counter(code for event in current["events"] for label in event["labels"] for code in label["failure_codes"])
    empty = [{"event": e["session"], "pair_reasons": dict(Counter(p["disposition"] for p in e["pairs"])),
              "maximum_common_age_run": max((p["maximum_common_run"] for p in e["pairs"]), default=0),
              "lap_exclusions": e["lap_exclusions"]} for e in cohort["events"] if not e["cases"]]
    return seal({"schema_version": "apex-compound-complete-failure-ledger-v10", "historical_experiments": experiments,
                 "repair_result_sha256": repair["content_sha256"], "cohort_audit_sha256": cohort["content_sha256"],
                 "current_event_failures": current, "current_failure_code_counts": dict(counts), "unsupported_source_details": empty,
                 "fixed": ["POOLED_QUALIFICATION_COULD_HIDE_FAILED_EVENTS", "INDEPENDENT_FULL_COHORT_DENOMINATOR_MISSING",
                           "SEPARATE_HEAD_DECISIONS_COULD_CONTRADICT_POINT_FORECAST", "UNCONTROLLED_INTERMEDIATE_NUMERICAL_VALUES"],
                 "improved_opened_cases": ["JAPAN_FALSE_ALARMS_REMOVED_BY_SELECTED_REFERENCE_PERSISTENCE",
                                           "JAPAN_AND_QATAR_PACE_REGRESSIONS_REMOVED_BY_SELECTED_REFERENCE_PERSISTENCE"],
                 "unresolved": ["ALL_EVENT_PACE_AND_CROSSOVER_GENERALIZATION", "FRESH_TWO_INFORMATIVE_EVENT_CONFIRMATION",
                                "UNCERTAINTY_CALIBRATION_BEYOND_DESCRIPTIVE_CROSS_EVENT_RADII"],
                 "data_limits": ["NO_ELIGIBLE_COMMON_AGE_SUPPORT_IN_FOUR_SOURCE_RACES", "PHYSICAL_WEAR_NOT_MEASURED",
                                 "FUEL_AND_PHYSICAL_COMPOUND_ALLOCATION_NOT_MEASURED"],
                 "new_holdout_acquisition_allowed": current["development_qualified"], "r041_complete": False})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repair", "cohort", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, inventory(read_json(args.repair), read_json(args.cohort)))
