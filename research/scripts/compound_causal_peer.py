"""Forecast R041 target laps from causally available, driver-adjusted peers."""

import argparse
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from statistics import median

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_driver_control import prior_differences
from audit_compound_race_context import check_result
from audit_compound_same_phase_support import clean_field, overlapping_ages
from compound_line_proximity import archive_laps
from confirm_compound_multiseason import canonical_file_sha
from diagnose_compound_line import score_forecasts
from prepare_compound_pit_exit import BASE, FOLDER


def observations(field, native, rows):
    clocks = {(end, driver): (lap, duration) for end, driver, lap, duration in native}
    if len(clocks) != len(native):
        raise ValueError("Ambiguous driver timing")
    controls = defaultdict(list)
    for a, b in combinations(sorted(field, key=lambda s: (s["driver"], s["stint"])), 2):
        drivers = a["driver"], b["driver"]
        if drivers[0] == drivers[1] or a["compound"] != b["compound"]:
            continue
        for age, u, v in overlapping_ages(a, b, clocks):
            controls[drivers].append(
                (u, v, a["stint"], b["stint"], a["values"][age] - b["values"][age])
            )
    for pool in controls.values():
        pool.sort(key=lambda p: (max(p[:2]), *p[:2]))
    records = []
    for row in rows:
        subject, ages = row["driver"], row["ages"]
        first_end = row["current_history"][-3]["end_s"]
        start = first_end - clocks[first_end, subject][1]
        items = []
        for peer in field:
            driver = peer["driver"]
            if (
                driver == subject
                or peer["compound"] != row["compounds"][1]
                or not all(k in peer["ends"] for k in ages)
            ):
                continue
            avail = max(peer["ends"][k] for k in ages)
            if avail > row["forecast_at_s"]:
                continue
            pair = tuple(sorted((subject, driver)))
            subject_first = pair[0] == subject
            stints = row["stints"][1], peer["stint"]
            diffs = prior_differences(
                controls[pair], start, stints if subject_first else stints[::-1]
            )
            if len(diffs) < 6:
                continue
            items.append(
                {
                    "driver": driver,
                    "stint": peer["stint"],
                    "available_at_s": avail,
                    "offset_s": median(diffs) * (1 if subject_first else -1),
                    "prior_laps": len(diffs),
                    "peer_laps_s": [peer["values"][k] for k in ages[-3:]],
                }
            )
        records.append(items)
    return records


def bound(row, laps):
    changes = [v - p for v, p in zip(laps, row["current_prefix_s"], strict=True)]
    return [
        p + max(-2.0, min(2.0, c))
        for p, c in zip(row["current_prefix_s"], changes, strict=True)
    ], sum(abs(c) > 2 for c in changes)


def predict(row, items, fallback):
    if not items:
        return fallback
    drivers = defaultdict(list)
    for item in items:
        if (
            item["prior_laps"] < 6
            or item["available_at_s"] > row["forecast_at_s"]
            or item["driver"] == row["driver"]
        ):
            raise ValueError("Ineligible peer observation")
        drivers[item["driver"]].append(
            [s + item["offset_s"] for s in item["peer_laps_s"]]
        )
    by_driver = [
        [median(axis) for axis in zip(*laps, strict=True)] for laps in drivers.values()
    ]
    return bound(row, [median(axis) for axis in zip(*by_driver, strict=True)])


def run(root):
    data = read_json(FOLDER / "compound-v24-cohort.json")
    control = read_json(FOLDER / "compound-v24-development.json")
    for doc in (data, control):
        check_seal(doc)
    if control["dataset_sha256"] != data["content_sha256"]:
        raise ValueError("Peer fallback cohort changed")
    baseline = control["results"]["nomination_practice_ridge"]
    fallbacks = {
        p["index"]: (p["laps_s"], p["bounded_laps"]) for p in baseline["predictions"]
    }
    records, forecasts, ideal, counts = {}, {}, {}, {}
    for event, source in data["sources"].items():
        selected = {
            i: r for i, r in enumerate(data["cases"]) if str(r["session"]) == event
        }
        field = clean_field(root, event, source)
        groups = observations(
            field, archive_laps(root, event, source), selected.values()
        )
        counts[event] = sum(bool(g) for g in groups)
        for (i, row), items in zip(selected.items(), groups, strict=True):
            records[str(i)] = items
            forecasts[i] = predict(row, items, fallbacks[i])
            ideal[i] = bound(row, row["current_target_s"]) if items else fallbacks[i]
    result = score_forecasts(data["cases"], data["sources"], forecasts)
    oracle = score_forecasts(data["cases"], data["sources"], ideal)
    audit = check_result(
        data,
        seal(
            {
                "result": result,
                "development_qualified": result["qualified"],
                "new_holdout_acquisition_allowed": result["qualified"],
            }
        ),
    )
    return seal(
        {
            "schema": "compound-causal-peer-v27",
            "dataset_sha256": data["content_sha256"],
            "control_sha256": control["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(
                BASE / "research/protocols/COMPOUND_CAUSAL_PEER_V27.md"
            ),
            "contributors": records,
            "supported_by_event": counts,
            "supported": sum(counts.values()),
            "result": result,
            "audit": audit,
            "bounded_oracle_diagnostic_failed_events": oracle["failed_events"],
            "unreachable_failed_events": [
                e for e in baseline["failed_events"] if counts[e] == 0
            ],
            "development_qualified": result["qualified"],
            "new_holdout_acquisition_allowed": result["qualified"],
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
