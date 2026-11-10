"""Refit the frozen pit-exit study and independently replay its decisions."""

import argparse
from math import log1p
from pathlib import Path
from statistics import median

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.compound_allocation import features, fit, forecast_laps, inventory
from apexsim.research.compound_bounded import training_weights
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_driving import base_vector, driving_vector
from audit_compound_race_context import check_result
from audit_compound_repair import compare
from confirm_compound_multiseason import canonical_file_sha
from diagnose_compound_driving import driving_features
from diagnose_compound_line import score_forecasts
from prepare_compound_pit_exit import BASE, FOLDER, PROTOCOL

DELTA_S = 0.45
PENALTY = 10.0
TOLERANCE = 1e-7
PRIMARY = "robust_native"


def solve_huber(design, targets, weights):
    """Minimize weighted Huber loss by iteratively reweighted ridge."""
    penalty = np.eye(design.shape[1]) * PENALTY
    penalty[0, 0] = 0.0
    coefficients = []
    for target in targets.T:
        effective = weights
        for _ in range(1000):
            weighted = design.T * effective
            beta = np.linalg.solve(weighted @ design + penalty, weighted @ target)
            residual = design @ beta - target
            gradient = (
                design.T @ (weights * np.clip(residual, -DELTA_S, DELTA_S))
                + penalty @ beta
            )
            if np.linalg.norm(gradient, ord=np.inf) <= TOLERANCE * weights.sum() / 2:
                break
            effective = weights * DELTA_S / np.maximum(DELTA_S, np.abs(residual))
        else:
            raise ValueError("Robust pit-exit regression did not converge")
        coefficients.append(beta)
    return np.asarray(coefficients)


def targets(rows):
    return np.asarray(
        [
            [lap - median(row["current_prefix_s"]) for lap in row["current_target_s"]]
            for row in rows
        ]
    )


def fit_robust(rows, matrix):
    weights = training_weights(rows)
    center = np.average(matrix, axis=0, weights=weights)
    centered = matrix - center
    scale = np.sqrt(np.average(centered**2, axis=0, weights=weights))
    scale[np.ptp(matrix, axis=0) == 0] = 1.0
    design = np.column_stack((np.ones(len(rows)), centered / scale))
    beta = solve_huber(design, targets(rows), weights)
    return {
        "center": center.tolist(),
        "scale": scale.tolist(),
        "intercept": beta[:, 0].tolist(),
        "coefficients": beta[:, 1:].tolist(),
    }


def replay_checkpoint(model, vector, prefix):
    z = [
        (v - c) / s
        for v, c, s in zip(vector, model["center"], model["scale"], strict=True)
    ]
    offsets = [
        bias + sum(w * v for w, v in zip(coefs, z, strict=True))
        for bias, coefs in zip(model["intercept"], model["coefficients"], strict=True)
    ]
    changes = [
        median(prefix) + offset - pace
        for pace, offset in zip(prefix, offsets, strict=True)
    ]
    laps = [
        pace + min(2.0, max(-2.0, change))
        for pace, change in zip(prefix, changes, strict=True)
    ]
    return laps, sum(abs(v) > 2.0 for v in changes)


def audit_fit(model, rows, inputs, robust):
    """Check standardization and stationarity using independently built inputs."""
    weights = training_weights(rows)
    center, scale = np.asarray(model["center"]), np.asarray(model["scale"])
    beta = np.asarray(model["coefficients"])
    standardized = (inputs - center) / scale
    compare(
        np.average(standardized, axis=0, weights=weights).tolist(), [0.0] * len(center)
    )
    compare(
        np.average(standardized**2, axis=0, weights=weights).tolist(),
        (np.ptp(inputs, axis=0) != 0).astype(float).tolist(),
    )
    residual = standardized @ beta.T + model["intercept"] - targets(rows)
    if robust:
        residual = np.clip(residual, -DELTA_S, DELTA_S)
    influence = weights[:, None] * residual
    intercept = influence.sum(axis=0)
    slope = influence.T @ standardized + PENALTY * beta
    max_gradient = max(np.abs(intercept).max(), np.abs(slope).max()) / weights.sum()
    if not np.isfinite(max_gradient) or max_gradient > TOLERANCE:
        raise ValueError("Pit-exit checkpoint failed the independent fit audit")
    return float(max_gradient)


