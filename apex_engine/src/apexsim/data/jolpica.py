"""Paginated Jolpica event metadata, immutable raw pages and offline verification.

Catalog identifiers are reconstructed from explicit season/round values. They do
not assert a cross-provider session match or turn scheduled times into telemetry.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from datetime import date, time, timedelta
from pathlib import Path, PurePosixPath

import requests

from apexsim import __version__
from apexsim.data.manifest import SourceManifest, SourceRequest
from apexsim.data.openf1_http import DownloadPolicy, OpenF1Client
from apexsim.provenance import file_sha256, payload_sha256, write_manifest

BASE_URL = "https://api.jolpi.ca/ergast/f1"
ARCHIVE_VERSION = "apex-jolpica-events-v1"
CATALOG_VERSION = "apex-event-catalog-v1"
TERMS_URL = "https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md"


class JolpicaClient(OpenF1Client):
    """Reuse bounded HTTP transport with Jolpica's URL, name and sustained-rate pacing."""

    base_url = BASE_URL
    source_name = "Jolpica"

    def __init__(self, policy: DownloadPolicy | None = None) -> None:
        policy = policy or DownloadPolicy(spacing_s=7.3)
        if policy.spacing_s < 7.2:
            raise ValueError("Jolpica spacing_s must be >= 7.2 for the 500/hour sustained limit")
        super().__init__(policy)


def _integer(value: object, name: str, minimum: int = 0, maximum: int = 100000) -> int:
    if type(value) is int:
        result = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        result = int(value)
    else:
        raise ValueError(f"Jolpica {name} must be an integer")
    if not minimum <= result <= maximum:
        raise ValueError(f"Jolpica {name} outside [{minimum}, {maximum}]")
    return result


def _query(season: int, page_size: int) -> dict:
    if type(season) is not int or type(page_size) is not int:
        raise ValueError("Jolpica season and page_size require exact integers")
    return {"season": _integer(season, "season", 1950, 2100),
            "page_size": _integer(page_size, "page_size", 1, 100)}


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate Jolpica JSON key: {key}")
        result[key] = value
    return result


def _page(body: bytes, season: int, offset: int, expected_total: int | None) -> tuple[dict, list[dict], int]:
    """Check each page envelope, advancing by actual records rather than assumed limits."""
    payload = json.loads(body, object_pairs_hook=_unique_object)
    json.dumps(payload, allow_nan=False)
    try:
        envelope = payload["MRData"]
        table = envelope["RaceTable"]
        races = table["Races"]
        returned_offset = _integer(envelope["offset"], "offset")
        total = _integer(envelope["total"], "total", 0, 100)
        limit = _integer(envelope["limit"], "limit", 1, 100)
        returned_season = _integer(table["season"], "season", 1950, 2100)
    except (KeyError, TypeError) as exc:
        raise ValueError("Jolpica malformed MRData/RaceTable page") from exc
    if envelope.get("series") != "f1" or returned_season != season or returned_offset != offset:
        raise ValueError("Jolpica page has wrong series, season or offset")
    if expected_total is not None and total != expected_total:
        raise ValueError("Jolpica total changed during pagination; acquire a fresh snapshot")
    if not isinstance(races, list) or any(not isinstance(row, dict) for row in races):
        raise ValueError("Jolpica Races must be a list of objects")
    if len(races) > limit or offset + len(races) > total or (not races and offset < total):
        raise ValueError("Jolpica page count is inconsistent or pagination made no progress")
    return payload, races, total


