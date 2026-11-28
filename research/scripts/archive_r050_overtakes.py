"""Archive the OpenF1 pass log for the fixed R050 FastF1 panel."""

import argparse
from pathlib import Path
from time import sleep

import requests
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from calibrate_pit_expanded import PARENT
from calibrate_pit_timing import BASE


def cohort(native_root):
    parent = read_json(PARENT)
    check_seal(parent)
    for event, expected in (parent["training"] | parent["evaluation"]).items():
        _, year, label = event.split("_")
        year, number = int(year), int(label[1:])
        assert_development_event(year, number, event_id=event)
        folder = (
            f"r026-fastf1-2023-r{number}-race-20261013"
            if year == 2023
            else f"fastf1-2024-r{number}-race-20261011"
        )
        yield event, year, native_root / folder, expected["source_sha256"]


def acquire(native_root, root):
    root.mkdir(parents=True, exist_ok=True)
    sessions = {}
    manifest = {}
    with requests.Session() as client:
        for event, year, native, expected in cohort(native_root):
            identity = read_json(native / "manifest.json")
            if identity["content_sha256"] != expected:
                raise ValueError(f"Incorrect native archive identity for {event}")
            day = identity["identity"]["t0_date"][:10]
            if year not in sessions:
                response = client.get(
                    "https://api.openf1.org/v1/sessions",
                    params={"year": year, "session_name": "Race"},
                    timeout=30,
                )
                response.raise_for_status()
                sessions[year] = response.json()
                sleep(2)
            (race,) = [r for r in sessions[year] if r["date_start"][:10] == day]
            path = root / f"{event}-overtakes.json"
            if not path.exists():
                response = client.get(
                    "https://api.openf1.org/v1/overtakes",
                    params={"session_key": race["session_key"]},
                    timeout=30,
                )
                response.raise_for_status()
                validate_passes(response.json(), race)
                with path.open("xb") as handle:
                    handle.write(response.content)
                sleep(2)
            validate_passes(read_json(path), race)
            manifest[event] = {
                "identity": race,
                "filename": path.name,
                "file_sha256": file_sha256(path),
            }
    write_manifest(root / "manifest.json", seal({"provider": "OPENF1", "events": manifest}))


def validate_passes(rows, identity):
    if (
        not isinstance(rows, list)
        or not rows
        or any(
            r["session_key"] != identity["session_key"] or r["meeting_key"] != identity["meeting_key"]
            for r in rows
        )
    ):
        raise ValueError("OpenF1 pass log is missing or has the wrong race identity")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    acquire(args.native_root, args.archive)
