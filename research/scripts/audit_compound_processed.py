"""Independently replay the processed-input arithmetic, checkpoint forecasts and race gates."""

import argparse
from hashlib import sha256
from pathlib import Path
from statistics import mean, median

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_driving import base_vector
from audit_compound_race_context import check_result
from audit_compound_repair import compare
from diagnose_compound_decision import ROOT


def vector(groups: list) -> list:
    if len(groups) != 3 or any(len(g) != 2 for g in groups):
        raise ValueError("Wrong processed group shape")
    flags = [all(p["coverage"] >= 0.9 for p in g) for g in groups]
    averages = [[mean(p["means"][j] for p in g) for j in range(5)] for g in groups]
    current = averages[0] if flags[0] else [0.0] * 5
    trend = (
        [groups[0][1]["means"][j] - groups[0][0]["means"][j] for j in range(5)]
        if flags[0]
        else [0.0] * 5
    )
    delta = [
        [current[j] - averages[k][j] for j in range(5)]
        if flags[0] and flags[k]
        else [0.0] * 5
        for k in (1, 2)
    ]
    return [*current, *trend, *delta[0], *delta[1], *[float(f) for f in flags]]


def audit(inputs: dict, result: dict) -> dict:
    folder = ROOT / "docs/verification"
    data = read_json(folder / "compound-v11-development-data.json")
    practice = read_json(folder / "compound-v17-practice-trends.json")
    for doc in (data, inputs, result, practice):
        check_seal(doc)
    compare(inputs["dataset_sha256"], data["content_sha256"], "cohort")
    compare(result["processed_sha256"], inputs["content_sha256"], "processed seal")
    for name, digest in result["hashes"].items():
        path = (ROOT / name).resolve()
        if (
            not path.is_relative_to(ROOT.resolve())
            or sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != digest
        ):
            raise ValueError("Processed implementation changed")
    corrected = read_json(folder / "compound-v21-nominations.json")
    check_seal(corrected)
    compare(
        result["correction_sha256"],
        corrected["content_sha256"],
        "nomination corrections",
    )
    nominations = {
        event: (source["issued"], values)
        for source in corrected["sources"]
        for event, values in source["events"].items()
    }
    compare(len(inputs["lap_summaries"]), len(data["cases"]), "summary count")
    replay(data, inputs, result["result"], nominations, practice, True)
    replay(data, inputs, result["control"], nominations, practice, False)
    # Prediction gates and unavailable native provenance are distinct required checks.
    predicted = result["result"]["qualified"]
    shadow = {k: v for k, v in result.items() if k != "content_sha256"}
    shadow.update(
        development_qualified=predicted, new_holdout_acquisition_allowed=predicted
    )
    gates = check_result(data, seal(shadow))
    shadow.update(
        result=result["control"],
        development_qualified=result["control"]["qualified"],
        new_holdout_acquisition_allowed=result["control"]["qualified"],
    )
    control_gates = check_result(data, seal(shadow))
    for flag in (
        "development_qualified",
        "new_holdout_acquisition_allowed",
        "candidate_accepted",
        "production_promotion",
    ):
        compare(result[flag], False, "processed provenance gate")
    return seal(
        {
            "schema": "compound-processed-audit-v21",
            "result_sha256": result["content_sha256"],
            "forecasts_verified": 2 * len(data["cases"]),
            "prediction_gates": gates,
            "control_gates": control_gates,
            "new_holdout_acquisition_allowed": False,
            "audit_passed": True,
        }
    )


def replay(data, inputs, model, nominations, practice, include_processed):
    for p in model["predictions"]:
        row = data["cases"][p["index"]]
        checkpoint = model["models"][str(row["session"])]
        x = base_vector(row, nominations, practice["events"])
        if include_processed:
            x += vector(inputs["lap_summaries"][p["index"]])
        z = [
            (v - c) / s
            for v, c, s in zip(
                x, checkpoint["center"], checkpoint["scale"], strict=True
            )
        ]
        changes = [
            b
            + sum(t * w for t, w in zip(z, weights, strict=True))
            + median(row["current_prefix_s"])
            - v
            for b, weights, v in zip(
                checkpoint["intercept"],
                checkpoint["coefficients"],
                row["current_prefix_s"],
                strict=True,
            )
        ]
        laps = [
            v + max(-2.0, min(2.0, d))
            for v, d in zip(row["current_prefix_s"], changes, strict=True)
        ]
        compare(p["laps_s"], laps, "processed forecast")
        compare(p["bounded_laps"], sum(abs(v) > 2 for v in changes), "bound hits")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, audit(read_json(args.data), read_json(args.result)))
