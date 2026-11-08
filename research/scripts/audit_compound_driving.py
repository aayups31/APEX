"""Independent scalar feature and checkpoint replay for the R041 v19 study."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite, log1p
from pathlib import Path
from statistics import mean, median

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_race_context import check_result
from audit_compound_repair import compare
from audit_compound_trajectory import features as trajectory_features
from diagnose_compound_decision import ROOT

FOLDER = ROOT / "docs/verification"


def driving_vector(groups: list[list[dict]]) -> list[float]:
    """Reconstruct 23 registered inputs directly from the nine stored lap summaries."""
    if len(groups) != 3 or any(len(group) != 3 for group in groups):
        raise ValueError("Driving audit requires three groups of three laps")
    supported, averages = [], []
    for group in groups:
        for lap in group:
            coverage, values = lap["coverage"], lap["means"]
            if not isfinite(coverage) or not 0 <= coverage <= 1 + 1e-12:
                raise ValueError("Invalid driving coverage")
            if len(values) != 5 or not all(isfinite(v) for v in values):
                raise ValueError("Invalid driving lap means")
            if not (0 <= values[0] <= 120 and all(0 <= v <= 1 for v in values[1:])):
                raise ValueError("Driving lap means outside observed channel bounds")
            if type(lap["samples"]) is not int or lap["samples"] < 0:
                raise ValueError("Invalid driving sample count")
        supported.append(all(lap["coverage"] >= 0.9 for lap in group))
        averages.append([mean(lap["means"][j] for lap in group) for j in range(5)])
    current = averages[0] if supported[0] else [0.0] * 5
    trend = (
        [groups[0][-1]["means"][j] - groups[0][0]["means"][j] for j in range(5)]
        if supported[0]
        else [0.0] * 5
    )
    differences = []
    for reference in (1, 2):
        differences.extend(
            [averages[0][j] - averages[reference][j] for j in range(5)]
            if supported[0] and supported[reference]
            else [0.0] * 5
        )
    return [*current, *trend, *differences, *[int(flag) for flag in supported]]


def base_vector(row: dict, nominations: dict, practice: dict) -> list[float]:
    """Reconstruct v17 input arithmetic through the earlier independent feature equations."""
    event = str(row["session"])
    when = datetime.fromtimestamp(row["forecast_at_s"], tz=timezone.utc)
    published, codes = nominations[event]
    if published >= when.date().isoformat() or when.year not in (2023, 2024, 2025):
        raise ValueError("Unavailable nomination or unsupported season")
    center = median(row["current_prefix_s"])
    values = trajectory_features(row, "full")
    values.extend(
        v - center for v in [*row["current_prefix_s"], *row["reference_target_s"]]
    )
    values.extend(int(c == row["compounds"][0]) for c in ("HARD", "MEDIUM", "SOFT"))
    season = [int(when.year == year) for year in (2023, 2024, 2025)]
    values.extend(season)
    lookup = dict(zip(("HARD", "MEDIUM", "SOFT"), codes, strict=True))
    identity = [
        int(number == lookup[c]) for c in row["compounds"] for number in range(1, 7)
    ]
    values.extend(identity)
    values.extend(year * flag for year in season for flag in identity)
    for compound in row["compounds"]:
        item = practice[event][compound]
        values.extend([item["drift_s"] or 0.0, log1p(item["drivers"])])
    return values


def audit() -> dict:
    """Audit stored summaries, scalar checkpoint inference, provenance and every race gate."""
    data, observed, result, previous, practice = [
        read_json(FOLDER / name)
        for name in (
            "compound-v11-development-data.json",
            "compound-v19-driving-data.json",
            "compound-v19-development.json",
            "compound-v17-development.json",
            "compound-v17-practice-trends.json",
        )
    ]
    for document in (data, observed, result, previous, practice):
        check_seal(document)
    compare(observed["dataset_sha256"], data["content_sha256"], "observed cohort seal")
    compare(result["driving_sha256"], observed["content_sha256"], "driving input seal")
    if type(observed["acquisition_ready"]) is not bool:
        raise ValueError("Driving acquisition readiness must be boolean")
    compare(
        result["acquisition_ready"],
        observed["acquisition_ready"],
        "acquisition readiness",
    )
    compare(result["v17_sha256"], previous["content_sha256"], "matched control seal")
    compare(
        practice["content_sha256"], previous["trends_sha256"], "practice input seal"
    )
    compare(practice["dataset_sha256"], data["content_sha256"], "practice cohort seal")
    for name, digest in result["hashes"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError("Driving audit source path escapes repository")
        compare(
            sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
            digest,
            "source hash",
        )
    documents = [
        read_json(FOLDER / name)
        for name in (
            "compound-nomination-inventory.json",
            "compound-v13-nomination-additions.json",
        )
    ]
    nominations = {}
    for document in documents:
        for source in document["sources"]:
            for event, codes in source["events"].items():
                if event in nominations:
                    raise ValueError("Duplicate driving-study nomination")
                nominations[event] = source["issued"], codes
    compare(sorted(nominations), sorted(data["sources"]), "nomination coverage")
    rows, summaries, model = data["cases"], observed["lap_summaries"], result["result"]
    compare(len(summaries), len(rows), "summary denominator")
    compare(
        sorted(model["models"]),
        sorted({str(r["session"]) for r in rows}),
        "checkpoint inventory",
    )
    compare(
        sorted(p["index"] for p in model["predictions"]),
        list(range(len(rows))),
        "prediction inventory",
    )
    for prediction in model["predictions"]:
        i = prediction["index"]
        row, checkpoint = rows[i], model["models"][str(rows[i]["session"])]
        x = base_vector(row, nominations, practice["events"]) + driving_vector(
            summaries[i]
        )
        z = []
        for value, center, scale in zip(
            x, checkpoint["center"], checkpoint["scale"], strict=True
        ):
            if not isfinite(scale) or scale <= 0:
                raise ValueError("Invalid driving checkpoint scale")
            z.append((value - center) / scale)
        raw = [
            b
            + sum(value * weight for value, weight in zip(z, weights, strict=True))
            + median(row["current_prefix_s"])
            - p
            for p, b, weights in zip(
                row["current_prefix_s"],
                checkpoint["intercept"],
                checkpoint["coefficients"],
                strict=True,
            )
        ]
        if len(raw) != 3 or not all(isfinite(value) for value in raw):
            raise ValueError("Invalid scalar driving prediction")
        laps = [
            p + min(2.0, max(-2.0, shift))
            for p, shift in zip(row["current_prefix_s"], raw, strict=True)
        ]
        compare(prediction["laps_s"], laps, "independent driving forecast")
        compare(
            prediction["bounded_laps"],
            sum(abs(v) > 2.0 for v in raw),
            "driving bound hits",
        )
    # Evaluate prediction arithmetic independently of the additional acquisition gate.
    prediction_qualified = model["qualified"]
    readiness_qualified = observed["acquisition_ready"] and prediction_qualified
    compare(
        result["development_qualified"],
        readiness_qualified,
        "combined development gate",
    )
    compare(
        result["new_holdout_acquisition_allowed"],
        readiness_qualified,
        "combined acquisition gate",
    )
    gate_document = {k: v for k, v in result.items() if k != "content_sha256"}
    gate_document.update(
        development_qualified=prediction_qualified,
        new_holdout_acquisition_allowed=prediction_qualified,
    )
    gates = check_result(data, seal(gate_document))
    gates["result_sha256"] = result["content_sha256"]
    return seal(
        {
            "schema": "compound-driving-scalar-audit-v19",
            "result_sha256": result["content_sha256"],
            "driving_sha256": observed["content_sha256"],
            "forecasts_verified": len(rows),
            "driving_feature_values_verified": 23 * len(rows),
            "acquisition_ready": observed["acquisition_ready"],
            "development_qualified": readiness_qualified,
            "race_gates": gates,
            "audit_passed": True,
            "scope": "STORED_LAP_SUMMARIES_FEATURE_ARITHMETIC_CHECKPOINT_INFERENCE_AND_GATES",
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, audit())
