"""Lossless source-response archives, explicit endpoint coverage and offline replay.

No temporal joins, unit conversions, filling or canonical feature construction occur
here. JSONL tables preserve decoded source values; original HTTP body bytes remain raw.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

import requests

from apexsim import __version__
from apexsim.data.manifest import SourceManifest, SourceRequest
from apexsim.data.openf1_http import BASE_URL, DownloadPolicy, OpenF1Client
from apexsim.provenance import file_sha256, payload_sha256, write_manifest

ARCHIVE_VERSION = "apex-openf1-archive-v1"
SNAPSHOT_VERSION = "apex-openf1-snapshot-v1"
REPLAY_VERSION = "apex-openf1-replay-v1"
SHARED_ENDPOINTS = ("laps", "stints", "weather", "race_control", "pit", "position", "intervals",
                    "overtakes", "session_result", "starting_grid", "team_radio",
                    "championship_drivers", "championship_teams")
TELEMETRY_ENDPOINTS = ("car_data", "location")
ENDPOINTS = ("sessions", "meetings", "drivers", *SHARED_ENDPOINTS, *TELEMETRY_ENDPOINTS)
REQUIRED_NONEMPTY = {"sessions", "meetings", "drivers", "laps", "weather", "car_data", "location"}


def _positive_int(value: int, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer; aliases such as latest are not frozen identities")
    return value


def _path(root: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    if not name or "\\" in name or ":" in name or relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Invalid OpenF1 artifact path")
    result = root / relative
    if not result.resolve().is_relative_to(root.resolve()):
        raise ValueError("OpenF1 artifact path escapes archive")
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON constant: {value}")


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _decode(body: bytes, status: int) -> tuple[object, list[dict]]:
    payload = json.loads(body, parse_constant=_reject_constant, object_pairs_hook=_unique_object)
    if status == 404 and payload == {"detail": "No results found."}:
        return payload, []
    if status != 200:
        raise ValueError(f"OpenF1 HTTP {status} is not a successful data response")
    if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
        raise ValueError("OpenF1 data response must be a list of objects")
    # Also reject numbers such as 1e999, which Python's JSON parser converts to inf.
    json.dumps(payload, allow_nan=False)
    return payload, payload


def _identity(rows: list[dict], session_key: int, *, historical: bool) -> dict:
    if len(rows) != 1 or type(rows[0].get("session_key")) is not int or rows[0]["session_key"] != session_key:
        raise ValueError("OpenF1 must resolve exactly the requested session")
    identity = rows[0]
    _positive_int(identity.get("meeting_key"), "meeting_key")
    if type(identity.get("year")) is not int or identity["year"] < 2023:
        raise ValueError("OpenF1 historical sessions require year >= 2023")
    dates = [datetime.fromisoformat(identity[name]) for name in ("date_start", "date_end")]
    if any(date.tzinfo is None for date in dates) or dates[0] >= dates[1]:
        raise ValueError("OpenF1 session dates must be timezone-aware and ordered")
    if historical and dates[1] + timedelta(minutes=30) >= datetime.now(timezone.utc):
        raise ValueError("OpenF1 acquisition requires a completed historical session")
    return identity


def _drivers(rows: list[dict]) -> list[int]:
    drivers = [_positive_int(row.get("driver_number"), "driver_number") for row in rows]
    if not drivers or len(set(drivers)) != len(drivers):
        raise ValueError("OpenF1 driver inventory is empty or duplicated")
    return sorted(drivers)


def _plan(session_key: int, meeting_key: int, drivers: list[int]) -> list[tuple[str, dict]]:
    shared = {"session_key": session_key}
    return [("sessions", shared), ("meetings", {"meeting_key": meeting_key}), ("drivers", shared),
            *((name, shared) for name in SHARED_ENDPOINTS),
            *((name, {**shared, "driver_number": driver}) for name in TELEMETRY_ENDPOINTS for driver in drivers)]


def _check_rows(endpoint: str, rows: list[dict], query: dict, meeting_key: int, drivers: list[int]) -> None:
    for row in rows:
        for name, expected in {**query, "meeting_key": meeting_key}.items():
            if type(row.get(name)) is not int or row[name] != expected:
                raise ValueError(f"OpenF1 {endpoint} row has wrong or missing {name}")
        if row.get("driver_number") is not None and (
                type(row["driver_number"]) is not int or row["driver_number"] not in drivers):
            raise ValueError(f"OpenF1 {endpoint} refers to an unknown driver")


def _table(rows: list[dict]) -> tuple[bytes, dict]:
    fields = sorted({key for row in rows for key in row})
    body = b"".join((json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                               allow_nan=False) + "\n").encode("utf-8") for row in rows)
    record = {"rows": len(rows), "fields": fields,
              "null_counts": {key: sum(key in row and row[key] is None for row in rows) for key in fields},
              "missing_counts": {key: sum(key not in row for row in rows) for key in fields},
              "driver_rows": dict(sorted(Counter(str(row["driver_number"]) for row in rows
                                                  if row.get("driver_number") is not None).items())),
              "availability": "nonempty" if rows else "empty_source_response"}
    return body, record


def _build_tables(root: Path, records: list[dict], session_key: int, output: Path | None = None) -> dict:
    """Derive tables only from recorded raw responses; optionally write to a fresh directory."""
    if len(records) < 3:
        raise ValueError("OpenF1 request inventory is incomplete")
    loaded: dict[str, list[dict]] = {name: [] for name in ENDPOINTS}
    identity = _identity(_decode(_path(root, records[0]["raw_path"]).read_bytes(),
                                 records[0]["status_code"])[1], session_key, historical=False)
    drivers = _drivers(_decode(_path(root, records[2]["raw_path"]).read_bytes(), records[2]["status_code"])[1])
    expected = _plan(session_key, identity["meeting_key"], drivers)
    if [(r["endpoint"], r["query"]) for r in records] != expected:
        raise ValueError("OpenF1 request inventory does not match the full endpoint/driver plan")
    for index, record in enumerate(records):
        if record["raw_path"] != f"raw/{index:04d}.json":
            raise ValueError("OpenF1 raw response inventory is not one-to-one")
        raw = _path(root, record["raw_path"])
        if raw.stat().st_size != record["bytes"] or file_sha256(raw) != record["sha256"]:
            raise ValueError("OpenF1 raw response hash mismatch")
        payload, rows = _decode(raw.read_bytes(), record["status_code"])
        if len(rows) != record["rows"] or payload_sha256(payload) != record["payload_sha256"]:
            raise ValueError("OpenF1 response row count or payload hash mismatch")
        _check_rows(record["endpoint"], rows, record["query"], identity["meeting_key"], drivers)
        loaded[record["endpoint"]].extend(rows)
    if len(loaded["meetings"]) != 1:
        raise ValueError("OpenF1 must resolve exactly one meeting")
    missing = [name for name in sorted(REQUIRED_NONEMPTY) if not loaded[name]]
    if missing:
        raise ValueError(f"OpenF1 required endpoints are empty: {missing}")
    lap_drivers = {row.get("driver_number") for row in loaded["laps"]}
    if None in lap_drivers:
        raise ValueError("OpenF1 lap rows require driver_number")
    for name in TELEMETRY_ENDPOINTS:
        if not lap_drivers.issubset({row["driver_number"] for row in loaded[name]}):
            raise ValueError(f"OpenF1 {name} is missing a lap driver's stream")
    tables = {}
    if output is not None:
        (output / "tables").mkdir(parents=True, exist_ok=False)
    from hashlib import sha256

    for endpoint, rows in loaded.items():
        body, record = _table(rows)
        tables[endpoint] = {**record, "sha256": sha256(body).hexdigest(), "bytes": len(body)}
        if output is not None:
            with (output / "tables" / f"{endpoint}.jsonl").open("xb") as handle:
                handle.write(body)
    return {"schema_version": SNAPSHOT_VERSION, "identity": identity, "drivers": drivers, "tables": tables,
            "empty_endpoints": sorted(name for name, record in tables.items() if record["rows"] == 0)}


def _seal(path: Path, payload: dict) -> dict:
    result = {**payload, "content_sha256": payload_sha256(payload)}
    write_manifest(path, result)
    return result


def download_openf1_session(session_key: int, output: str | Path, *, policy: DownloadPolicy | None = None) -> dict:
    """Freeze all 18 endpoint families; telemetry queries are partitioned by driver.

    The directory must be new. Publish the completion manifest only after the entire
    query plan validates. Preserve partial responses on failure for diagnosis.
    """
    _positive_int(session_key, "session_key")
    policy = policy or DownloadPolicy()
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    (root / "raw").mkdir()
    client = OpenF1Client(policy)
    records = []
    source = SourceManifest("openf1", {"session_key": session_key}, "https://openf1.org/",
                            license_id="CC-BY-NC-SA-4.0", canonical_schema_version=SNAPSHOT_VERSION,
                            notes=["Source values may include upstream reconstructions; no APEX filling or alignment.",
                                   "Empty responses are preserved; they do not prove that no real event occurred.",
                                   "Team-radio URLs are metadata only; linked audio is not downloaded."])

    def acquire(endpoint: str, query: dict) -> list[dict]:
        body, metadata = client.get(endpoint, query)
        relative = f"raw/{len(records):04d}.json"
        raw = root / relative
        with raw.open("xb") as handle:
            handle.write(body)
        # Save HTTP metadata even when payload validation subsequently fails.
        write_manifest(raw.with_suffix(".request.json"), {"endpoint": endpoint, "query": query, **metadata})
        payload, rows = _decode(body, metadata["status_code"])
        record = {"endpoint": endpoint, "query": query, "raw_path": relative, **metadata,
                  "sha256": file_sha256(raw), "bytes": len(body), "rows": len(rows),
                  "payload_sha256": payload_sha256(payload)}
        records.append(record)
        source.requests.append(SourceRequest(f"{BASE_URL}/{endpoint}", dict(query), metadata["retrieved_at_utc"],
                                              len(rows), record["payload_sha256"]))
        return rows

    try:
        identity = _identity(acquire("sessions", {"session_key": session_key}), session_key, historical=True)
        acquire("meetings", {"meeting_key": identity["meeting_key"]})
        drivers = _drivers(acquire("drivers", {"session_key": session_key}))
        for endpoint, query in _plan(session_key, identity["meeting_key"], drivers)[3:]:
            acquire(endpoint, query)
    finally:
        client.close()
    snapshot = _build_tables(root, records, session_key, root)
    write_manifest(root / "snapshot.json", snapshot)
    files = {path.relative_to(root).as_posix(): {"sha256": file_sha256(path), "bytes": path.stat().st_size}
             for path in sorted(root.rglob("*")) if path.is_file()}
    manifest = {"schema_version": ARCHIVE_VERSION, "query": {"session_key": session_key},
                "identity": identity, "environment": {"python": sys.version.split()[0], "apexsim": __version__,
                                                       "requests": requests.__version__},
                "download_policy": asdict(policy), "requests": records, "source_manifest": source.to_dict(),
                "files": files}
    return _seal(root / "manifest.json", manifest)


def verify_openf1_archive(archive: str | Path) -> dict:
    """Verify exact inventory, request coverage and raw-to-table equivalence without HTTP."""
    root = Path(archive)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    digest = manifest.pop("content_sha256", None)
    if digest != payload_sha256(manifest):
        raise ValueError("OpenF1 manifest content hash mismatch")
    if manifest.get("schema_version") != ARCHIVE_VERSION:
        raise ValueError("Unsupported OpenF1 archive schema")
    session_key = _positive_int(manifest["query"]["session_key"], "session_key")
    for name, record in manifest["files"].items():
        path = _path(root, name)
        if not path.is_file() or path.stat().st_size != record["bytes"] or file_sha256(path) != record["sha256"]:
            raise ValueError(f"OpenF1 artifact hash mismatch: {name}")
    expected_files = {"snapshot.json"} | {f"tables/{endpoint}.jsonl" for endpoint in ENDPOINTS}
    expected_files |= {f"raw/{i:04d}{suffix}" for i in range(len(manifest["requests"]))
                       for suffix in (".json", ".request.json")}
    actual_files = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} - {"manifest.json"}
    if actual_files != set(manifest["files"]) or set(manifest["files"]) != expected_files:
        raise ValueError("OpenF1 archive file inventory mismatch")
    source = dict(manifest["source_manifest"])
    source_digest = source.pop("content_sha256", None)
    if source_digest != payload_sha256(source) or source["source"] != "openf1" or source["query"] != manifest["query"]:
        raise ValueError("OpenF1 source manifest mismatch")
    expected_requests = []
    for record in manifest["requests"]:
        expected_requests.append({"endpoint": f"{BASE_URL}/{record['endpoint']}", "query": record["query"],
                                  "retrieved_at_utc": record["retrieved_at_utc"], "records": record["rows"],
                                  "payload_sha256": record["payload_sha256"]})
        metadata = json.loads(_path(root, record["raw_path"]).with_suffix(".request.json").read_text(encoding="utf-8"))
        if metadata != {key: record[key] for key in ("endpoint", "query", "status_code", "retrieved_at_utc", "headers", "attempts")}:
            raise ValueError("OpenF1 HTTP metadata mismatch")
    if source["requests"] != expected_requests:
        raise ValueError("OpenF1 source request lineage mismatch")
    snapshot = _build_tables(root, manifest["requests"], session_key)
    recorded = json.loads((root / "snapshot.json").read_text(encoding="utf-8"))
    if snapshot != recorded or snapshot["identity"] != manifest["identity"]:
        raise ValueError("OpenF1 reconstructed snapshot mismatch")
    for endpoint, record in snapshot["tables"].items():
        if file_sha256(root / "tables" / f"{endpoint}.jsonl") != record["sha256"]:
            raise ValueError(f"OpenF1 raw-to-table mismatch: {endpoint}")
    manifest["content_sha256"] = digest
    return manifest


def replay_openf1_archive(archive: str | Path, output: str | Path, *, timeout_s: int = 300) -> dict:
    """Rebuild in a fresh process with a Python socket audit guard and compare all tables."""
    root, destination = Path(archive).resolve(), Path(output).resolve()
    if destination.exists():
        raise FileExistsError(f"OpenF1 replay output already exists: {destination}")
    if destination.is_relative_to(root):
        raise ValueError("OpenF1 replay output must be outside the frozen archive")
    manifest = verify_openf1_archive(root)
    destination.mkdir(parents=True, exist_ok=False)
    with (destination / "worker.log").open("x", encoding="utf-8") as log:
        try:
            result = subprocess.run([sys.executable, "-m", "apexsim.data.openf1_worker", str(root), str(destination)],
                                    stdout=log, stderr=subprocess.STDOUT, timeout=timeout_s, check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("OpenF1 replay timed out; inspect worker.log") from exc
    if result.returncode != 0:
        raise RuntimeError("OpenF1 offline replay failed; inspect worker.log")
    rebuilt = json.loads((destination / "snapshot.json").read_text(encoding="utf-8"))
    expected = json.loads((root / "snapshot.json").read_text(encoding="utf-8"))
    worker = json.loads((destination / "worker_result.json").read_text(encoding="utf-8"))
    mismatches = sorted(name for name in ENDPOINTS if rebuilt["tables"].get(name) != expected["tables"][name]
                        or file_sha256(destination / "tables" / f"{name}.jsonl") != expected["tables"][name]["sha256"])
    passed = rebuilt == expected and not mismatches and worker["network_attempts"] == 0
    verify_openf1_archive(root)
    report = _seal(destination / "replay_report.json", {
        "schema_version": REPLAY_VERSION, "archive_sha256": manifest["content_sha256"], "passed": passed,
        "identity": rebuilt["identity"], "endpoint_count": len(ENDPOINTS), "request_count": len(manifest["requests"]),
        "network_attempts": worker["network_attempts"], "mismatched_tables": mismatches,
        "rows": {name: record["rows"] for name, record in rebuilt["tables"].items()},
        "empty_endpoints": rebuilt["empty_endpoints"], "archive_unchanged": True})
    if not passed:
        raise ValueError("OpenF1 offline reconstruction differs; inspect replay_report.json")
    return report
