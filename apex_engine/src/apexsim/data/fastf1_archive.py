"""Immutable FastF1 acquisition and verified, network-disabled cache reconstruction.

FastF1 cache settings are process-global. Each load runs in a fresh worker; offline
loads use a private copy so the frozen SQLite and parser cache are never mutated.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path, PurePosixPath

from apexsim.data.manifest import SourceManifest
from apexsim.provenance import file_sha256, payload_sha256, write_manifest

ARCHIVE_VERSION = "apex-fastf1-archive-v1"
SNAPSHOT_VERSION = "apex-fastf1-snapshot-v1"
REPLAY_VERSION = "apex-fastf1-replay-v1"
PACKAGES = ("fastf1", "pandas", "numpy", "pyarrow")
REQUIRED_TABLES = {"laps", "weather_data", "race_control_messages", "track_status", "session_status", "results"}
SESSION_NAMES = {"FP1": "Practice 1", "FP2": "Practice 2", "FP3": "Practice 3",
                 "Q": "Qualifying", "R": "Race", "S": "Sprint",
                 "SQ": "Sprint Qualifying", "SS": "Sprint Shootout"}


@dataclass(frozen=True)
class FastF1Query:
    """An exact calendar round avoids FastF1's fuzzy event-name matching."""

    year: int
    round_number: int
    session: str

    def __post_init__(self) -> None:
        for name, low, high in (("year", 2018, 2100), ("round_number", 1, 30)):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} must be an integer in [{low}, {high}]")
        if self.session not in SESSION_NAMES:
            raise ValueError("Unsupported FastF1 session code")


def validate_identity(query: FastF1Query, identity: dict) -> None:
    if (identity.get("year"), identity.get("round_number"), identity.get("session_name")) != (
        query.year, query.round_number, SESSION_NAMES[query.session],
    ):
        raise ValueError("FastF1 resolved a different season/round/session")


def environment_versions() -> dict[str, str]:
    """Parser and serialization versions are pinned by each archive's evidence."""
    try:
        packages = {name: version(name) for name in PACKAGES}
    except PackageNotFoundError as exc:
        raise RuntimeError("FastF1 archives require the real-data extra") from exc
    return {"python": sys.version.split()[0], **packages}


def _artifact_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        raise ValueError("Invalid archive artifact path")
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("Archive artifact path escapes its root")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("Archive artifact path escapes its root")
    return resolved


def _worker(query: FastF1Query, root: Path, *, offline: bool, timeout_s: int) -> dict:
    command = [sys.executable, "-m", "apexsim.data.fastf1_worker", str(root.resolve()),
               str(query.year), str(query.round_number), query.session]
    if offline:
        command.append("--offline")
    with (root / "worker.log").open("x", encoding="utf-8") as log:
        try:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=timeout_s, check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"FastF1 load timed out; inspect {root / 'worker.log'}") from exc
    if result.returncode != 0 or not (root / "snapshot.json").is_file():
        raise RuntimeError(f"FastF1 load failed; inspect {root / 'worker.log'}")
    return json.loads((root / "snapshot.json").read_text(encoding="utf-8"))


def _seal(path: Path, payload: dict) -> dict:
    payload["content_sha256"] = payload_sha256(payload)
    write_manifest(path, payload)
    return payload


