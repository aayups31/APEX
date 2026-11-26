"""Whole-race evaluation of the R041 sequential pace and drift model."""

import argparse
from collections import defaultdict
from pathlib import Path
from statistics import median

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.compound_trajectory import robust_line, validate_history
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_pit_exit_residuals import decision_report
from audit_compound_race_context import check_result
from audit_compound_repair import compare
from confirm_compound_multiseason import canonical_file_sha
from diagnose_compound_line import FOLDER, score_forecasts
from scipy.special import logsumexp

PROTOCOL = FOLDER.parents[1] / "research/protocols/COMPOUND_STINT_STATE_V26.md"


def reference_stats(rows):
    windows = {}
    for row in rows:
        validate_history(row)
        key = (
            str(row["session"]),
            row["compounds"][0],
            row["driver"],
            row["stints"][0],
            tuple(row["ages"]),
        )
        stats = robust_line(row["reference_history"])
        if windows.setdefault(key, stats) != stats:
            raise ValueError("Conflicting repeated reference history")
    return windows


def train_prior(windows, heldout, compound):
    races = defaultdict(list)
    matching = {event for event, c, *_ in windows if c == compound and event != heldout}
    pooled = len(matching) < 3
    for (event, c, *_), stats in windows.items():
        if event != heldout and (pooled or c == compound):
            races[event].append(stats)
    slopes = [median(s for s, _ in group) for group in races.values()]
    drift = median(slopes)
    return {
        "drift": drift,
        "drift_sd": max(0.03, 1.4826 * median(abs(s - drift) for s in slopes)),
        "noise": max(
            0.10,
            1.4826 * median(median(r for _, r in group) for group in races.values()),
        ),
        "training_events": sorted(races),
        "pooled_compounds": pooled,
    }


def forecast(row, model, asymmetric):
    validate_history(row)
    history = row["current_history"]
    origin = history[0]["age"]
    sigma = model["noise"]
    units = np.linspace(-4, 4, 51)
    slopes = model["drift"] + model["drift_sd"] * units
    levels = history[0]["pace_s"] + sigma * np.linspace(-3, 3, 61)[:, None]
    log_prior = np.broadcast_to(-0.5 * units**2, (61, 51))
    posterior = log_prior.copy()
    for lap in history:
        residual = (lap["pace_s"] - levels - slopes * (lap["age"] - origin)) / sigma
        likelihood = -0.5 * residual**2
        if asymmetric:
            likelihood = np.logaddexp(
                np.log(0.9) + likelihood, np.log(0.05) - (residual - 2) ** 2 / 8
            )
        posterior += likelihood
        posterior -= logsumexp(posterior)
    weights = np.exp(posterior)
    mean_level = np.sum(weights * levels)
    mean_slope = np.sum(weights * slopes)
    ages = np.asarray(row["ages"][-3:]) - origin
    delay = 0.2 * sigma if asymmetric else 0.0
    projected = mean_level + ages * mean_slope + delay

    # Independent batch calculation, integrating predictions over both states.
    t = np.asarray([p["age"] - origin for p in history])[:, None, None]
    y = np.asarray([p["pace_s"] for p in history])[:, None, None]
    errors = (y - (levels + t * slopes)) / sigma
    density = -(errors**2) / 2
    if asymmetric:
        tails = -0.5 * ((errors - 2) / 2) ** 2
        density = logsumexp(
            np.stack((density, tails)), b=np.reshape([0.9, 0.05], (2, 1, 1, 1)), axis=0
        )
    joint = log_prior + density.sum(axis=0)
    mass = np.exp(joint - joint.max())
    replay = [np.average(levels + age * slopes + delay, weights=mass) for age in ages]
    compare(projected.tolist(), replay, "batch state inference")
    prefix = np.asarray(row["current_prefix_s"])
    delta = projected - prefix
    return (prefix + np.clip(delta, -2, 2)).tolist(), int(np.sum(abs(delta) > 2))


def study():
    data, baseline, fuel = [
        read_json(FOLDER / name)
        for name in (
            "compound-v24-cohort.json",
            "compound-v24-development.json",
            "compound-v24-residual-audit.json",
        )
    ]
    for doc in (data, baseline, fuel):
        check_seal(doc)
    if not (
        data["content_sha256"] == baseline["dataset_sha256"] == fuel["dataset_sha256"]
        and fuel["result_sha256"] == baseline["content_sha256"]
    ):
        raise ValueError("State study inputs disagree")
    rows = data["cases"]
    stats = reference_stats(rows)
    priors, forecasts = {}, {"symmetric": {}, "asymmetric": {}}
    for i, row in enumerate(rows):
        event, compound = str(row["session"]), row["compounds"][1]
        local = priors.setdefault(event, {})
        if compound not in local:
            local[compound] = train_prior(stats, event, compound)
        for name, predictions in forecasts.items():
            predictions[i] = forecast(row, local[compound], name == "asymmetric")
    results, audits, residuals = {}, {}, {}
    for name, predictions in forecasts.items():
        result = results[name] = score_forecasts(rows, data["sources"], predictions)
        audits[name] = check_result(
            data,
            seal(
                {
                    "result": result,
                    "development_qualified": result["qualified"],
                    "new_holdout_acquisition_allowed": result["qualified"],
                }
            ),
        )
        residuals[name] = decision_report(
            fuel["cases"], sorted(result["predictions"], key=lambda p: p["index"])
        )
    control = baseline["results"]["nomination_practice_ridge"]
    return seal(
        {
            "schema": "compound-stint-state-v26",
            "dataset_sha256": data["content_sha256"],
            "baseline_sha256": baseline["content_sha256"],
            "fuel_sha256": fuel["content_sha256"],
            "implementation_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(PROTOCOL),
            "priors": priors,
            "results": results,
            "audits": audits,
            "fuel_diagnostics": residuals,
            "ridge_control": {k: control[k] for k in ("macro_mae_s", "failed_events")},
            "development_qualified": results["asymmetric"]["qualified"],
            "new_holdout_acquisition_allowed": results["asymmetric"]["qualified"],
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected", type=Path)
    args = parser.parse_args()
    result = study()
    if args.expected:
        expected = read_json(args.expected)
        check_seal(expected)
        for key in (
            "results",
            "priors",
            "fuel_diagnostics",
            "development_qualified",
            "protocol_sha256_lf",
            "dataset_sha256",
            "implementation_sha256_lf",
            "new_holdout_acquisition_allowed",
        ):
            compare(result[key], expected[key], key)
    write_manifest(args.output, result)
