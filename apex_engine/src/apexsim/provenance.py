from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib import metadata
from pathlib import Path
from typing import Any

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
TRACKED_PACKAGES = (
    "apexsim",
    "numpy",
    "pandas",
    "scikit-learn",
    "torch",
    "pydantic",
    "fastapi",
    "uvicorn",
)


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_payload(value: Any) -> Any:
    """Convert supported config objects into deterministic JSON-compatible data."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value):
        return normalize_payload(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): normalize_payload(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [normalize_payload(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def payload_sha256(value: Any) -> str:
    encoded = json.dumps(
        normalize_payload(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _git_details(repository_root: Path) -> dict[str, Any]:
    def run(*arguments: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", *arguments],
                cwd=repository_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            return None
        return result.stdout.strip()

    commit = run("rev-parse", "HEAD")
    branch = run("branch", "--show-current")
    status = run("status", "--porcelain")
    diff = run("diff", "--binary", "HEAD")
    untracked_output = run("ls-files", "--others", "--exclude-standard")
    untracked = []
    for relative_path in (untracked_output or "").splitlines():
        path = repository_root / relative_path
        if path.is_file():
            untracked.append({"path": relative_path, "sha256": file_sha256(path)})
    working_tree = {
        "diff_sha256": sha256((diff or "").encode("utf-8")).hexdigest(),
        "untracked": untracked,
    }
    return {
        "commit": commit,
        "branch": branch,
        "dirty": bool(status) if status is not None else None,
        "working_tree_sha256": payload_sha256(working_tree),
    }


def _package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for package in TRACKED_PACKAGES:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            continue
    return versions


def file_records(paths: Sequence[str | Path]) -> list[dict[str, Any]]:
    records = []
    for path_value in paths:
        path = Path(path_value)
        if not path.is_file():
            continue
        records.append(
            {
                "path": str(path),
                "sha256": file_sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    return records


def build_run_manifest(
    *,
    run_id: str,
    run_type: str,
    config: Any,
    seed: int,
    repository_root: str | Path,
    inputs: Sequence[str | Path] = (),
    artifacts: Sequence[str | Path] = (),
    truth_labels: Mapping[str, str] | None = None,
    notes: Sequence[str] = (),
) -> dict[str, Any]:
    normalized_config = normalize_payload(config)
    source = _git_details(Path(repository_root))
    environment = {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "packages": _package_versions(),
    }
    return {
        "schema_version": "apex-run-manifest-v1",
        "run_id": run_id,
        "run_type": run_type,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": int(seed),
        "source": source,
        "source_sha256": payload_sha256(source),
        "environment": environment,
        "environment_sha256": payload_sha256(environment),
        "config": normalized_config,
        "config_sha256": payload_sha256(normalized_config),
        "inputs": file_records(inputs),
        "artifacts": file_records(artifacts),
        "truth_labels": dict(sorted((truth_labels or {}).items())),
        "notes": list(notes),
    }


def ensure_run_directory(root: str | Path, run_id: str) -> Path:
    """Create an empty run directory and refuse ambiguous or reused run identifiers."""
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError(
            "run_id must start with an alphanumeric character and contain only "
            "letters, numbers, dots, dashes, or underscores"
        )
    run_dir = Path(root) / run_id
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(f"Run directory already contains artifacts: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_manifest(path: str | Path, manifest: Mapping[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(normalize_payload(manifest), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return output
