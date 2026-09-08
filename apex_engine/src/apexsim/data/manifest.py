from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apexsim import __version__
from apexsim.provenance import file_sha256, payload_sha256

SOURCE_MANIFEST_SCHEMA = "apex-source-manifest-v1"


@dataclass(frozen=True)
class SourceFile:
    path: str
    sha256: str
    role: str
    rows: int | None = None
    bytes: int | None = None


@dataclass(frozen=True)
class SourceRequest:
    endpoint: str
    query: dict[str, Any]
    retrieved_at_utc: str
    records: int | None
    payload_sha256: str | None


@dataclass
class SourceManifest:
    """Tamper-evident record for one immutable public-data retrieval operation."""

    source: str
    query: dict[str, Any]
    terms_url: str
    license_id: str | None = None
    adapter_version: str = __version__
    canonical_schema_version: str = "apex-canonical-v1"
    schema_version: str = SOURCE_MANIFEST_SCHEMA
    accessed_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    requests: list[SourceRequest] = field(default_factory=list)
    files: list[SourceFile] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add_request(
        self,
        endpoint: str,
        query: dict[str, Any],
        payload: Any | None,
        records: int | None = None,
    ) -> None:
        """Record a source request and hash its decoded payload when available."""
        self.requests.append(
            SourceRequest(
                endpoint=endpoint,
                query=dict(sorted(query.items())),
                retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                records=records,
                payload_sha256=payload_sha256(payload) if payload is not None else None,
            )
        )

    def add_file(self, path: str | Path, rows: int | None = None, role: str = "raw") -> None:
        source_path = Path(path)
        if not source_path.is_file():
            raise FileNotFoundError(f"Cannot add missing source artifact: {source_path}")
        self.files.append(
            SourceFile(
                path=str(source_path),
                sha256=file_sha256(source_path),
                role=role,
                rows=rows,
                bytes=source_path.stat().st_size,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["content_sha256"] = payload_sha256(payload)
        return payload

    def save(self, path: str | Path) -> Path:
        """Write once; an existing manifest is evidence and is never overwritten."""
        if not self.source.strip():
            raise ValueError("Source manifest requires a source identifier")
        if not self.terms_url.startswith("https://"):
            raise ValueError("Source manifest terms_url must be an HTTPS URL")
        if not self.requests and not self.files:
            raise ValueError("Source manifest requires at least one request or file record")
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")
        return output


def load_source_manifest(path: str | Path, verify_files: bool = True) -> dict[str, Any]:
    """Load a source manifest and reject content or referenced-file tampering."""
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    recorded_hash = payload.pop("content_sha256", None)
    actual_hash = payload_sha256(payload)
    if recorded_hash != actual_hash:
        raise ValueError(f"Source manifest content hash mismatch: {manifest_path}")
    if payload.get("schema_version") != SOURCE_MANIFEST_SCHEMA:
        raise ValueError(f"Unsupported source manifest schema: {payload.get('schema_version')}")
    if verify_files:
        for record in payload.get("files", []):
            source_path = Path(record["path"])
            if not source_path.is_file():
                raise FileNotFoundError(f"Manifest source artifact is missing: {source_path}")
            if file_sha256(source_path) != record["sha256"]:
                raise ValueError(f"Manifest source artifact hash mismatch: {source_path}")
    payload["content_sha256"] = recorded_hash
    return payload
