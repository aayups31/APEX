"""Evaluate the frozen pre-race long-run model across whole held-out weekends."""

import argparse
from datetime import datetime, timezone
from math import log1p
from pathlib import Path

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.compound_allocation import features, inventory
from apexsim.research.evidence import check_seal, read_json, seal
from diagnose_compound_line import FOLDER, evaluate


def study():
    data, parent, archive, trends = [
        read_json(FOLDER / name)
        for name in (
            "compound-v11-development-data.json",
            "compound-v13-development.json",
            "compound-v17-practice-sources.json",
            "compound-v17-practice-trends.json",
        )
    ]
    for doc in (data, parent, archive, trends):
        check_seal(doc)
    if not (
        data["content_sha256"]
        == parent["dataset_sha256"]
        == trends["dataset_sha256"]
        == archive["dataset_sha256"]
        and archive["content_sha256"] == trends["archive_sha256"]
        and set(data["sources"]) == set(trends["events"]) == set(archive["events"])
    ):
        raise ValueError("Practice cohort or archive mismatch")
    allocation = inventory(
        [
            s
            for name in (
                "compound-nomination-inventory.json",
                "compound-v13-nomination-additions.json",
            )
            for s in read_json(FOLDER / name)["sources"]
        ],
        set(data["sources"]),
    )
    rows = data["cases"]
    matrix, support = [], []
    for row in rows:
        event = str(row["session"])
        session = archive["events"][event]["session"]
        when = datetime.fromtimestamp(row["forecast_at_s"], tz=timezone.utc)
        if session and datetime.fromisoformat(session["date_end"]) >= when:
            raise ValueError("Practice not complete by forecast")
        x = features(row, allocation, True)
        counts = []
        for compound in row["compounds"]:
            item = trends["events"][event][compound]
            counts.append(item["drivers"])
            x.extend([item["drift_s"] or 0.0, log1p(item["drivers"])])
        support.append(counts)
        matrix.append(x)
    result = evaluate(rows, data["sources"], np.asarray(matrix))
    previous = set(parent["recipes"]["nominated"]["failed_events"])
    failed = set(result["failed_events"])
    return seal(
        {
            "schema": "compound-practice-v17",
            "result": result,
            "trends_sha256": trends["content_sha256"],
            "control_sha256": parent["content_sha256"],
            "supporting_driver_counts": support,
            "gained_events": sorted(previous - failed),
            "lost_events": sorted(failed - previous),
            "development_qualified": result["qualified"],
            "new_holdout_acquisition_allowed": result["qualified"],
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, study())