def _read_sealed(path: Path, schema: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    digest = payload.pop("content_sha256", None)
    if digest != payload_sha256(payload):
        raise ValueError("FastF1 manifest content hash mismatch")
    if payload.get("schema_version") != schema:
        raise ValueError("Unsupported FastF1 manifest schema")
    payload["content_sha256"] = digest
    return payload


def _snapshot(root: Path) -> dict:
    snapshot = json.loads((root / "snapshot.json").read_text(encoding="utf-8"))
    if snapshot.get("schema_version") != SNAPSHOT_VERSION:
        raise ValueError("Unsupported FastF1 snapshot schema")
    import pyarrow.parquet as pq

    drivers = snapshot["identity"]["drivers"]
    if not drivers or len(set(drivers)) != len(drivers) or any(not re.fullmatch(r"[0-9]+", driver) for driver in drivers):
        raise ValueError("Invalid FastF1 snapshot driver inventory")
    expected_tables = REQUIRED_TABLES | {f"{kind}/{driver}" for kind in ("car_data", "pos_data") for driver in drivers}
    if set(snapshot["tables"]) != expected_tables:
        raise ValueError("Incomplete FastF1 snapshot table inventory")
    for name, record in snapshot["tables"].items():
        if not re.fullmatch(r"[a-z_]+(?:/[0-9]+)?", name):
            raise ValueError("Invalid FastF1 snapshot table name")
        path = _artifact_path(root, f"tables/{name}.parquet")
        if file_sha256(path) != record["sha256"]:
            raise ValueError(f"FastF1 snapshot hash mismatch: {name}")
        with pq.ParquetFile(path) as parquet:
            if parquet.metadata.num_rows != record["rows"] or record["rows"] <= 0:
                raise ValueError(f"FastF1 snapshot row count mismatch: {name}")
    if not snapshot.get("complete"):
        raise ValueError("FastF1 snapshot is incomplete")
    return snapshot


def download_fastf1_session(query: FastF1Query, output: str | Path, *, timeout_s: int = 1200) -> dict:
    """Acquire one full session, freeze all cache files, and publish its manifest last.

    The exported tables preserve FastF1 source columns and units. They are not the
    dense legacy feature CSV or the five canonical public tables; no values are filled.
    """
    environment_versions()
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    (root / "cache").mkdir()
    _worker(query, root, offline=False, timeout_s=timeout_s)
    snapshot = _snapshot(root)
    if snapshot["environment"] != environment_versions():
        raise ValueError("FastF1 worker environment mismatch")
    records = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "worker.log":
            relative = path.relative_to(root).as_posix()
            _artifact_path(root, relative)
            records[relative] = {"sha256": file_sha256(path), "bytes": path.stat().st_size}
    if not any(name.startswith("cache/") for name in records):
        raise ValueError("FastF1 returned no cache evidence")
    source = SourceManifest("fastf1", asdict(query), "https://docs.fastf1.dev/",
                            canonical_schema_version=SNAPSHOT_VERSION,
                            notes=["Native FastF1 tables include upstream reconstructions; not raw measured ground truth.",
                                   "HTTP and parser cache files are enumerated in the enclosing archive.",
                                   "Source-data rights remain with the respective providers."])
    source.add_request("fastf1.get_session", {**asdict(query), "backend": "fastf1"}, None)
    source.add_request("fastf1.Session.load", {"laps": True, "telemetry": True, "weather": True, "messages": True},
                       None, records=snapshot["tables"]["laps"]["rows"])
    manifest = {"schema_version": ARCHIVE_VERSION, "query": asdict(query),
                "environment": snapshot["environment"], "identity": snapshot["identity"],
                "source_manifest": source.to_dict(), "files": records}
    return _seal(root / "manifest.json", manifest)


def verify_fastf1_archive(path: str | Path) -> dict:
    """Verify hashes and inventory without unpickling any cache or making requests."""
    root = Path(path)
    manifest = _read_sealed(root / "manifest.json", ARCHIVE_VERSION)
    query = FastF1Query(**manifest["query"])
    validate_identity(query, manifest["identity"])
    source = dict(manifest["source_manifest"])
    digest = source.pop("content_sha256", None)
    if digest != payload_sha256(source) or source["source"] != "fastf1" or source["query"] != manifest["query"]:
        raise ValueError("FastF1 source manifest mismatch")
    for relative, record in manifest["files"].items():
        artifact = _artifact_path(root, relative)
        if not artifact.is_file() or file_sha256(artifact) != record["sha256"] or artifact.stat().st_size != record["bytes"]:
            raise ValueError(f"FastF1 archive artifact hash mismatch: {relative}")
    inventory = {p.relative_to(root).as_posix() for folder in ("cache", "tables") for p in (root / folder).rglob("*") if p.is_file()}
    recorded = {p for p in manifest["files"] if p.startswith(("cache/", "tables/"))}
    if inventory != recorded or "snapshot.json" not in manifest["files"]:
        raise ValueError("FastF1 archive inventory mismatch")
    snapshot = _snapshot(root)
    if snapshot["environment"] != manifest["environment"] or snapshot["identity"] != manifest["identity"]:
        raise ValueError("FastF1 snapshot identity mismatch")
    return manifest


def replay_fastf1_archive(archive: str | Path, output: str | Path, *, timeout_s: int = 1200) -> dict:
    """Rebuild in a fresh process with cached-only HTTP plus a socket audit guard.

    Only load archives created by a trusted local acquisition: FastF1's stage-two
    parser cache uses pickle. Hashes detect alteration, not malicious authorship.
    """
    root, destination = Path(archive), Path(output)
    if destination.exists():
        raise FileExistsError(f"Replay output already exists: {destination}")
    if destination.resolve().is_relative_to(root.resolve()):
        raise ValueError("Replay output must be outside the frozen archive")
    manifest = verify_fastf1_archive(root)
    if environment_versions() != manifest["environment"]:
        raise ValueError("FastF1 replay environment mismatch; use the archive's recorded versions")
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copytree(root / "cache", destination / "cache")
    _worker(FastF1Query(**manifest["query"]), destination, offline=True, timeout_s=timeout_s)
    rebuilt, expected = _snapshot(destination), _snapshot(root)
    mismatches = sorted(name for name in expected["tables"].keys() | rebuilt["tables"].keys()
                        if expected["tables"].get(name) != rebuilt["tables"].get(name))
    passed = not mismatches and rebuilt["identity"] == expected["identity"] and rebuilt["network_attempts"] == 0
    report = {"schema_version": REPLAY_VERSION, "archive_sha256": manifest["content_sha256"],
              "environment": rebuilt["environment"], "identity": rebuilt["identity"],
              "network_attempts": rebuilt["network_attempts"], "table_count": len(rebuilt["tables"]),
              "rows": {name: record["rows"] for name, record in rebuilt["tables"].items()},
              "mismatched_tables": mismatches, "passed": passed}
    # Also prove that the worker did not alter the original archive.
    verify_fastf1_archive(root)
    _seal(destination / "replay_report.json", report)
    if not passed:
        raise ValueError(f"FastF1 offline reconstruction differs; inspect {destination / 'replay_report.json'}")
    return report
