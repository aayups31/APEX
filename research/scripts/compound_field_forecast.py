"""Replace privileged future-field features with race-held-out predictions."""

import argparse
from collections import defaultdict
from pathlib import Path
from statistics import mean

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.compound_allocation import forecast_laps
from apexsim.research.compound_bounded import training_weights
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_driving import base_vector
from audit_compound_race_context import check_result
from confirm_compound_multiseason import canonical_file_sha
from diagnose_compound_line import score_forecasts
from prepare_compound_pit_exit import BASE, FOLDER
from sklearn.linear_model import Ridge


def fit_field(training, contexts):
    x = np.asarray([c["causal"] for c in contexts])
    y = np.asarray([c["future_diagnostic"] for c in contexts])
    weights = training_weights(training)
    center = np.average(x, axis=0, weights=weights)
    scale = np.sqrt(np.average((x - center) ** 2, axis=0, weights=weights))
    scale[np.ptp(x, axis=0) == 0] = 1.0
    ridge = Ridge(alpha=10.0, solver="svd").fit(
        (x - center) / scale, y, sample_weight=weights
    )
    return {
        "center": center.tolist(),
        "scale": scale.tolist(),
        "coefficients": ridge.coef_.tolist(),
        "intercept": ridge.intercept_.tolist(),
    }


def predict_field(model, causal):
    z = (np.asarray(causal) - model["center"]) / model["scale"]
    output = (np.asarray(model["coefficients"]) @ z + model["intercept"]).tolist()
    for i in (0, 3):
        count = causal[i + 2]
        if count == 0:
            output[i : i + 3] = [0.0] * 3
        else:
            output[i + 1] = max(0.0, output[i + 1])
            output[i + 2] = min(count, max(0.0, output[i + 2]))
    return output


def field_errors(rows, contexts, predictions):
    results = {}
    for j, name in enumerate(("all_compounds", "same_compound")):
        offset = j * 3
        races = defaultdict(list)
        for i, (row, context) in enumerate(zip(rows, contexts, strict=True)):
            if context["future_peer_counts"][j]:
                observed = context["future_diagnostic"][offset]
                estimates = [predictions[i][offset], 0.0, 3 * context["causal"][offset]]
                races[str(row["session"])].append(
                    [abs(v - observed) for v in estimates]
                )
        events = {
            event: dict(
                zip(
                    ("forecast", "zero", "extrapolate"),
                    map(mean, zip(*values, strict=True)),
                    strict=True,
                )
            )
            for event, values in sorted(races.items())
        }
        results[name] = {
            "cases": sum(map(len, races.values())),
            "events": events,
            "macro_mae_s": {
                k: mean(e[k] for e in events.values())
                for k in ("forecast", "zero", "extrapolate")
            },
        }
    return results


def run():
    data, prev, control, practice, nominations = [
        read_json(FOLDER / f"compound-{name}.json")
        for name in (
            "v24-cohort",
            "v28-development",
            "v24-development",
            "v17-practice-trends",
            "v21-nominations",
        )
    ]
    for doc in (data, prev, control, practice, nominations):
        check_seal(doc)
    if (
        prev["dataset_sha256"],
        prev["control_sha256"],
        control["practice_sha256"],
        control["nominations_sha256"],
    ) != (
        data["content_sha256"],
        control["content_sha256"],
        practice["content_sha256"],
        nominations["content_sha256"],
    ):
        raise ValueError("Field forecast source mismatch")
    allocations = {
        event: (source["issued"], codes)
        for source in nominations["sources"]
        for event, codes in source["events"].items()
    }
    rows, contexts = data["cases"], prev["contexts"]
    if len(contexts) != len(rows):
        raise ValueError("Field context inventory changed")
    models, forecasts, estimates = {}, {}, {}
    for event, downstream in prev["future_field_diagnostic_only"]["models"].items():
        training = [i for i, r in enumerate(rows) if str(r["session"]) != event]
        model = models[event] = fit_field(
            [rows[i] for i in training], [contexts[i] for i in training]
        )
        for i, row in enumerate(rows):
            if str(row["session"]) == event:
                causal = contexts[i]["causal"]
                estimates[i] = predict_field(model, causal)
                vector = (
                    base_vector(row, allocations, practice["events"])
                    + causal
                    + estimates[i]
                )
                forecasts[i] = forecast_laps(
                    downstream, vector, row["current_prefix_s"]
                )
    result = score_forecasts(rows, data["sources"], forecasts)
    flags = {
        "development_qualified": result["qualified"],
        "new_holdout_acquisition_allowed": result["qualified"],
    }
    return seal(
        {
            "schema": "compound-field-forecast-v29",
            "dataset_sha256": data["content_sha256"],
            "parent_sha256": prev["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(
                BASE / "research/protocols/COMPOUND_FIELD_FORECAST_V29.md"
            ),
            "models": models,
            "field_estimates": [estimates[i] for i in range(len(rows))],
            "field_errors": field_errors(rows, contexts, estimates),
            "result": result,
            "audit": check_result(data, seal({"result": result, **flags})),
            **flags,
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, run())
