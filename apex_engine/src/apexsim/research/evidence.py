"""Small shared immutable JSON/inventory helpers for new research studies.

Exact content integrity and tolerant numerical regeneration are separate checks.
Existing accepted studies retain their original implementations and artifacts.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from apexsim.provenance import file_sha256, payload_sha256, write_manifest


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def seal(payload: dict) -> dict:
    return dict(payload, content_sha256=payload_sha256(payload))


def check_seal(payload: dict) -> None:
    if payload.get("content_sha256") != payload_sha256({k: v for k, v in payload.items() if k != "content_sha256"}):
        raise ValueError("Research evidence content seal mismatch")


def inventory(root: Path) -> dict:
    files = {}
    for p in sorted(root.rglob("*")):
        if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
            raise ValueError("Unsafe research artifact path")
        if p.is_file() and p != root/"manifest.json":
            files[p.relative_to(root).as_posix()] = {"sha256": file_sha256(p), "bytes": p.stat().st_size}
    return files


def finish_run(root: Path, version: str, summary: dict) -> dict:
    """Seal a completed run, writing its manifest last and refusing existing files."""
    summary = seal(summary)
    write_manifest(root/"summary.json", summary)
    write_manifest(root/"manifest.json", seal({"schema_version": version+"-manifest",
                                              "summary_sha256": summary["content_sha256"], "files": inventory(root)}))
    return summary


def verify_inventory(root: Path, version: str) -> dict:
    manifest = read_json(root/"manifest.json")
    check_seal(manifest)
    if manifest.get("schema_version") != version+"-manifest":
        raise ValueError("Research evidence manifest version mismatch")
    for name in manifest["files"]:
        p = root/name
        if ("\\" in name or ":" in name or Path(name).is_absolute() or ".." in Path(name).parts
                or p.is_symlink() or not p.resolve().is_relative_to(root.resolve())):
            raise ValueError("Unsafe research artifact path")
    if inventory(root) != manifest["files"]:
        raise ValueError("Research evidence inventory/hash mismatch")
    return manifest


def compare_numeric(actual, expected, path="results", *, atol=1e-8, rtol=1e-7) -> None:
    """Compare scientific values without replacing exact stored-file/hash checks."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError("Scientific replay keys mismatch: "+path)
        for key in expected:
            compare_numeric(actual[key], expected[key], path+"/"+key, atol=atol, rtol=rtol)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError("Scientific replay list mismatch: "+path)
        for i, (a, b) in enumerate(zip(actual, expected, strict=True)):
            compare_numeric(a, b, path+"/"+str(i), atol=atol, rtol=rtol)
    elif isinstance(expected, float):
        if (isinstance(actual, bool) or not isinstance(actual, (float, int))
                or not np.isfinite([actual, expected]).all() or not np.isclose(actual, expected, atol=atol, rtol=rtol)):
            raise ValueError("Scientific replay numeric mismatch: "+path)
    elif type(actual) is not type(expected) or actual != expected:
        raise ValueError("Scientific replay value mismatch: "+path)