def _catalog(races: list[dict], season: int) -> dict:
    events, seen = [], set()
    for row in races:
        try:
            if _integer(row["season"], "race season", 1950, 2100) != season:
                raise ValueError("Jolpica race season mismatch")
            round_number = _integer(row["round"], "round", 1, 100)
            circuit_id, race_name = row["Circuit"]["circuitId"], row["raceName"]
            race_date, race_time = row["date"], row.get("time")
            date.fromisoformat(race_date)
            if race_time is not None and time.fromisoformat(race_time.replace("Z", "+00:00")).utcoffset() != timedelta(0):
                raise ValueError("Jolpica race time must be explicit UTC when present")
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError("Jolpica event metadata is missing required identity/date fields") from exc
        if round_number in seen:
            raise ValueError("Jolpica duplicate season/round across pages")
        if not isinstance(circuit_id, str) or not circuit_id.strip() or not isinstance(race_name, str) or not race_name.strip():
            raise ValueError("Jolpica circuit and race identifiers must be nonempty strings")
        seen.add(round_number)
        events.append({"event_id": f"F1_{season}_R{round_number:02d}", "season": season, "round_number": round_number,
                       "circuit_id": circuit_id, "race_name": race_name, "race_date": race_date,
                       "race_time_utc": race_time, "source": "jolpica",
                       "truth_labels": {"event_id": "RECONSTRUCTED", "season": "MEASURED", "round_number": "MEASURED",
                                        "circuit_id": "MEASURED", "race_name": "MEASURED", "race_date": "MEASURED",
                                        "race_time_utc": "UNKNOWN" if race_time is None else "MEASURED"}})
    return {"schema_version": CATALOG_VERSION, "season": season,
            "events": sorted(events, key=lambda event: event["round_number"]),
            "rows": len(events), "complete_source_query": True,
            "notes": ["Provider-reported calendar metadata; not measured on-track session starts.",
                      "Stable event IDs are derived from season/round; provider session linkage remains separate."]}


def _path(root: Path, relative: str) -> Path:
    name = PurePosixPath(relative)
    if not relative or name.is_absolute() or ".." in name.parts or "\\" in relative or ":" in relative:
        raise ValueError("Invalid Jolpica artifact path")
    result = root / name
    if not result.resolve().is_relative_to(root.resolve()):
        raise ValueError("Jolpica artifact path escapes root")
    return result


