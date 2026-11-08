"""Evaluate the registered driving-state model against the full R041 cohort."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from diagnose_compound_decision import ROOT
from diagnose_compound_line import FOLDER, evaluate
from diagnose_compound_practice import practice_inputs


def driving_features(groups: list[list[dict]]) -> list[float]:
    """Return 23 inputs with explicit support and zero-filled missing groups."""
    if len(groups) != 3 or any(len(g) != 3 for g in groups):
        raise ValueError("Driving state requires three groups of three laps")
    for group in groups:
        for lap in group:
            coverage, values = lap["coverage"], lap["means"]
            if not np.isfinite(coverage) or not 0 <= coverage <= 1 + 1e-12:
                raise ValueError("Invalid driving coverage")
            if len(values) != 5 or not np.isfinite(values).all():
                raise ValueError("Invalid driving means")
            if not 0 <= values[0] <= 120 or any(not 0 <= v <= 1 for v in values[1:]):
                raise ValueError("Driving means outside observed bounds")
    supported = [all(lap["coverage"] >= 0.9 for lap in g) for g in groups]
    means = [np.mean([lap["means"] for lap in g], axis=0) for g in groups]
    current = means[0] if supported[0] else np.zeros(5)
    trend = (
        np.subtract(groups[0][-1]["means"], groups[0][0]["means"])
        if supported[0]
        else np.zeros(5)
    )
    differences = [
        current - means[j] if supported[0] and supported[j] else np.zeros(5)
        for j in (1, 2)
    ]
    return [
        *current.tolist(),
        *trend.tolist(),
        *differences[0].tolist(),
        *differences[1].tolist(),
        *[float(s) for s in supported],
    ]


def study() -> dict:
    data, parent, _, _, base_matrix = practice_inputs()
    driving = read_json(FOLDER / "compound-v19-driving-data.json")
    control = read_json(FOLDER / "compound-v17-development.json")
    for doc in (driving, control):
        check_seal(doc)
    if (
        driving["dataset_sha256"] != data["content_sha256"]
        or control["control_sha256"] != parent["content_sha256"]
    ):
        raise ValueError("Driving-state input cohort mismatch")
    matrix = np.asarray(
        [
            base + driving_features(groups)
            for base, groups in zip(base_matrix, driving["lap_summaries"], strict=True)
        ]
    )
    result = evaluate(data["cases"], data["sources"], matrix)
    paths = [
        Path(__file__),
        ROOT / "research/scripts/compound_driving_data.py",
        ROOT / "research/protocols/COMPOUND_DRIVING_STATE_V19.md",
        ROOT / "research/protocols/COMPOUND_DRIVING_STATE_V19_ACCESS.md",
    ]
    hashes = {
        p.relative_to(ROOT).as_posix(): sha256(
            p.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for p in paths
    }
    ready = driving["acquisition_ready"]
    return seal(
        {
            "schema": "compound-driving-v19",
            "result": result,
            "hashes": hashes,
            "driving_sha256": driving["content_sha256"],
            "v17_sha256": control["content_sha256"],
            "acquisition_ready": ready,
            "development_qualified": ready and result["qualified"],
            "new_holdout_acquisition_allowed": ready and result["qualified"],
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, study())
