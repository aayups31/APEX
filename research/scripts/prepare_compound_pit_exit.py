"""Rebuild and independently audit matched compound windows at native pit exits."""

import argparse
from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path

from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.compound_readiness import LABELS, crossing
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_cohort import compare_published, enumerate_cases, enumerate_fastf1
from confirm_compound_crossover import timestamp
from confirm_compound_multiseason import canonical_file_sha
from confirm_compound_reference import ENDPOINTS, build_cases, tables_from_archive
from diagnose_compound_adaptation import field_stints
from diagnose_compound_line import FOLDER
from prepare_compound_trajectory import BASE, OPENED, V9, attach

PROTOCOL = BASE / "research/protocols/COMPOUND_PIT_EXIT_V24.md"
MAPPING = {
    **OPENED,
    **{k: (*v, "r041-v9-confirmation-20261104") for k, v in V9.items()},
}


def delayed_exit(stint, laps):
    """Find the exact reported in-lap, next-lap pit-out boundary pattern."""
    start, end = stint.get("lap_start"), stint.get("lap_end")
    if type(start) is not int or type(end) is not int or start <= 1 or start >= end:
        return False
    first, second = laps.get(start, {}), laps.get(start + 1, {})
    return (
        first.get("is_pit_out_lap") is False
        and second.get("is_pit_out_lap") is True
        and bool(first.get("date_start"))
        and bool(second.get("date_start"))
        and timestamp(first["date_start"]) < timestamp(second["date_start"])
    )


def reanchor(tables):
    """Translate the age origin for the existing mask and window builders."""
    drivers = defaultdict(dict)
    for row in tables["laps"]:
        d, n = row["driver_number"], row["lap_number"]
        if n in drivers[d]:
            raise ValueError("Duplicate native driver/lap")
        drivers[d][n] = row
    stints, shifts, dispositions = [], {}, Counter()
    for row in tables["stints"]:
        driver = row["driver_number"]
        identity = driver, row["stint_number"]
        if identity in shifts:
            raise ValueError("Duplicate native stint")
        laps = drivers[driver]
        prior = row.get("tyre_age_at_start")
        usable = row["compound"] in ("SOFT", "MEDIUM", "HARD") and prior is not None
        start, end = row.get("lap_start"), row.get("lap_end")
        shifts[identity] = int(usable and delayed_exit(row, laps))
        if not usable or type(start) is not int or type(end) is not int or end < start:
            dispositions["unsupported_metadata"] += 1
        elif start == 1:
            dispositions["first_lap"] += 1
        else:
            exits = [
                n
                for n, lap in laps.items()
                if start <= n <= end and lap.get("is_pit_out_lap") is True
            ]
            dispositions[
                "delayed_exit"
                if shifts[identity]
                else "reported_exit"
                if start in exits
                else "other_exit_pattern"
                if exits
                else "no_observed_exit"
            ] += 1
            dispositions["multiple_exits"] += len(exits) > 1
        # The legacy mask still sees the original interval. The translated
        # origin is an internal coordinate, never a published provider prior.
        stints.append(
            {**row, "tyre_age_at_start": prior - 1} if shifts[identity] else row
        )
    return {**tables, "stints": stints}, drivers, shifts, dict(dispositions)


def independent_tables(raw):
    """Derive the shift from adjacent native flag transitions for the old audit."""
    ordered = sorted(
        raw["laps"], key=lambda row: (row["driver_number"], row["lap_number"])
    )
    candidates = {
        (left["driver_number"], left["lap_number"])
        for left, right in pairwise(ordered)
        if left["driver_number"] == right["driver_number"]
        and right["lap_number"] == left["lap_number"] + 1
        and left.get("is_pit_out_lap") is False
        and right.get("is_pit_out_lap") is True
        and left.get("date_start")
        and right.get("date_start")
        and timestamp(left["date_start"]) < timestamp(right["date_start"])
    }
    shifted, stints = set(), []
    for meta in raw["stints"]:
        driver, stint = meta["driver_number"], meta["stint_number"]
        first, last, prior = (
            meta["lap_start"],
            meta["lap_end"],
            meta.get("tyre_age_at_start"),
        )
        if (
            type(first) is int
            and type(last) is int
            and 1 < first < last
            and (driver, first) in candidates
            and prior is not None
            and meta["compound"] in {"SOFT", "MEDIUM", "HARD"}
        ):
            meta = {**meta, "tyre_age_at_start": prior - 1}
            shifted.add((driver, stint))
        stints.append(meta)
    return {**raw, "stints": stints}, shifted


def physical_windows(row, metadata):
    """Map each age in both blocks back to the actual native lap number."""
    windows = []
    for stint in row["stints"]:
        meta = metadata[row["driver"], stint]
        windows.append(
            tuple(
                meta["lap_start"] + age - meta["tyre_age_at_start"] - 1
                for age in row["ages"]
            )
        )
    return tuple(windows)


