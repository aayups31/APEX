"""Assess transfer of same-compound driver offsets to later clean race windows."""

import argparse
from collections import defaultdict
from itertools import combinations, groupby
from pathlib import Path
from statistics import mean, median

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_same_phase_support import clean_field, overlapping_ages
from compound_line_proximity import archive_laps
from confirm_compound_multiseason import canonical_file_sha
from prepare_compound_pit_exit import BASE, FOLDER


def prior_differences(pool, cutoff, excluded):
    used_a, used_b, differences = set(), set(), []
    for u, v, i, j, difference in pool:
        if max(u, v) >= cutoff:
            break
        if excluded and (i == excluded[0] or j == excluded[1]):
            continue
        if u not in used_a and v not in used_b:
            used_a.add(u)
            used_b.add(v)
            differences.append(difference)
    return differences


def inspect_event(field, native, *, different_compounds=False):
    clocks = {(end, driver): (lap, duration) for end, driver, lap, duration in native}
    if len(clocks) != len(native):
        raise ValueError("Ambiguous driver-control clocks")
    controls, windows = defaultdict(list), []
    for a, b in combinations(sorted(field, key=lambda s: (s["driver"], s["stint"])), 2):
        drivers = a["driver"], b["driver"]
        stints = a["stint"], b["stint"]
        if drivers[0] == drivers[1]:
            continue
        pairs = list(overlapping_ages(a, b, clocks))

        differences = {age: a["values"][age] - b["values"][age] for age, _, _ in pairs}
        starts = {
            age: min(u - clocks[u, drivers[0]][1], v - clocks[v, drivers[1]][1])
            for age, u, v in pairs
        }

        same = a["compound"] == b["compound"]
        if same:
            for age, u, v in pairs:
                controls[drivers].append((u, v, *stints, differences[age]))
        if same == different_compounds:
            continue
        for _, group in groupby(enumerate(pairs), key=lambda p: p[1][0] - p[0]):
            run = [item for _, item in group]
            for k in range(0, len(run) - 11, 12):
                block = run[k : k + 12]

                if min(starts[p[0]] for p in block[-3:]) <= max(
                    max(p[1:]) for p in block[:3]
                ):
                    raise ValueError("Driver-control target overlaps prefix")
                windows.append(
                    (
                        drivers,
                        stints,
                        (a["compound"], b["compound"]),
                        block[0][0],
                        starts[block[0][0]],
                        median(differences[p[0]] for p in block[:3]),
                        median(differences[p[0]] for p in block[-3:]),
                    )
                )
    for pool in controls.values():
        pool.sort(key=lambda p: (max(p[:2]), *p[:2]))
    results = []
    for drivers, stints, compounds, age, cutoff, prefix, target in windows:
        item = {
            "drivers": list(drivers),
            "stints": list(stints),
            "compounds": list(compounds),
            "first_age": age,
            "cutoff": cutoff,
            "prefix": prefix,
            "target": target,
        }
        for label, exclude in (("prior", None), ("cross_stint", stints)):
            diffs = prior_differences(controls[drivers], cutoff, exclude)
            item[label] = median(diffs) if len(diffs) >= 6 else None
            item[label + "_count"] = len(diffs)
        results.append(item)
    return results


def metrics(rows, method):
    subset = [r for r in rows if r[method] is not None]
    if not subset:
        return {"cases": 0}
    return {
        "cases": len(subset),
        "prior_mae": mean(abs(r[method] - r["target"]) for r in subset),
        "prefix_mae": mean(abs(r["prefix"] - r["target"]) for r in subset),
        "zero_mae": mean(abs(r["target"]) for r in subset),
    }


def audit(root):
    data = read_json(FOLDER / "compound-v24-cohort.json")
    check_seal(data)
    cases, summaries = {}, {}
    for event, source in data["sources"].items():
        cases[event] = inspect_event(
            clean_field(root, event, source), archive_laps(root, event, source)
        )
    for method in ("prior", "cross_stint"):
        folds = {e: metrics(rows, method) for e, rows in cases.items()}
        supported = [m for m in folds.values() if m["cases"]]
        summaries[method] = {
            "folds": folds,
            "races": len(supported),
            "cases": sum(m["cases"] for m in supported),
            "macro_mae": {
                key: mean(m[key] for m in supported) if supported else None
                for key in ("prior_mae", "zero_mae", "prefix_mae")
            },
            "improved_over_zero": sum(
                m["prior_mae"] < m["zero_mae"] for m in supported
            ),
            "improved_over_prefix": sum(
                m["prior_mae"] < m["prefix_mae"] for m in supported
            ),
        }
    return seal(
        {
            "schema": "compound-driver-control-v1",
            "dataset_sha256": data["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(
                BASE / "research/protocols/COMPOUND_DRIVER_CONTROL_CHECK.md"
            ),
            "cases": cases,
            "summaries": summaries,
            "scope": "SAME_COMPOUND_NEGATIVE_CONTROL_ONLY",
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, audit(args.native_root))
