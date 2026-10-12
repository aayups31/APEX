"""R020 metadata-only reservation; no benchmark telemetry acquisition or modelling."""
from __future__ import annotations

import json
import re
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from apexsim.data.jolpica import verify_jolpica_archive
from apexsim.provenance import file_sha256, payload_sha256, write_manifest

RESERVATION_VERSION = "apex-permanent-benchmark-reservation-v1"
SELECTION = "calendar rounds divisible by four, excluding acquired/inspected development weekends"


def event_key(season: object, round_number: object) -> tuple[int, int]:
    if type(season) is not int or not 1950 <= season <= 2100 or type(round_number) is not int or not 1 <= round_number <= 100:
        raise ValueError("Benchmark identity requires integral season and round")
    return season, round_number


def event_id(key: tuple[int, int]) -> str:
    return f"F1_{key[0]}_R{key[1]:02d}"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sealed(value: dict) -> None:
    if value.get("content_sha256") != payload_sha256({k: v for k, v in value.items() if k != "content_sha256"}):
        raise ValueError("Benchmark reservation/input content hash mismatch")


def audit_managed_archive_identities(root: Path, corpus: dict) -> list[dict]:
    """Read only top-level archive identity metadata, conservatively excluding acquired events."""
    opened = {e["provider_session_keys"]["openf1"]: event_key(e["season"], e["round_number"])
              for e in corpus["entries"]}
    records = []
    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        manifest, snapshot = folder / "manifest.json", folder / "snapshot.json"
        path = manifest if manifest.is_file() else snapshot
        if path.is_file():
            value = _read(path)
            schema = value.get("schema_version")
            if schema in ("apex-fastf1-archive-v1", "apex-fastf1-snapshot-v1"):
                identity = value["identity"]
                key = event_key(identity["year"], identity["round_number"])
            elif schema in ("apex-openf1-archive-v1", "apex-openf1-snapshot-v1"):
                session = value["identity"]["session_key"]
                if session not in opened:
                    raise ValueError("Unresolved managed OpenF1 acquisition; supply reviewed development lineage first")
                key = opened[session]
            else:
                continue
            records.append({"path": folder.name, "event_id": event_id(key), "season": key[0], "round_number": key[1],
                            "basis": "archive/snapshot identity metadata", "metadata_file": path.name,
                            "metadata_sha256": file_sha256(path)})
        elif (folder / "cache").is_dir():
            # Conservative exclusion for the known incomplete FastF1 downloader naming convention.
            match = re.match(r"fastf1-(\d{4})-r(\d{1,2})-", folder.name)
            if not match:
                raise ValueError("Unresolved managed partial cache; cannot establish untouched membership")
            key = event_key(int(match[1]), int(match[2]))
            records.append({"path": folder.name, "event_id": event_id(key), "season": key[0], "round_number": key[1],
                            "basis": "conservative partial-cache directory query; not authoritative source identity",
                            "metadata_file": None, "metadata_sha256": None})
    return records


def selected_events(calendars: list[dict], excluded: set[tuple[int, int]]) -> list[dict]:
    result, seen = [], set()
    for calendar in calendars:
        for row in calendar["event_catalog"]["events"]:
            key = event_key(row["season"], row["round_number"])
            if key in seen or row["event_id"] != event_id(key):
                raise ValueError("Duplicate or aliased calendar event identity")
            seen.add(key)
            if key[1] % 4 == 0 and key not in excluded:
                result.append(row)
    return sorted(result, key=lambda r: (r["season"], r["round_number"]))