def download_jolpica_events(season: int, output: str | Path, *, page_size: int = 100) -> dict:
    """Freeze one season's race calendar, fetching every page with an identifying user agent.

    Raw bodies preserve circuit/session scheduling details beyond the small derived
    event index. Empty seasons are valid zero-row source snapshots, not populated datasets.
    """
    query = _query(season, page_size)
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    (root / "raw").mkdir()
    client = JolpicaClient()
    source = SourceManifest("jolpica", query, TERMS_URL, license_id="CC-BY-NC-SA-4.0", canonical_schema_version=CATALOG_VERSION,
                            notes=["Provider-reported calendar; raw pages preserve all scheduling fields.",
                                   "Upstream source-data rights are not inferred from the API software licence."])
    records, races = [], []
    offset, total = 0, None
    endpoint = f"{season}/races/"
    try:
        while total is None or offset < total:
            params = {"limit": page_size, "offset": offset}
            body, metadata = client.get(endpoint, params)
            relative = f"raw/{len(records):04d}.json"
            with (root / relative).open("xb") as handle:
                handle.write(body)
            write_manifest((root / relative).with_suffix(".request.json"),
                           {"endpoint": f"{BASE_URL}/{endpoint}", "query": params, **metadata,
                            "user_agent": client.session.headers["User-Agent"]})
            if metadata["status_code"] != 200:
                raise ValueError(f"Jolpica HTTP {metadata['status_code']} is not a successful page")
            payload, page_races, total = _page(body, season, offset, total)
            races.extend(page_races)
            _catalog(races, season)  # Reject overlapping/incorrect pages before further requests.
            records.append({"path": relative, "query": params, "rows": len(page_races), "total": total,
                            "payload_sha256": payload_sha256(payload)})
            source.requests.append(SourceRequest(f"{BASE_URL}/{endpoint}", params, metadata["retrieved_at_utc"],
                                                  len(page_races), payload_sha256(payload)))
            offset += len(page_races)
    finally:
        client.close()
    catalog = _catalog(races, season)
    write_manifest(root / "events.json", catalog)
    manifest = {"schema_version": ARCHIVE_VERSION, "query": query, "pages": records, "event_count": len(races),
                "source_manifest": source.to_dict(), "download_policy": asdict(client.policy),
                "environment": {"python": sys.version.split()[0], "apexsim": __version__, "requests": requests.__version__},
                "files": {p.relative_to(root).as_posix(): {"sha256": file_sha256(p), "bytes": p.stat().st_size}
                          for p in sorted(root.rglob("*")) if p.is_file()}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(root / "manifest.json", manifest)
    return manifest


def verify_jolpica_archive(archive: str | Path) -> dict:
    """Rebuild the event index from verified local pages, checking pagination and source lineage."""
    root = Path(archive)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    digest = manifest.pop("content_sha256", None)
    if digest != payload_sha256(manifest):
        raise ValueError("Jolpica manifest content hash mismatch")
    if manifest.get("schema_version") != ARCHIVE_VERSION:
        raise ValueError("Unsupported Jolpica archive schema")
    query = _query(**manifest["query"])
    if not manifest["pages"]:
        raise ValueError("Jolpica archive requires at least one response page")
    expected_files = {"events.json"} | {f"raw/{i:04d}{suffix}" for i in range(len(manifest["pages"]))
                                       for suffix in (".json", ".request.json")}
    for relative, record in manifest["files"].items():
        path = _path(root, relative)
        if not path.is_file() or path.stat().st_size != record["bytes"] or file_sha256(path) != record["sha256"]:
            raise ValueError(f"Jolpica artifact hash mismatch: {relative}")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} - {"manifest.json"}
    if actual != expected_files or set(manifest["files"]) != expected_files:
        raise ValueError("Jolpica archive inventory mismatch")
    source = dict(manifest["source_manifest"])
    source_digest = source.pop("content_sha256", None)
    if source_digest != payload_sha256(source) or source["source"] != "jolpica" or source["query"] != query:
        raise ValueError("Jolpica source manifest mismatch")
    races, expected_requests = [], []
    offset, total = 0, None
    for i, record in enumerate(manifest["pages"]):
        if total is not None and offset >= total:
            raise ValueError("Jolpica archive contains extra pages after completion")
        params = {"limit": query["page_size"], "offset": offset}
        if record["path"] != f"raw/{i:04d}.json" or record["query"] != params:
            raise ValueError("Jolpica page path/query mismatch")
        raw = _path(root, record["path"])
        payload, page_races, total = _page(raw.read_bytes(), query["season"], offset, total)
        if (record["rows"], record["total"], record["payload_sha256"]) != (len(page_races), total, payload_sha256(payload)):
            raise ValueError("Jolpica page counts or payload hash mismatch")
        http = json.loads(raw.with_suffix(".request.json").read_text(encoding="utf-8"))
        endpoint = f"{BASE_URL}/{query['season']}/races/"
        if http["endpoint"] != endpoint or http["query"] != params or http["status_code"] != 200 or not http["user_agent"].startswith("APEX/"):
            raise ValueError("Jolpica HTTP request metadata mismatch")
        expected_requests.append({"endpoint": endpoint, "query": params, "retrieved_at_utc": http["retrieved_at_utc"],
                                  "records": len(page_races), "payload_sha256": payload_sha256(payload)})
        races.extend(page_races)
        offset += len(page_races)
    if offset != total or manifest["event_count"] != total or source["requests"] != expected_requests:
        raise ValueError("Jolpica pagination is incomplete or request lineage differs")
    rebuilt = _catalog(races, query["season"])
    if rebuilt != json.loads((root / "events.json").read_text(encoding="utf-8")):
        raise ValueError("Jolpica raw-to-catalog reconstruction mismatch")
    manifest["content_sha256"] = digest
    return manifest


def read_jolpica_events(archive: str | Path) -> list[dict]:
    """Return verified events ordered by calendar round, without network access."""
    verify_jolpica_archive(archive)
    return json.loads((Path(archive) / "events.json").read_text(encoding="utf-8"))["events"]
