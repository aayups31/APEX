"""Reconstruct prior car proximity at the finish and intermediate timing points."""

import argparse
from bisect import bisect_left
from pathlib import Path
from statistics import mean

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_race_context import check_result
from compound_field_evolution import score
from compound_sectors import base_vector, native_sectors
from confirm_compound_multiseason import canonical_file_sha
from prepare_compound_pit_exit import BASE, FOLDER
from prepare_compound_pit_exit_telemetry import windows

PROTOCOL = BASE / "research/protocols/COMPOUND_SECTOR_TRAFFIC_V30.md"


def timing_points(indexed):
    """Finish, sector one, sector two, with timestamps of lap completion."""
    by_lap = {}
    crossings = [[], [], []]
    for (driver, end), split in indexed.items():
        points = [end]
        if split is not None:
            start = end - split["duration_s"]
            first, second, _ = split["sectors_s"]
            points.extend([start + first, start + first + second])
        by_lap[driver, end] = points
        for stream, time in zip(crossings, points):
            stream.append((time, driver, end))
    return by_lap, [sorted(stream) for stream in crossings]


def previous_car(stream, driver, time, cutoff):
    begin = bisect_left(stream, (time - 10,))
    stop = bisect_left(stream, (time,))
    for stamp, peer, lap_end in reversed(stream[begin:stop]):
        if peer != driver and lap_end <= cutoff:
            return [stamp, peer, lap_end]
    return None


def link(row, by_lap, crossings):
    driver, cutoff = row["driver"], row["forecast_at_s"]
    result = []
    for group in windows(row):
        laps = []
        for lap in group:
            end = lap["end_s"]
            if end > cutoff:
                raise ValueError("Subject timing point is after forecast cutoff")
            points = by_lap[driver, end]
            laps.append(
                [
                    [point, previous_car(stream, driver, point, cutoff)]
                    for point, stream in zip(points, crossings)
                ]
            )
        result.append(laps)
    return result


def feature_vectors(row, groups):
    finish, intermediate = [], []
    cutoff, driver = row["forecast_at_s"], row["driver"]
    for group, history in zip(groups, windows(row), strict=True):
        gaps = [[], [], []]
        for lap, known in zip(group, history, strict=True):
            if (
                len(lap) not in (1, 3)
                or lap[0][0] != known["end_s"]
                or lap[0][0] > cutoff
            ):
                raise ValueError("Subject split inventory changed")
            if len(lap) == 3 and not lap[1][0] < lap[2][0] < lap[0][0]:
                raise ValueError("Misordered subject sector crossings")
            for point_id, (stamp, peer) in enumerate(lap):
                gap = 10.0
                if peer is not None:
                    peer_stamp, peer_driver, peer_end = peer
                    gap = stamp - peer_stamp
                    if (
                        peer_driver == driver
                        or not 0 < gap <= 10.0
                        or not peer_stamp <= peer_end <= cutoff
                        or (point_id == 0 and peer_stamp != peer_end)
                    ):
                        raise ValueError("Ineligible peer timing point")
                gaps[point_id].append(gap)
        for i, values in enumerate(gaps):
            valid = len(values) == 3
            stats = (
                [
                    mean(values),
                    sum(v <= 1.5 for v in values) / 3,
                    values[-1] - values[0],
                ]
                if valid
                else [0.0, 0.0, 0.0]
            )
            if i == 0:
                if not valid:
                    raise ValueError("Incomplete finish timing")
                finish.extend(stats)
            else:
                intermediate.extend([*stats, float(valid)])
    return finish, intermediate


def load_sources():
    data, control, practice, nominations = [
        read_json(FOLDER / f"compound-{name}.json")
        for name in (
            "v24-cohort",
            "v24-development",
            "v17-practice-trends",
            "v21-nominations",
        )
    ]
    for doc in (data, control, practice, nominations):
        check_seal(doc)
    if (
        control["dataset_sha256"],
        control["practice_sha256"],
        control["nominations_sha256"],
    ) != (
        data["content_sha256"],
        practice["content_sha256"],
        nominations["content_sha256"],
    ):
        raise ValueError("Multi-point traffic parents disagree")
    allocation = {
        event: (source["issued"], codes)
        for source in nominations["sources"]
        for event, codes in source["events"].items()
    }
    base = [base_vector(row, allocation, practice["events"]) for row in data["cases"]]
    return data, control, base


def study(data, control, base, links):
    finish, multi_point = [], []
    for row, x, groups in zip(data["cases"], base, links, strict=True):
        line, sector = feature_vectors(row, groups)
        finish.append(x + line)
        multi_point.append(x + line + sector)
    line_result = score(data, finish)
    result = score(data, multi_point)
    flags = {
        "development_qualified": result["qualified"],
        "new_holdout_acquisition_allowed": result["qualified"],
    }
    coverage = {
        "cases_with_current_prefix_sectors": sum(
            all(len(lap) == 3 for lap in g[0]) for g in links
        ),
        "cases_with_current_latest_sector_peers": [
            sum(len(g[0][-1]) == 3 and g[0][-1][i][1] is not None for g in links)
            for i in (1, 2)
        ],
        "cases_with_current_latest_finish_peer": sum(
            g[0][-1][0][1] is not None for g in links
        ),
        "cases_with_intermediate_peer_in_current_prefix": sum(
            any(peer is not None for lap in g[0] for _, peer in lap[1:]) for g in links
        ),
    }
    return seal(
        {
            "schema": "compound-sector-traffic-v30",
            "dataset_sha256": data["content_sha256"],
            "control_sha256": control["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(PROTOCOL),
            "links": links,
            "coverage": coverage,
            "finish_only": line_result,
            "result": result,
            "audit": check_result(data, seal({"result": result, **flags})),
            **flags,
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


def run(root):
    data, control, base = load_sources()
    links = [None] * len(data["cases"])
    for event, source in data["sources"].items():
        by_lap, crossings = timing_points(native_sectors(root, event, source))
        for i, row in enumerate(data["cases"]):
            if str(row["session"]) == event:
                links[i] = link(row, by_lap, crossings)
    return study(data, control, base, links)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
