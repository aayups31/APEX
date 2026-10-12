"""Default permanent benchmark exclusion for managed development workflows."""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from pathlib import Path

from apexsim.data.benchmark_reservation import event_key, load_benchmark_reservation

DEFAULT_POLICY_PATH = Path(__file__).with_name("benchmark_policy.json")
DEFAULT_POLICY_SHA256 = "7d690115b7bcd0a52f20acdbf44e628e82efe556b48caf5ebe49b15e29b4ea7d"


def protected_events() -> set[tuple[int, int]]:
    """Fail closed if the package's sealed, pinned reservation is absent or altered."""
    if not DEFAULT_POLICY_PATH.is_file():
        raise RuntimeError("Permanent benchmark policy is missing; development access refused")
    policy = load_benchmark_reservation(DEFAULT_POLICY_PATH, expected_digest=DEFAULT_POLICY_SHA256)
    return {event_key(r["season"], r["round_number"]) for r in policy["members"]}


def assert_development_event(season: object, round_number: object, *, event_id: str | None = None) -> None:
    """Check numeric weekend identity and a canonical ID independently of session aliases."""
    key = event_key(season, round_number)
    if event_id is not None:
        match = re.fullmatch(r"F1_(\d{4})_R(\d{2})", event_id)
        if match and key != (int(match[1]), int(match[2])):
            raise ValueError("Conflicting benchmark event ID and season/round identity")
    if key in protected_events():
        raise ValueError(f"Permanent benchmark event {key[0]}/round {key[1]} is forbidden in development/calibration")


def assert_development_sessions(rows: Iterable[Mapping]) -> None:
    """Ordinary experiment partitions, including test, cannot contain permanent members."""
    protected = protected_events()
    for row in rows:
        season, round_number, label = row["season"], row["round"], row["event_id"]
        match = re.fullmatch(r"F1_(\d{4})_R(\d{2})", label)
        named = (int(match[1]), int(match[2])) if match else None
        if named is not None and (season != named[0] or (round_number is not None and round_number != named[1])):
            raise ValueError("Conflicting benchmark event ID and season/round identity")
        if round_number is not None:
            key = event_key(season, round_number)
        elif named is not None:
            key = named
        elif row.get("source") == "synthetic" and row.get("truth_labels", {}).get("event_id") == "SIMULATED":
            continue
        else:
            raise ValueError("Unresolved public event identity cannot enter development/calibration")
        if key in protected:
            raise ValueError(f"Permanent benchmark event {key[0]}/round {key[1]} is forbidden in ordinary experiment splits")