def compare_windows(before, after, original, updated):
    def index(rows, metadata):
        result = {}
        for row in rows:
            ref, current = physical_windows(row, metadata)
            key = row["driver"], tuple(row["stints"]), current
            if key in result:
                raise ValueError(
                    "Duplicate physical current window within a stint pair"
                )
            result[key] = ref, row
        return result

    old, new = index(before, original), index(after, updated)
    shared = old.keys() & new.keys()
    transitions = []
    for start, target in LABELS:
        counts = Counter(
            f"{int(crossing(old[k][1][start], old[k][1][target]))}"
            f"->{int(crossing(new[k][1][start], new[k][1][target]))}"
            for k in shared
        )
        transitions.append(dict(sorted(counts.items())))
    return {
        "added_current_windows_by_pair": len(new.keys() - old.keys()),
        "removed_current_windows_by_pair": len(old.keys() - new.keys()),
        "shared_current_windows_by_pair": len(shared),
        "changed_reference_windows": sum(old[k][0] != new[k][0] for k in shared),
        "reindexed_current_windows": sum(
            old[k][1]["ages"] != new[k][1]["ages"] for k in shared
        ),
        "label_transitions": transitions,
    }


def openf1_event(native_root, event, source, before, legacy):
    session = int(event)
    number, meeting, folder = MAPPING[session]
    root = native_root / folder
    tables, digest = tables_from_archive(root, session, (number, meeting))
    if digest != source["archive_sha256"]:
        raise ValueError("Pit-exit archive differs from the frozen cohort")
    manifest = read_json(root / "manifest.json")
    raw = {}
    for endpoint in ENDPOINTS:
        name = f"{session}-{endpoint}.json"
        if file_sha256(root / name) != manifest["files"][name]:
            raise ValueError("Pit-exit audit archive changed")
        raw[endpoint] = read_json(root / name)
    original_cases, original_report = enumerate_cases(raw, session)
    compare_published(legacy, event, source, original_cases, original_report)
    updated, drivers, shifts, dispositions = reanchor(tables)
    independent, independent_shifts = independent_tables(raw)
    if {key for key, shift in shifts.items() if shift} != independent_shifts:
        raise ValueError("Independent pit-exit anchor mismatch")
    rows, counts = build_cases(updated, session)
    fields = field_stints(updated)
    original_meta = {(s["driver_number"], s["stint_number"]): s for s in raw["stints"]}
    updated_meta = {
        (s["driver_number"], s["stint_number"]): s for s in updated["stints"]
    }
    for field in fields:
        identity = field["driver"], field["stint"]
        if shifts[identity]:
            meta = updated_meta[identity]
            anchor = meta["lap_start"] + 1
            exit_clock = timestamp(drivers[identity[0]][anchor]["date_start"])
            for age in field["values"]:
                lap = meta["lap_start"] + age - meta["tyre_age_at_start"] - 1
                if (
                    lap <= anchor
                    or timestamp(drivers[identity[0]][lap]["date_start"]) <= exit_clock
                ):
                    raise ValueError("Pit-exit anchor is unavailable at a retained lap")
    rebuilt = [attach(row, fields) for row in rows]
    expected, report = enumerate_cases(independent, session)
    if report["lap_exclusions"] != original_report["lap_exclusions"]:
        raise ValueError("Pit-exit correction changed physical lap eligibility")
    revision = {**source, **counts, "blocks": len(rebuilt)}
    compare_published({"cases": rebuilt}, event, revision, expected, report)
    changes = compare_windows(before, rebuilt, original_meta, updated_meta)
    report = {
        **report,
        **changes,
        "old_cases": len(before),
        "anchor_dispositions": dispositions,
        "shifted_stints": [list(key) for key in sorted(independent_shifts)],
        "independent_pair_denominators_checked": True,
    }
    return rebuilt, revision, report


def prepare(native_root):
    legacy = read_json(FOLDER / "compound-v11-development-data.json")
    panel = read_json(FOLDER / "compound-v23-pit-exit-panel.json")
    for doc in (legacy, panel):
        check_seal(doc)
    rows, sources, reports = [], {}, {}
    for event, source in legacy["sources"].items():
        before = [row for row in legacy["cases"] if str(row["session"]) == event]
        if source["provider"] == "OPENF1":
            cases, revision, report = openf1_event(
                native_root, event, source, before, legacy
            )
        elif source["provider"] == "FASTF1":
            _, year, round_text = event.split("_")
            number = int(round_text[1:])
            folder = (
                f"fastf1-2024-r{number}-race-20261011"
                if year == "2024"
                else f"r026-fastf1-2023-r{number}-race-20261013"
            )
            root = native_root / folder
            manifest = read_json(root / "manifest.json")
            query = manifest["query"]
            if (query["year"], query["round_number"], manifest["content_sha256"]) != (
                int(year),
                number,
                source["archive_sha256"],
            ):
                raise ValueError(
                    "Pit-exit FastF1 archive differs from the frozen cohort"
                )
            expected, report = enumerate_fastf1(root, event)
            compare_published(legacy, event, source, expected, report)
            cases, revision = before, source
            report = {
                **report,
                "old_cases": len(before),
                "native_tyre_life_preserved": True,
            }
        else:
            raise ValueError("Unknown pit-exit source provider")
        rows.extend(cases)
        sources[event], reports[event] = revision, report
        print(f"Audited {event}: {len(before)} -> {len(cases)} cases", flush=True)
    return seal(
        {
            "schema": "compound-pit-exit-cohort-v24",
            "scope": "PREVIOUSLY_OPENED_DEVELOPMENT_ONLY",
            "parent_sha256": legacy["content_sha256"],
            "panel_sha256": panel["content_sha256"],
            "protocol_sha256_lf": canonical_file_sha(PROTOCOL),
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "cases": rows,
            "sources": sources,
            "audit": reports,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, prepare(args.native_root))
