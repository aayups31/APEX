"""Construct additional R041 training windows only from verified opened archives."""

import argparse
from collections import defaultdict
from itertools import groupby, pairwise
from math import isfinite
from pathlib import Path

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from diagnose_compound_decision import ROOT
from prepare_compound_trajectory import (
    OPENED,
    V9,
    fastf1_field,
    field_stints,
    tables_from_archive,
)


def opened_field(event: str, source: dict, root: Path) -> list:
    if source["provider"] == "FASTF1":
        _, year, label = event.split("_")
        number = int(label[1:])
        assert_development_event(int(year), number, event_id=event)
        folder = (
            f"fastf1-2024-r{number}-race-20261011"
            if year == "2024"
            else f"r026-fastf1-2023-r{number}-race-20261013"
        )
        field, digest = fastf1_field(root / folder)
    elif source["provider"] == "OPENF1":
        sessions = {
            **OPENED,
            **{k: (*v, "r041-v9-confirmation-20261104") for k, v in V9.items()},
        }
        number, meeting, folder = sessions[int(event)]
        assert_development_event(2025, number)
        tables, digest = tables_from_archive(
            root / folder, int(event), (number, meeting)
        )
        field = field_stints(tables)
    else:
        raise ValueError("Unknown provider")
    if digest != source["archive_sha256"]:
        raise ValueError("Unpaired source is outside opened archive set")
    return field


def additional(event: str, stint: dict, occupied: set) -> list:
    """Exclude previously used ages first; partition every remaining contiguous run."""
    available = sorted(set(stint["values"]) - occupied)
    windows = []
    for _, items in groupby(enumerate(available), lambda item: item[1] - item[0]):
        run = [age for _, age in items]
        for start in range(0, len(run) - 11, 12):
            ages = run[start : start + 12]
            times = [stint["ends"][age] for age in ages]
            pace = [stint["values"][age] for age in ages]
            if not all(isfinite(t) for t in times) or any(
                b <= a for a, b in pairwise(times)
            ):
                raise ValueError("Unordered native window")
            if not all(isfinite(v) and v > 0 for v in pace):
                raise ValueError("Invalid native pace")
            windows.append(
                {
                    "session": event,
                    "driver": stint["driver"],
                    "stints": [None, stint["stint"]],
                    "compounds": [None, stint["compound"]],
                    "ages": ages,
                    "forecast_at_s": times[2],
                    "current_prefix_s": pace[:3],
                    "current_target_s": pace[-3:],
                    "target_end_s": times[-1],
                }
            )
    return windows


def prepare(root: Path) -> dict:
    original = read_json(ROOT / "docs/verification/compound-v11-development-data.json")
    check_seal(original)
    occupied = defaultdict(set)
    for row in original["cases"]:
        occupied[str(row["session"]), row["driver"], row["stints"][1]].update(
            row["ages"]
        )
    extra, counts = [], {}
    for event, source in original["sources"].items():
        count = len(extra)
        for stint in opened_field(event, source, root):
            extra.extend(
                additional(
                    event, stint, occupied[event, stint["driver"], stint["stint"]]
                )
            )
        counts[event] = len(extra) - count
    return seal(
        {
            "schema": "unpaired-development-training-v14",
            "parent_sha256": original["content_sha256"],
            "additional_windows": extra,
            "additional_by_source": counts,
            "scope": "TRAINING_ONLY_ENTIRE_EVALUATION_EVENT_EXCLUDED",
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--native-root", type=Path, default=ROOT / ".cache")
    args = parser.parse_args()
    write_manifest(args.output, prepare(args.native_root))