def evaluate(data, matrix, independent, *, robust=False):
    rows, sources = data["cases"], data["sources"]
    forecasts, models = {}, {}
    gradient = 0.0
    fit_model = fit_robust if robust else fit
    for event in sorted(sources):
        train = [i for i, row in enumerate(rows) if str(row["session"]) != event]
        test = [i for i, row in enumerate(rows) if str(row["session"]) == event]
        if not test:
            continue
        training_rows = [rows[i] for i in train]
        model = models[event] = fit_model(training_rows, matrix[train])
        gradient = max(
            gradient, audit_fit(model, training_rows, independent[train], robust)
        )
        for i in test:
            prefix = rows[i]["current_prefix_s"]
            laps, hits = forecast_laps(model, matrix[i], prefix)
            other, other_hits = replay_checkpoint(model, independent[i], prefix)
            compare(laps, other, "pit-exit forecast")
            compare(hits, other_hits, "pit-exit forecast bounds")
            forecasts[i] = laps, hits
    result = {**score_forecasts(rows, sources, forecasts), "models": models}
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
    return result, {**audit, "maximum_scaled_fit_gradient": gradient}


def study(data, observed):
    legacy, nominations, practice, old_control, old_native = [
        read_json(FOLDER / name)
        for name in (
            "compound-v11-development-data.json",
            "compound-v21-nominations.json",
            "compound-v17-practice-trends.json",
            "compound-v21-development.json",
            "compound-v23-development.json",
        )
    ]
    for item in (
        data,
        observed,
        legacy,
        nominations,
        practice,
        old_control,
        old_native,
    ):
        check_seal(item)
    if not (
        data["parent_sha256"]
        == practice["dataset_sha256"]
        == legacy["content_sha256"]
        == old_control["dataset_sha256"]
        == old_native["dataset_sha256"]
        and old_control["correction_sha256"] == nominations["content_sha256"]
        and data["content_sha256"] == observed["dataset_sha256"]
        and data["protocol_sha256_lf"] == canonical_file_sha(PROTOCOL)
        and observed["v23_sha256"] == old_native["native_sha256"]
    ):
        raise ValueError("Pit-exit development parents changed")
    alloc = inventory(nominations["sources"], set(data["sources"]))
    raw_nominations = {
        event: (source["issued"], codes)
        for source in nominations["sources"]
        for event, codes in source["events"].items()
    }
    control, native, independent_control, independent_native = [], [], [], []
    for row, groups in zip(data["cases"], observed["lap_summaries"], strict=True):
        x = features(row, alloc, True)
        for compound in row["compounds"]:
            item = practice["events"][str(row["session"])][compound]
            x.extend([item["drift_s"] or 0.0, log1p(item["drivers"])])
        check = base_vector(row, raw_nominations, practice["events"])
        with_native = x + driving_features(groups)
        verify_native = check + driving_vector(groups)
        compare(with_native, verify_native, "pit-exit feature vector")
        control.append(x)
        native.append(with_native)
        independent_control.append(check)
        independent_native.append(verify_native)
    base_x, native_x, base_check, native_check = map(
        np.asarray, (control, native, independent_control, independent_native)
    )
    results, audits = {}, {}
    for name, x, verification in (
        ("nomination_practice_ridge", base_x, base_check),
        ("native_ridge", native_x, native_check),
        (PRIMARY, native_x, native_check),
    ):
        results[name], audits[name] = evaluate(
            data, x, verification, robust=name == PRIMARY
        )
    paths = (
        PROTOCOL,
        Path(__file__),
        Path(__file__).with_name("prepare_compound_pit_exit.py"),
        Path(__file__).with_name("prepare_compound_pit_exit_telemetry.py"),
    )
    return seal(
        {
            "schema": "compound-pit-exit-development-v24",
            "dataset_sha256": data["content_sha256"],
            "telemetry_sha256": observed["content_sha256"],
            "practice_sha256": practice["content_sha256"],
            "nominations_sha256": nominations["content_sha256"],
            "previous_controls": {
                "nomination_practice_ridge": old_control["content_sha256"],
                "native_ridge": old_native["content_sha256"],
            },
            "source_sha256_lf": {
                p.relative_to(BASE).as_posix(): canonical_file_sha(p) for p in paths
            },
            "results": results,
            "independent_audits": audits,
            "primary": PRIMARY,
            "development_qualified": results[PRIMARY]["qualified"],
            "new_holdout_acquisition_allowed": results[PRIMARY]["qualified"],
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


def verify_replay(actual, expected):
    check_seal(expected)
    fields = (
        "dataset_sha256",
        "telemetry_sha256",
        "source_sha256_lf",
        "primary",
        "development_qualified",
        "new_holdout_acquisition_allowed",
        "candidate_accepted",
        "production_promotion",
    )
    for field in fields:
        compare(actual[field], expected[field], field)
    for name, result in actual["results"].items():
        compare(result, expected["results"][name], name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--telemetry", type=Path, required=True)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = study(read_json(args.data), read_json(args.telemetry))
    if args.expected:
        verify_replay(result, read_json(args.expected))
    write_manifest(args.output, result)
