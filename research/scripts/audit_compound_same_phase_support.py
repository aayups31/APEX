"""Count same-phase crossover study support without scoring any outcomes."""

import argparse
from collections import Counter, defaultdict, deque
from itertools import combinations, groupby
from pathlib import Path

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from compound_line_proximity import archive_laps
from confirm_compound_multiseason import canonical_file_sha
from confirm_compound_reference import tables_from_archive
from diagnose_compound_adaptation import field_stints
from prepare_compound_pit_exit import BASE, FOLDER, MAPPING, reanchor
from prepare_compound_trajectory import fastf1_field


def clean_field(native_root, event, source):
    if source["provider"] == "OPENF1":
        session = int(event)
        round_number, meeting, folder = MAPPING[session]
        tables, digest = tables_from_archive(
            native_root / folder, session, (round_number, meeting)
        )
        adjusted, _, _, _ = reanchor(tables)
        rows = field_stints(adjusted)
    elif source["provider"] == "FASTF1":
        _, year, race = event.split("_")
        number = int(race[1:])
        folder = (
            f"fastf1-2024-r{number}-race-20261011"
            if year == "2024"
            else f"r026-fastf1-2023-r{number}-race-20261013"
        )
        rows, digest = fastf1_field(native_root / folder)
    else:
        raise ValueError("Unknown same-phase source")
    if digest != source["archive_sha256"]:
        raise ValueError("Same-phase audit archive changed")
    return rows


def overlapping_ages(first, second, clocks):
    """Equal ages within one race lap and 30 seconds of one another."""
    for age in sorted(first["ends"].keys() & second["ends"].keys()):
        a, b = first["ends"][age], second["ends"][age]
        laps_apart = abs(clocks[a, first["driver"]][0] - clocks[b, second["driver"]][0])
        if laps_apart <= 1 and abs(a - b) <= 30:
            yield age, a, b


def sixth_pair_end(pairs):
    """Earliest availability under a deterministic nonreuse control rule."""
    left, right = set(), set()
    for a, b in sorted(pairs, key=lambda p: (max(p), *p)):
        if a not in left and b not in right:
            left.add(a)
            right.add(b)
            if len(left) == 6:
                return max(a, b)
    return None


def control_path(graph, start, destination, cutoff):
    """Check whether prior controls connect two drivers through the field."""
    pending = deque([(start, 0)])
    seen = {start}
    while pending:
        driver, depth = pending.popleft()
        for peer, clock in graph[driver]:
            if clock >= cutoff or peer in seen:
                continue
            if peer == destination:
                return depth + 1
            pending.append((peer, depth + 1))
            seen.add(peer)
    return None


def event_support(field, native):
    clocks = {(end, driver): (lap, elapsed) for end, driver, lap, elapsed in native}
    if len(clocks) != len(native):
        raise ValueError("Ambiguous same-phase timing")
    controls, candidates = defaultdict(set), defaultdict(list)
    for a, b in combinations(
        sorted(field, key=lambda row: (row["driver"], row["stint"])), 2
    ):
        if a["driver"] == b["driver"]:
            continue
        drivers = (a["driver"], b["driver"])
        overlap = list(overlapping_ages(a, b, clocks))
        if a["compound"] == b["compound"]:
            controls[drivers].update((u, v) for _, u, v in overlap)
            continue
        for _, group in groupby(
            enumerate(overlap), key=lambda item: item[1][0] - item[0]
        ):
            run = [row for _, row in group]
            for offset in range(0, len(run) - 11, 12):
                _, u, v = run[offset]
                candidates[drivers].append(
                    min(u - clocks[u, a["driver"]][1], v - clocks[v, b["driver"]][1])
                )
    # Prior matched controls must end before either lap in the new prefix starts.
    # A physical lap supplies at most one control pair for a driver pair.
    graph = defaultdict(list)
    for (a, b), pairs in controls.items():
        available = sixth_pair_end(pairs)
        if available is not None:
            graph[a].append((b, available))
            graph[b].append((a, available))
    paths, direct_pairs, connected_pairs = Counter(), set(), set()
    for drivers, windows in candidates.items():
        for time in windows:
            distance = control_path(graph, *drivers, time)
            if distance is not None:
                paths[distance] += 1
                connected_pairs.add(drivers)
                if distance == 1:
                    direct_pairs.add(drivers)
    return {
        "candidate_windows": sum(map(len, candidates.values())),
        "driver_pairs": len(candidates),
        "windows_with_six_prior_controls": paths[1],
        "driver_pairs_with_prior_controls": len(direct_pairs),
        "windows_with_connected_prior_controls": sum(paths.values()),
        "driver_pairs_with_connected_prior_controls": len(connected_pairs),
        "shortest_prior_control_paths": {
            str(k): count for k, count in sorted(paths.items())
        },
    }


def audit(data, native_root):
    check_seal(data)
    events = {}
    for event, source in data["sources"].items():
        field = clean_field(native_root, event, source)
        native = archive_laps(native_root, event, source)
        events[event] = event_support(field, native)
    return seal(
        {
            "schema": "compound-same-phase-support-v1",
            "scope": "OPENED_RACES_ONLY_MATCHABILITY_WITHOUT_CROSSOVER_OUTCOMES",
            "dataset_sha256": data["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "maximum_clock_gap_s": 30,
            "maximum_race_lap_gap": 1,
            "minimum_prior_same_compound_laps": 6,
            "events": events,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = read_json(FOLDER / "compound-v24-cohort.json")
    write_manifest(args.output, audit(data, args.native_root))
