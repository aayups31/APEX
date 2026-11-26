"""Test whether driver-adjusted compound differences transfer across races."""

import argparse
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_driver_control import inspect_event
from audit_compound_same_phase_support import clean_field
from compound_line_proximity import archive_laps
from confirm_compound_multiseason import canonical_file_sha
from prepare_compound_pit_exit import BASE, FOLDER

ORDER = ("HARD", "MEDIUM", "SOFT")


def orientation(row):
    a, b = row["compounds"]
    return ((a, b), 1) if ORDER.index(a) < ORDER.index(b) else ((b, a), -1)


def score(events):
    gaps = defaultdict(lambda: defaultdict(list))
    for event, rows in events.items():
        for row in rows:
            pair, sign = orientation(row)
            gaps[pair][event].append(sign * (row["target"] - row["prior"]))
    folds = {}
    for event, rows in events.items():
        predictions = []
        for row in rows:
            pair, sign = orientation(row)
            training = {e: median(g) for e, g in gaps[pair].items() if e != event}
            gap = median(training.values()) if training else 0.0
            predictions.append(
                {
                    **row,
                    "prediction": row["prior"] + sign * gap,
                    "training_race_medians": training,
                }
            )
        folds[event] = {
            "predictions": predictions,
            "cases": len(rows),
            "fallback_cases": sum(not r["training_race_medians"] for r in predictions),
            "mae": {
                k: mean(abs(r[k] - r["target"]) for r in predictions)
                for k in ("prediction", "prefix", "prior")
            }
            if rows
            else {},
        }
    return folds


def study(root):
    data = read_json(FOLDER / "compound-v24-cohort.json")
    support = read_json(FOLDER / "compound-same-phase-connected-support.json")
    check_seal(data)
    check_seal(support)
    if data["content_sha256"] != support["dataset_sha256"]:
        raise ValueError("Mismatched support inventory")
    events = {}
    for event, source in data["sources"].items():
        rows = inspect_event(
            clean_field(root, event, source),
            archive_laps(root, event, source),
            different_compounds=True,
        )
        events[event] = [r for r in rows if r["prior"] is not None]
        counts = support["events"][event]
        if (len(rows), len(events[event])) != (
            counts["candidate_windows"],
            counts["windows_with_six_prior_controls"],
        ):
            raise ValueError("Driver transfer denominator mismatch")
    folds = score(events)
    supported = [v for v in folds.values() if v["cases"]]
    return seal(
        {
            "scope": "DIRECT_DRIVER_CONTROL_DIFFERENT_COMPOUND_TRANSFER_DIAGNOSTIC",
            "dataset_sha256": data["content_sha256"],
            "support_sha256": support["content_sha256"],
            "source_sha256_lf": {
                p.name: canonical_file_sha(p)
                for p in (
                    Path(__file__),
                    Path(__file__).with_name("audit_compound_driver_control.py"),
                    BASE / "research/protocols/COMPOUND_DRIVER_TRANSFER.md",
                )
            },
            "folds": folds,
            "macro_mae": {
                k: mean(r["mae"][k] for r in supported)
                for k in ("prediction", "prefix", "prior")
            },
            "fallback_cases": sum(r["fallback_cases"] for r in supported),
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, study(args.native_root))
