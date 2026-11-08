"""Evaluate one registered processed-driving candidate on the unchanged R041 cohort."""

import argparse
from hashlib import sha256
from pathlib import Path

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from apexsim.research.tracing_telemetry import processed_features
from diagnose_compound_decision import ROOT
from diagnose_compound_line import evaluate
from diagnose_compound_practice import practice_inputs


def study(path: Path) -> dict:
    data, parent, _, _, matrix = practice_inputs()
    inputs = read_json(path)
    check_seal(inputs)
    if inputs["dataset_sha256"] != data["content_sha256"]:
        raise ValueError("Wrong processed cohort")
    x = np.asarray(
        [
            base + processed_features(groups)
            for base, groups in zip(matrix, inputs["lap_summaries"], strict=True)
        ]
    )
    result = evaluate(data["cases"], data["sources"], x)
    paths = [
        Path(__file__),
        ROOT / "research/scripts/prepare_compound_processed.py",
        ROOT / "apex_engine/src/apexsim/research/tracing_telemetry.py",
        ROOT / "research/protocols/COMPOUND_PROCESSED_V20.md",
    ]
    hashes = {
        p.relative_to(ROOT).as_posix(): sha256(
            p.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for p in paths
    }
    return seal(
        {
            "schema": "compound-processed-model-v20",
            "dataset_sha256": data["content_sha256"],
            "processed_sha256": inputs["content_sha256"],
            "v13_parent_sha256": parent["content_sha256"],
            "hashes": hashes,
            "result": result,
            "prediction_qualified": result["qualified"],
            "development_qualified": False,
            "native_provenance_known": False,
            "new_holdout_acquisition_allowed": False,
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, study(args.data))
