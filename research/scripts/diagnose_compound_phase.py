"""Test causal race-lap position and then the registered same-race feedback."""

import argparse
from pathlib import Path

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from diagnose_compound_feedback import race_forecasts
from diagnose_compound_line import FOLDER, evaluate, score_forecasts
from diagnose_compound_practice import practice_inputs


def phase_features(row, prefix_windows):
    numbers = []
    for native, history in zip(
        prefix_windows,
        (row["reference_history"][:3], row["current_history"][-3:]),
        strict=True,
    ):
        if len(history) != 3 or [p[2] for p in native] != [
            lap["pace_s"] for lap in history
        ]:
            raise ValueError("Race lap differs from frozen prefix")
        laps = [p[0] for p in native]
        if laps != list(range(int(laps[0]), int(laps[0]) + 3)) or laps[0] < 1:
            raise ValueError("Invalid prefix race laps")
        if any(lap["end_s"] > row["forecast_at_s"] for lap in history):
            raise ValueError("Unavailable race lap")
        numbers.append(laps[-1])
    reference, current = numbers
    if current <= reference:
        raise ValueError("Reference stint must precede current stint")
    return [current, current - reference]


def study():
    data, _, trends, _, matrix = practice_inputs()
    fuel, timing, previous = [
        read_json(FOLDER / name)
        for name in (
            "compound-v17-fuel-sensitivity.json",
            "compound-v16-feedback-clocks.json",
            "compound-v17-development.json",
        )
    ]
    for doc in (fuel, timing, previous):
        check_seal(doc)
    if (
        fuel["dataset_sha256"] != data["content_sha256"]
        or fuel["clocks_sha256"] != timing["content_sha256"]
        or previous["trends_sha256"] != trends["content_sha256"]
        or timing["dataset_sha256"] != data["content_sha256"]
    ):
        raise ValueError("Race phase input seal mismatch")
    rows = data["cases"]
    for i, (row, record) in enumerate(zip(rows, fuel["cases"], strict=True)):
        if record["index"] != i or record["event"] != str(row["session"]):
            raise ValueError("Race phase case identity mismatch")
        matrix[i].extend(phase_features(row, record["windows"][:2]))
    unadjusted = evaluate(rows, data["sources"], np.asarray(matrix))
    base = {p["index"]: p for p in unadjusted["predictions"]}
    forecasts, trace = {}, {}
    for event in data["sources"]:
        indices = [i for i, r in enumerate(rows) if str(r["session"]) == event]
        predictions, peers = race_forecasts(rows, base, timing["clocks"], indices)
        forecasts.update(predictions)
        trace.update(peers)
    primary = score_forecasts(rows, data["sources"], forecasts)
    return seal(
        {
            "schema": "compound-race-phase-v18",
            "result": primary,
            "phase_only": unadjusted,
            "feedback": [trace[i] for i in range(len(rows))],
            "fuel_sha256": fuel["content_sha256"],
            "v17_sha256": previous["content_sha256"],
            "development_qualified": primary["qualified"],
            "new_holdout_acquisition_allowed": primary["qualified"],
            "production_promotion": False,
            "candidate_accepted": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, study())
