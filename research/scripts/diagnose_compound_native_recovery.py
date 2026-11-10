"""Fit and independently replay the complete native R041 recovery candidate."""

import argparse
from hashlib import sha256
from math import log1p
from pathlib import Path
from statistics import median

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.compound_allocation import features, inventory
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_driving import base_vector, driving_vector
from audit_compound_race_context import check_result
from audit_compound_repair import compare
from diagnose_compound_decision import ROOT
from diagnose_compound_driving import driving_features
from diagnose_compound_line import FOLDER, evaluate


def audit(
    data: dict, observed: dict, result: dict, nominations: dict, practice: dict
) -> dict:
    """Independently reconstruct input arithmetic, scalar inference and race gates."""
    for item in result["predictions"]:
        index = item["index"]
        row = data["cases"][index]
        checkpoint = result["models"][str(row["session"])]
        x = base_vector(row, nominations, practice) + driving_vector(
            observed["lap_summaries"][index]
        )
        z = [
            (v - c) / s
            for v, c, s in zip(
                x, checkpoint["center"], checkpoint["scale"], strict=True
            )
        ]
        changes = [
            b
            + sum(v * w for v, w in zip(z, weights, strict=True))
            + median(row["current_prefix_s"])
            - p
            for b, weights, p in zip(
                checkpoint["intercept"],
                checkpoint["coefficients"],
                row["current_prefix_s"],
                strict=True,
            )
        ]
        laps = [
            p + min(2.0, max(-2.0, delta))
            for p, delta in zip(row["current_prefix_s"], changes, strict=True)
        ]
        compare(item["laps_s"], laps, "native recovery forecast")
        compare(
            item["bounded_laps"],
            sum(abs(v) > 2 for v in changes),
            "native recovery bounds",
        )
    return check_result(
        data,
        seal(
            {
                "result": result,
                "development_qualified": result["qualified"],
                "new_holdout_acquisition_allowed": result["qualified"],
            }
        ),
    )


def study(observed: dict) -> dict:
    data = read_json(FOLDER / "compound-v11-development-data.json")
    corrected = read_json(FOLDER / "compound-v21-nominations.json")
    practice = read_json(FOLDER / "compound-v17-practice-trends.json")
    previous = read_json(FOLDER / "compound-v21-development.json")
    for doc in (data, observed, corrected, practice, previous):
        check_seal(doc)
    if not (
        observed["acquisition_ready"]
        and data["content_sha256"]
        == observed["dataset_sha256"]
        == previous["dataset_sha256"]
        == practice["dataset_sha256"]
        and corrected["content_sha256"] == previous["correction_sha256"]
    ):
        raise ValueError(
            "Native recovery is incomplete or uses a different corrected cohort"
        )
    allocations = inventory(corrected["sources"], set(data["sources"]))
    matrix = []
    for row, groups in zip(data["cases"], observed["lap_summaries"], strict=True):
        x = features(row, allocations, True)
        for compound in row["compounds"]:
            item = practice["events"][str(row["session"])][compound]
            x.extend([item["drift_s"] or 0.0, log1p(item["drivers"])])
        matrix.append(x + driving_features(groups))
    result = evaluate(data["cases"], data["sources"], np.asarray(matrix))
    nominations = {
        event: (source["issued"], codes)
        for source in corrected["sources"]
        for event, codes in source["events"].items()
    }
    gate_audit = audit(data, observed, result, nominations, practice["events"])
    sources = [
        Path(__file__),
        ROOT / "research/scripts/prepare_compound_native_recovery.py",
        ROOT / "research/protocols/COMPOUND_NATIVE_RECOVERY_V23.md",
        ROOT / "research/protocols/COMPOUND_NATIVE_RECOVERY_V23_ACCESS.md",
    ]
    hashes = {
        path.relative_to(ROOT).as_posix(): sha256(
            path.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for path in sources
    }
    return seal(
        {
            "schema": "compound-native-model-v23",
            "dataset_sha256": data["content_sha256"],
            "native_sha256": observed["content_sha256"],
            "control_sha256": previous["content_sha256"],
            "hashes": hashes,
            "result": result,
            "independent_checkpoint_and_gate_audit": gate_audit,
            "new_holdout_acquisition_allowed": result["qualified"],
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, study(read_json(args.data)))
