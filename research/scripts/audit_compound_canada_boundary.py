"""Check whether Canadian tyre-age disagreements follow the recorded pit exits."""

import argparse
from hashlib import sha256
from pathlib import Path

from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from diagnose_compound_line import FOLDER, ROOT
from prepare_compound_trajectory import OPENED, tables_from_archive


def audit(root: Path, cache: Path) -> dict:
    event = 9963
    number, meeting, folder = OPENED[event]
    tables, archive_hash = tables_from_archive(root / folder, event, (number, meeting))
    residuals = read_json(FOLDER / "compound-v22-residuals.json")
    inputs = read_json(FOLDER / "compound-v21-processed-data.json")
    for doc in (residuals, inputs):
        check_seal(doc)
    if (
        inputs["content_sha256"] != residuals["processed_sha256"]
        or inputs["origins"][str(event)]["native_archive_sha256"] != archive_hash
    ):
        raise ValueError("Canada boundary evidence uses different sources")
    stints = {(s["driver_number"], s["stint_number"]): s for s in tables["stints"]}
    pit_out = [
        (lap["driver_number"], lap["lap_number"])
        for lap in tables["laps"]
        if lap["is_pit_out_lap"] is True
    ]
    links = {(p["case"], p["key"], p["group"]): p for p in inputs["links"]}
    checks = []
    for conflict in residuals["source_conflicts"]:
        if "age" not in conflict["identity_differences"]:
            continue
        link = links[conflict["case"], conflict["key"], conflict["group"]]
        if not link["key"].startswith("2025-Canadian Grand Prix-"):
            raise ValueError("Unexpected age conflict identity")
        driver = link["driver"]
        stint = stints[driver, link["stint"]]
        exits = [
            lap
            for d, lap in pit_out
            if d == driver and stint["lap_start"] <= lap <= stint["lap_end"]
        ]
        if len(exits) != 1:
            raise ValueError("Ambiguous Canadian stint pit exit")
        age = stint["tyre_age_at_start"] + link["lap"] - exits[0] + 1
        url = link["url"].rsplit("/", 1)[0] + "/laptimes.json"
        receipt = read_json(cache / f"{sha256(url.encode()).hexdigest()}.receipt.json")
        check_seal(receipt)
        payload = cache / f"{receipt['body_sha256']}.body"
        if (receipt["url"], receipt["content_sha256"], file_sha256(payload)) != (
            url,
            link["metadata_sha256"],
            receipt["body_sha256"],
        ):
            raise ValueError("Canada exported stint source changed")
        exported = read_json(payload)
        earlier = exported["lap"].index(stint["lap_start"])
        first = exported["lap"].index(exits[0])
        checks.append(
            {
                "case": link["case"],
                "driver": driver,
                "lap": link["lap"],
                "stint": link["stint"],
                "reported_start_lap": stint["lap_start"],
                "recorded_exit_lap": exits[0],
                "export_stint_at_reported_start": exported["stint"][earlier],
                "export_stint_at_exit": exported["stint"][first],
                "export_pit_in_at_reported_start": exported["pin"][earlier],
                "export_pit_out_at_exit": exported["pout"][first],
                "age_from_recorded_exit": age,
                "frozen_age": link["age"],
                "export_age": conflict["identity_differences"]["age"][1],
            }
        )
    return seal(
        {
            "schema": "compound-canada-boundary-audit-v22",
            "event": event,
            "source_archive_sha256": archive_hash,
            "residual_sha256": residuals["content_sha256"],
            "checks": checks,
            "matching_exit_age": sum(
                c["age_from_recorded_exit"] == c["export_age"] for c in checks
            ),
            "scope": "CANADA_SOURCE_DISCREPANCY_DIAGNOSTIC",
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=ROOT / ".cache")
    parser.add_argument(
        "--cache", type=Path, default=ROOT / ".cache/r041-v20-snapshots"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, audit(args.native_root, args.cache))
