from __future__ import annotations

import argparse
from pathlib import Path

from apexsim.data.manifest import SourceManifest
from apexsim.data.openf1_adapter import ingest_openf1_session
from apexsim.data.validate import validate_canonical_frame


def main() -> None:
    parser = argparse.ArgumentParser(description="Download one OpenF1 driver/session into APEX canonical CSV")
    parser.add_argument("session_key", type=int)
    parser.add_argument("driver_number", type=int)
    parser.add_argument("--sample-hz", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path("data/raw_downloads/openf1_session.csv"))
    args = parser.parse_args()

    frame = ingest_openf1_session(args.session_key, args.driver_number, args.output, args.sample_hz)
    report = validate_canonical_frame(frame, strict=False)
    manifest = SourceManifest(
        source="openf1",
        query={
            "session_key": args.session_key,
            "driver_number": args.driver_number,
            "sample_hz": args.sample_hz,
        },
        terms_url="https://openf1.org/docs/",
        notes=[f"contract_passed={report.passed}", "Historical access/terms must be reviewed at use time."],
    )
    manifest.add_file(args.output, rows=len(frame))
    manifest.save(args.output.with_suffix(".manifest.json"))
    print(report.to_dict())


if __name__ == "__main__":
    main()
