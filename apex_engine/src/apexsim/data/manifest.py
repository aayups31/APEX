from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class SourceFile:
    path: str
    sha256: str
    rows: int | None = None
    bytes: int | None = None


@dataclass
class SourceManifest:
    source: str
    query: dict[str, Any]
    terms_url: str
    adapter_version: str = "0.2.0"
    schema_version: str = "apex-canonical-v1"
    accessed_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    files: list[SourceFile] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add_file(self, path: str | Path, rows: int | None = None) -> None:
        p = Path(path)
        self.files.append(SourceFile(str(p), file_sha256(p), rows, p.stat().st_size))

    def save(self, path: str | Path) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
