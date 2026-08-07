from __future__ import annotations

import argparse
from pathlib import Path

from apexsim.data.fastf1_adapter import ingest_fastf1_session
from apexsim.data.manifest import SourceManifest
from apexsim.data.validate import validate_canonical_frame


def main() -> None:
    parser = argparse.ArgumentParser(description="Download one FastF1 driver/session into APEX canonical CSV")
    parser.add_argument("year", type=int)
    parser.add_argument("event")
    parser.add_argument("session", help="FP1, FP2, FP3, Q, S or R")
    parser.add_argument("driver", help="Driver abbreviation such as VER")
    parser.add_argument("--sample-hz", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("data/raw_downloads/fastf1_session.csv"))
    args = parser.parse_args()

    frame = ingest_fastf1_session(
        args.year, args.event, args.session, args.driver, args.output, args.sample_hz
    )
    report = validate_canonical_frame(frame, strict=False)
    manifest = SourceManifest(
        source="fastf1",
        query={
            "year": args.year,
            "event": args.event,
            "session": args.session,
            "driver": args.driver,
            "sample_hz": args.sample_hz,
        },
        terms_url="https://docs.fastf1.dev/",
        notes=[f"contract_passed={report.passed}", "Do not redistribute bulk source data without reviewing terms."],
    )
    manifest.add_file(args.output, rows=len(frame))
    manifest.save(args.output.with_suffix(".manifest.json"))
    print(report.to_dict())


if __name__ == "__main__":
    main()
