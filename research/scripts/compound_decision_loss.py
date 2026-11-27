"""Learn a bounded shared lap shift using a joint timing and crossover loss."""

import argparse
from pathlib import Path

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.compound_bounded import training_weights
from apexsim.research.compound_readiness import LABELS, crossing
from apexsim.research.evidence import seal
from audit_compound_common_shift import MARGIN
from audit_compound_race_context import check_result
from audit_compound_repair import compare
from compound_sector_traffic import load_sources
from confirm_compound_multiseason import canonical_file_sha
from diagnose_compound_decision import contrasts
from diagnose_compound_line import score_forecasts
from prepare_compound_pit_exit import BASE
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler

PROTOCOL = BASE / "research/protocols/COMPOUND_DECISION_LOSS_V31.md"


def fit_shift(rows, matrix, decision_aware):
    weights = training_weights(rows)
    scaler = StandardScaler().fit(matrix, sample_weight=weights)
    x = np.column_stack((np.ones(len(rows)), scaler.transform(matrix)))
    levels, desired, signs, classes = [], [], [], []
    for row in rows:
        baseline = contrasts(row["reference_target_s"], row["current_prefix_s"])
        desired.append(
            [b - row[target] for b, (_, target) in zip(baseline, LABELS, strict=True)]
        )
        signs.append(
            [
                int(row[start] > MARGIN) - int(row[start] < -MARGIN)
                for start, _ in LABELS
            ]
        )
        classes.append(
            [1 if crossing(row[start], row[target]) else -1 for start, target in LABELS]
        )
        levels.append(baseline)
    direction, labels = np.asarray(signs), np.asarray(classes)
    threshold = np.asarray(levels) + MARGIN * direction
    target_shift = np.asarray(desired)
    balance = np.zeros_like(direction, dtype=float)
    if decision_aware:
        for label in (-1, 1):
            mass = weights[:, None] * ((direction != 0) & (labels == label))
            if not mass.sum():
                raise ValueError("Training fold lacks a crossover outcome class")
            balance += mass / (2 * mass.sum())
    normalized = weights / weights.sum()
    penalty = 10 / weights.sum()

    def objective(beta):
        shift = x @ beta
        residual = shift[:, None] - target_shift
        slack = np.maximum(
            0, MARGIN - labels * direction * (shift[:, None] - threshold)
        )
        loss = (
            normalized @ np.mean(residual**2, axis=1)
            + np.sum(balance * slack**2)
            + penalty * np.dot(beta[1:], beta[1:])
        )
        by_case = normalized * residual.mean(axis=1) - np.sum(
            balance * slack * labels * direction, axis=1
        )
        gradient = 2 * (x.T @ by_case)
        gradient[1:] += 2 * penalty * beta[1:]
        return loss, gradient

    solution = minimize(
        objective,
        np.zeros(x.shape[1]),
        jac=True,
        method="L-BFGS-B",
        options={"ftol": 1e-15, "gtol": 1e-9, "maxiter": 1000},
    )
    error = np.linalg.norm(objective(solution.x)[1], ord=np.inf)
    if not solution.success or not np.isfinite(error) or error > 1e-6:
        raise ValueError(f"Shared shift fitting failed stationarity check: {error}")
    return {
        "center": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "intercept": float(solution.x[0]),
        "coefficients": solution.x[1:].tolist(),
    }


def forecast(model, x, prefix):
    shift = float(
        np.asarray(model["coefficients"]) @ ((x - model["center"]) / model["scale"])
        + model["intercept"]
    )
    bounded = min(2.0, max(-2.0, shift))
    return [v + bounded for v in prefix], 3 * int(abs(shift) > 2.0)


def evaluate(data, base, *, decision_aware):
    rows = data["cases"]
    matrix = np.asarray(base)
    forecasts, models = {}, {}
    for event in sorted(data["sources"]):
        test = [i for i, row in enumerate(rows) if str(row["session"]) == event]
        if not test:
            continue
        train = [i for i, row in enumerate(rows) if str(row["session"]) != event]
        model = models[event] = fit_shift(
            [rows[i] for i in train], matrix[train], decision_aware
        )
        for i in test:
            prefix = rows[i]["current_prefix_s"]
            laps, hits = forecasts[i] = forecast(model, matrix[i], prefix)
            shift = model["intercept"] + sum(
                weight * (value - center) / scale
                for weight, value, center, scale in zip(
                    model["coefficients"],
                    base[i],
                    model["center"],
                    model["scale"],
                    strict=True,
                )
            )
            compare(
                laps,
                [min(v + 2, max(v - 2, v + shift)) for v in prefix],
                "shift checkpoint",
            )
            compare(hits, 3 * int(abs(shift) > 2), "shift bound")
    result = {**score_forecasts(rows, data["sources"], forecasts), "models": models}
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
    return result, audit


def run():
    data, control, base = load_sources()
    timing, timing_audit = evaluate(data, base, decision_aware=False)
    result, audit = evaluate(data, base, decision_aware=True)
    return seal(
        {
            "schema": "compound-decision-loss-v31",
            "dataset_sha256": data["content_sha256"],
            "control_sha256": control["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(PROTOCOL),
            "timing_only": timing,
            "timing_audit": timing_audit,
            "result": result,
            "audit": audit,
            "development_qualified": result["qualified"],
            "new_holdout_acquisition_allowed": result["qualified"],
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, run())
