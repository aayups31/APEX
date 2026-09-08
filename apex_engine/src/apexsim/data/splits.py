"""P1-08: explicit, immutable event-grouped session splits for public evidence."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pyarrow as pa

from apexsim.data.tables import read_dataset, validate_table
from apexsim.provenance import payload_sha256, write_manifest

SPLIT_VERSION = "apex-session-splits-v1"
PARTITIONS = ("train", "val", "test")


def validate_assignments(sessions: pa.Table, assignments: Mapping[str, Sequence[str]]) -> dict[str, list[str]]:
    """Require full coverage, nonempty partitions, and disjoint sessions AND events.

    Assignments are explicit so test selection is frozen by an experiment protocol,
    rather than silently rerandomized whenever a source session is added.
    """
    validate_table("sessions", sessions)
    if set(assignments) != set(PARTITIONS):
        raise ValueError("Splits require exactly train, val and test partitions")
    rows = {row["session_id"]: row for row in sessions.to_pylist()}
    source_sessions: set[tuple[str, str]] = set()
    for row in rows.values():
        identity = (row["source"], row["source_session_id"])
        if identity in source_sessions:
            raise ValueError(f"Duplicate source session identity: {identity}")
        source_sessions.add(identity)
    seen_sessions: set[str] = set()
    event_partition: dict[str, str] = {}
    round_partition: dict[tuple[int, int], str] = {}
    normalized = {}
    for partition in PARTITIONS:
        members = assignments[partition]
        if isinstance(members, (str, bytes)) or not isinstance(members, (list, tuple)) or not members:
            raise ValueError(f"{partition}: expected a nonempty session list")
        if any(not isinstance(member, str) or member not in rows for member in members):
            raise ValueError(f"{partition}: unknown session_id")
        if len(members) != len(set(members)) or seen_sessions.intersection(members):
            raise ValueError(f"{partition}: duplicate or overlapping session_id")
        for member in members:
            event = rows[member]["event_id"]
            if event in event_partition and event_partition[event] != partition:
                raise ValueError(f"Event leakage: {event!r} spans {event_partition[event]} and {partition}")
            event_partition[event] = partition
            row = rows[member]
            if row["round"] is not None:
                weekend = (row["season"], row["round"])
                if weekend in round_partition and round_partition[weekend] != partition:
                    raise ValueError(f"Event leakage: season/round {weekend} spans partitions")
                round_partition[weekend] = partition
        seen_sessions.update(members)
        normalized[partition] = sorted(members)
    if seen_sessions != set(rows):
        raise ValueError(f"Unassigned sessions: {sorted(set(rows) - seen_sessions)}")
    return normalized


def freeze_splits(dataset: str | Path, assignments: Mapping[str, Sequence[str]], output: str | Path, *, purpose: str) -> dict:
    """Write once, binding the split to the exact verified dataset and session file."""
    if Path(output).exists():
        raise FileExistsError(f"Split manifest already exists: {output}")
    if not isinstance(purpose, str) or not purpose.strip():
        raise ValueError("Split manifest requires an experiment purpose")
    tables, dataset_manifest = read_dataset(dataset)
    normalized = validate_assignments(tables["sessions"], assignments)
    payload = {
        "schema_version": SPLIT_VERSION,
        "dataset_sha256": dataset_manifest["content_sha256"],
        "sessions_sha256": dataset_manifest["tables"]["sessions"]["sha256"],
        "group_by": "event_id", "purpose": purpose,
        "partitions": normalized,
        "normalization_policy": "fit_on_train_only",
    }
    payload["content_sha256"] = payload_sha256(payload)
    write_manifest(output, payload)
    return payload


def load_splits(path: str | Path, dataset: str | Path, *, session_ids: Sequence[str] | None = None) -> dict:
    """Reject tampering, changed datasets, event leakage or mismatched telemetry."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    digest = payload.pop("content_sha256", None)
    if digest != payload_sha256(payload):
        raise ValueError("Split manifest content hash mismatch")
    if payload.get("schema_version") != SPLIT_VERSION or payload.get("group_by") != "event_id":
        raise ValueError("Unsupported split manifest schema or grouping")
    if payload.get("normalization_policy") != "fit_on_train_only" or not payload.get("purpose", "").strip():
        raise ValueError("Invalid split experiment policy")
    tables, manifest = read_dataset(dataset)
    if payload["dataset_sha256"] != manifest["content_sha256"] or payload["sessions_sha256"] != manifest["tables"]["sessions"]["sha256"]:
        raise ValueError("Split manifest dataset identity mismatch")
    normalized = validate_assignments(tables["sessions"], payload["partitions"])
    if session_ids is not None:
        expected = {session for members in normalized.values() for session in members}
        if set(session_ids) != expected:
            raise ValueError("Telemetry sessions do not exactly match frozen split sessions")
    payload["content_sha256"] = digest
    return payload