def freeze_benchmark_reservation(calendars: Sequence[str | Path], development_corpus: str | Path,
                                 evidence_root: str | Path, output: str | Path, *, purpose: str) -> dict:
    """Freeze systematic calendar membership before any benchmark payload is acquired."""
    destination, corpus_path, root = Path(output), Path(development_corpus), Path(evidence_root)
    if destination.exists():
        raise FileExistsError(f"Benchmark reservation already exists: {destination}")
    if not isinstance(purpose, str) or not purpose.strip() or len(calendars) < 2:
        raise ValueError("Benchmark requires a purpose and at least two calendar seasons")
    corpus = _read(corpus_path)
    _sealed(corpus)
    if corpus.get("schema_version") != "apex-development-event-corpus-v1" or corpus.get("role") != "DEVELOPMENT":
        raise ValueError("Benchmark requires verified development corpus metadata")
    inputs = {str(corpus_path): file_sha256(corpus_path)}
    snapshots = []
    for folder in map(Path, calendars):
        if destination.resolve().is_relative_to(folder.resolve()):
            raise ValueError("Benchmark output must be outside calendar archives")
        manifest = verify_jolpica_archive(folder)
        catalog = _read(folder / "events.json")
        snapshots.append({"archive_sha256": manifest["content_sha256"], "query": manifest["query"],
                          "environment": manifest["environment"], "event_catalog": catalog,
                          "events_file_sha256": file_sha256(folder / "events.json")})
        for name in ("manifest.json", "events.json"):
            inputs[str(folder / name)] = file_sha256(folder / name)
    if len({s["query"]["season"] for s in snapshots}) != len(snapshots):
        raise ValueError("Benchmark calendar seasons must be distinct")
    inspected = audit_managed_archive_identities(root, corpus)
    excluded = {event_key(e["season"], e["round_number"]) for e in corpus["entries"] + inspected}
    members = selected_events(snapshots, excluded)
    if len(members) < 2:
        raise ValueError("No sufficient untouched benchmark membership")
    if inputs != {path: file_sha256(path) for path in inputs} or inspected != audit_managed_archive_identities(root, corpus):
        raise ValueError("Benchmark metadata changed during reservation")
    result = {"schema_version": RESERVATION_VERSION, "purpose": purpose,
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "selection_rule": SELECTION,
              "scope": "ALL_SESSIONS_OF_WHOLE_EVENT", "role": "PERMANENT_BENCHMARK",
              "telemetry_acquired_by_this_task": False, "calibration_allowed": False,
              "development_corpus_sha256": corpus["content_sha256"], "calendars": snapshots,
              "excluded_event_keys": [list(k) for k in sorted(excluded)], "inspection_inventory": inspected,
              "members": members, "event_count": len(members), "implementation_sha256": file_sha256(Path(__file__)),
              "limitations": ["Reservation only; no acquired benchmark dataset or calibrated prediction claim.",
                              "Untouched claim covers managed APEX source/modelling history, not unknown external human exposure.",
                              "Technical metadata/QC access is separate from outcome inspection; no telemetry opened here.",
                              "No silent replacement for missing future source coverage; preserve these protected weekends."]}
    result["content_sha256"] = payload_sha256(result)
    write_manifest(destination, result)
    return result


def load_benchmark_reservation(path: str | Path, *, expected_digest: str | None = None) -> dict:
    """Validate the portable sealed membership without opening source telemetry."""
    result = _read(Path(path))
    _sealed(result)
    if expected_digest is not None and result["content_sha256"] != expected_digest:
        raise ValueError("Permanent benchmark policy digest mismatch")
    if (result.get("schema_version") != RESERVATION_VERSION or result.get("selection_rule") != SELECTION
            or result.get("scope") != "ALL_SESSIONS_OF_WHOLE_EVENT" or result.get("role") != "PERMANENT_BENCHMARK"
            or result.get("calibration_allowed") is not False or result.get("telemetry_acquired_by_this_task") is not False):
        raise ValueError("Unsupported benchmark reservation policy")
    excluded = {event_key(*key) for key in result["excluded_event_keys"]}
    expected = selected_events(result["calendars"], excluded)
    if result["members"] != expected or result["event_count"] != len(expected) or len(expected) < 2:
        raise ValueError("Benchmark selection/membership mismatch")
    return result
