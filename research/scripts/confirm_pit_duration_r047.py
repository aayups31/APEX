"""Replay the frozen R047 model on the registered 2025 confirmation races."""

import argparse
from pathlib import Path

import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from calibrate_pit_timing import COLUMNS, canonical_file_sha, extract
from fit_pit_duration_race_shift import BASE, SCALES, evaluate

RACES = {
    1: ("albert_park", "Australian Grand Prix"),
    4: ("bahrain", "Bahrain Grand Prix"),
    6: ("miami", "Miami Grand Prix"),
    16: ("monza", "Italian Grand Prix"),
    18: ("marina_bay", "Singapore Grand Prix"),
}
FOLDER = BASE / "docs/verification"


def run(root):
    fitted = read_json(FOLDER / "pit-duration-r047-v1.json")
    decision = read_json(FOLDER / "pit-duration-r047-v2.json")
    for doc in (fitted, decision):
        check_seal(doc)
    if decision["parent_sha256"] != fitted["content_sha256"] or (
        decision["scale_multipliers"] != list(SCALES) or decision["passed"] is not True
    ):
        raise ValueError(
            "R047 distribution was not frozen and qualified for confirmation"
        )
    events = {}
    for number, (circuit, name) in RACES.items():
        assert_development_event(2025, number)
        archive = root / f"r047-fastf1-2025-r{number}"
        manifest = verify_fastf1_archive(archive)
        query = manifest["query"]
        if (query["year"], query["round_number"], query["session"]) != (
            2025,
            number,
            "R",
        ) or (manifest["identity"]["event_name"] != name):
            raise ValueError("Unexpected R047 confirmation race")
        stops, excluded = extract(
            pd.read_parquet(archive / "tables/laps.parquet", columns=COLUMNS)
        )
        events[f"F1_2025_R{number:02}"] = {
            "circuit": circuit,
            "stops": stops,
            "exclusions": excluded,
            "source_sha256": manifest["content_sha256"],
        }
    support = all(len(event["stops"]) >= 5 for event in events.values())
    scored = (
        evaluate(fitted["calibration"], events)
        if all(e["stops"] for e in events.values())
        else None
    )
    return seal(
        {
            "schema": "apex-pit-duration-r047-2025-confirmation",
            "development_sha256": decision["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "events": events,
            "result": scored,
            "support_passed": support,
            "passed": support and bool(scored and scored["passed"]),
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
