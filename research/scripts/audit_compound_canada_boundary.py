"""Check whether Canadian tyre-age disagreements follow the recorded pit exits."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path

from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from diagnose_compound_line import FOLDER, ROOT
from prepare_compound_trajectory import OPENED, V9, tables_from_archive


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


def panel(root: Path, cache: Path) -> dict:
    """Check the pit-out convention across every matched known OpenF1 input lap."""
    inputs = read_json(FOLDER / "compound-v21-processed-data.json")
    data = read_json(FOLDER / "compound-v11-development-data.json")
    for doc in (inputs, data):
        check_seal(doc)
    if inputs["dataset_sha256"] != data["content_sha256"]:
        raise ValueError("Boundary panel cohort changed")
    mappings = {
        **OPENED,
        **{k: (*v, "r041-v9-confirmation-20261104") for k, v in V9.items()},
    }
    grouped = defaultdict(dict)
    for item in inputs["links"]:
        event = str(data["cases"][item["case"]]["session"])
        if data["sources"][event]["provider"] == "OPENF1":
            grouped[event][item["driver"], item["stint"], item["lap"]] = item
    counts, disagreements = {}, []
    for event, items in grouped.items():
        number, meeting, folder = mappings[int(event)]
        tables, archive_hash = tables_from_archive(
            root / folder, int(event), (number, meeting)
        )
        if archive_hash != data["sources"][event]["archive_sha256"]:
            raise ValueError("Boundary panel native source changed")
        stints = {(s["driver_number"], s["stint_number"]): s for s in tables["stints"]}
        exits = defaultdict(list)
        for lap in tables["laps"]:
            if lap["is_pit_out_lap"] is True:
                exits[lap["driver_number"]].append(lap["lap_number"])
        exported_by_driver = {}
        tallies = Counter()
        for (driver, stint, lap), link in sorted(items.items()):
            if driver not in exported_by_driver:
                url = link["url"].rsplit("/", 1)[0] + "/laptimes.json"
                receipt = read_json(
                    cache / f"{sha256(url.encode()).hexdigest()}.receipt.json"
                )
                check_seal(receipt)
                body = cache / f"{receipt['body_sha256']}.body"
                if (receipt["url"], receipt["content_sha256"], file_sha256(body)) != (
                    url,
                    link["metadata_sha256"],
                    receipt["body_sha256"],
                ):
                    raise ValueError("Boundary panel export changed")
                exported_by_driver[driver] = read_json(body)
            exported = exported_by_driver[driver]
            i = exported["lap"].index(lap)
            if (
                int(exported["dNum"][i]),
                exported["stint"][i],
                exported["compound"][i],
            ) != (driver, stint, link["compound"]):
                tallies["incompatible_identity"] += 1
                continue
            native = stints[driver, stint]
            reported = native["lap_start"]
            expected = native["tyre_age_at_start"] + lap - reported + 1
            if expected != link["age"]:
                raise ValueError("Frozen age differs from reported-start formula")
            observed = exported["life"][i]
            candidates = [
                v
                for v in exits[driver]
                if reported <= v <= lap and v <= native["lap_end"]
            ]
            eligible = reported > 1 and len(candidates) == 1
            corrected = expected - (candidates[0] - reported) if eligible else expected
            tallies["matched_identity"] += 1
            tallies["exit_available"] += eligible
            tallies["original_disagrees"] += expected != observed
            tallies["exit_rule_disagrees"] += corrected != observed
            tallies["repairs"] += expected != observed and corrected == observed
            tallies["new_conflicts"] += expected == observed and corrected != observed
            if expected != observed or corrected != observed:
                disagreements.append(
                    {
                        "event": event,
                        "driver": driver,
                        "stint": stint,
                        "lap": lap,
                        "original_age": expected,
                        "exit_age": corrected,
                        "export_age": observed,
                    }
                )
        counts[event] = dict(tallies)
    return seal(
        {
            "schema": "compound-pit-exit-panel-v23",
            "input_sha256": inputs["content_sha256"],
            "scope": "KNOWN_LAP_AGE_DIAGNOSTIC_ONLY",
            "counts": counts,
            "disagreements": disagreements,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=ROOT / ".cache")
    parser.add_argument(
        "--cache", type=Path, default=ROOT / ".cache/r041-v20-snapshots"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--panel", action="store_true")
    args = parser.parse_args()
    build = panel if args.panel else audit
    write_manifest(args.output, build(args.native_root, args.cache))
