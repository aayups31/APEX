"""R019 immutable development collections over independently verified archives.

Paths locate evidence under an explicit caller-owned root. No provider data is
merged, imputed or made training-ready by registration. Benchmark roles are refused.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from apexsim import __version__
from apexsim.data.alignment_report import validate_link
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.data.jolpica import verify_jolpica_archive
from apexsim.data.observed import verify_observed_tables
from apexsim.data.openf1_archive import verify_openf1_archive
from apexsim.data.tables import COLUMNS, DATASET_VERSION, TABLE_VERSION, table_schema
from apexsim.provenance import file_sha256, payload_sha256, write_manifest

CORPUS_VERSION = "apex-development-event-corpus-v1"


@dataclass(frozen=True)
class CorpusSession:
    """Archive directories relative to evidence_root; rationale precedes modelling."""

    fastf1: str
    openf1: str
    jolpica: str
    observed: str
    rationale: str
    role: str = "DEVELOPMENT"


def _path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("Corpus requires relative POSIX paths")
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != relative or relative == ".":
        raise ValueError("Corpus path escapes or aliases its evidence root")
    target = root / relative
    if not target.resolve().is_relative_to(root.resolve()) or target.is_symlink():
        raise ValueError("Corpus path escapes its evidence root")
    if not target.is_dir():
        raise ValueError("Corpus requires existing archive directories")
    return target


def _schema_fingerprint() -> str:
    schemas = {}
    for name in COLUMNS:
        schema = table_schema(name)
        schemas[name] = {"fields": [{"name": f.name, "type": str(f.type), "nullable": f.nullable,
                                     "metadata": {k.decode(): v.decode() for k, v in (f.metadata or {}).items()}}
                                    for f in schema],
                         "metadata": {k.decode(): v.decode() for k, v in (schema.metadata or {}).items()}}
    return payload_sha256(schemas)


def _entry(root: Path, spec: CorpusSession) -> dict:
    if spec.role != "DEVELOPMENT" or not isinstance(spec.rationale, str) or not spec.rationale.strip():
        raise ValueError("Corpus requires DEVELOPMENT role and a membership rationale")
    paths = {name: _path(root, getattr(spec, name)) for name in ("fastf1", "openf1", "jolpica", "observed")}
    if len({p.resolve() for p in paths.values()}) != 4:
        raise ValueError("Corpus archive paths must be distinct")
    # Read identity metadata before native verifier payloads: never inspect a protected weekend here.
    fast_metadata = json.loads((paths["fastf1"] / "manifest.json").read_text(encoding="utf-8"))
    link = json.loads((paths["observed"] / "session_link.json").read_text(encoding="utf-8"))
    assert_development_event(fast_metadata["query"]["year"], fast_metadata["query"]["round_number"])
    assert_development_event(fast_metadata["identity"]["year"], fast_metadata["identity"]["round_number"])
    assert_development_event(link["season"], link["round_number"])
    archives = {"fastf1": verify_fastf1_archive(paths["fastf1"]),
                "openf1": verify_openf1_archive(paths["openf1"]),
                "jolpica": verify_jolpica_archive(paths["jolpica"])}
    observed = verify_observed_tables(paths["observed"])
    identity = validate_link(link, archives["fastf1"], archives["openf1"], archives["jolpica"], paths["jolpica"])
    if observed["identity"] != identity or observed["source_archives_sha256"] != {
            name: m["content_sha256"] for name, m in archives.items()}:
        raise ValueError("Observed corpus lineage does not match native archives")
    native = {}
    for name, manifest in archives.items():
        source = manifest["source_manifest"]
        if not manifest.get("environment") or not source.get("adapter_version") or not source.get("accessed_at_utc"):
            raise ValueError("Corpus source versions/retrieval time are missing")
        native[name] = {"archive_schema": manifest["schema_version"], "archive_sha256": manifest["content_sha256"],
                        "manifest_file_sha256": file_sha256(paths[name] / "manifest.json"),
                        "source_manifest_sha256": source["content_sha256"], "query": manifest["query"],
                        "environment": manifest["environment"], "adapter_version": source["adapter_version"],
                        "native_schema_version": source["canonical_schema_version"],
                        "accessed_at_utc": source["accessed_at_utc"], "terms_url": source["terms_url"],
                        "license_id": source.get("license_id"), "file_count": len(manifest["files"]),
                        "total_bytes": sum(r["bytes"] for r in manifest["files"].values())}
    bundles = {}
    for name in ("fastf1", "openf1"):
        manifest = json.loads((paths["observed"] / name / "manifest.json").read_text(encoding="utf-8"))
        bundles[name] = {"dataset_schema": manifest["schema_version"], "dataset_sha256": manifest["content_sha256"],
                         "table_rows": observed["providers"][name]["table_rows"],
                         "null_counts": observed["providers"][name]["null_counts"],
                         "issue_count": len(observed["providers"][name]["issues"])}
        if manifest["schema_version"] != DATASET_VERSION:
            raise ValueError("Unsupported canonical corpus dataset version")
    return {"spec": asdict(spec), "event_id": identity["event_id"], "season": link["season"],
            "round_number": link["round_number"], "session_code": link["session_code"],
            "circuit_id": link["jolpica_circuit_id"], "session_date": link["session_date"],
            "provider_session_keys": {"fastf1": archives["fastf1"]["identity"]["api_path"],
                                      "openf1": link["openf1_session_key"]},
            "session_link_sha256": file_sha256(paths["observed"] / "session_link.json"),
            "native": native, "canonical": bundles,
            "observed_report_sha256": observed["content_sha256"],
            "observed_manifest_sha256": file_sha256(paths["observed"] / "manifest.json"),
            "mapping_schema_version": observed["schema_version"], "mapping_environment": observed["environment"],
            "mapping_implementation_sha256": observed["implementation_sha256"]}


def _membership(entries: list[dict]) -> None:
    if len({e["event_id"] for e in entries}) < 2:
        raise ValueError("Corpus requires at least two distinct events")
    identities = [(e["season"], e["round_number"], e["session_code"]) for e in entries]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate event/session corpus membership")
    for provider in ("fastf1", "openf1"):
        keys = [e["provider_session_keys"][provider] for e in entries]
        hashes = [e["native"][provider]["archive_sha256"] for e in entries]
        if len(set(keys)) != len(keys) or len(set(hashes)) != len(hashes):
            raise ValueError("Duplicate provider session identity or archive alias")


def freeze_event_corpus(evidence_root: str | Path, sessions: Sequence[CorpusSession], output: str | Path,
                        *, purpose: str) -> dict:
    """Verify a multi-event DEVELOPMENT collection, then write one exclusive manifest."""
    destination, root = Path(output), Path(evidence_root).resolve()
    if destination.exists():
        raise FileExistsError(f"Corpus output already exists: {destination}")
    if not isinstance(purpose, str) or not purpose.strip() or not sessions:
        raise ValueError("Corpus purpose and membership are required")
    for spec in sessions:
        for name in ("fastf1", "openf1", "jolpica", "observed"):
            if destination.resolve().is_relative_to(_path(root, getattr(spec, name)).resolve()):
                raise ValueError("Corpus output must be outside referenced archives")
    entries = sorted((_entry(root, spec) for spec in sessions),
                     key=lambda e: (e["season"], e["round_number"], e["session_code"]))
    _membership(entries)
    # Reconstruct a second time to reject changed source evidence before publication.
    if entries != sorted((_entry(root, spec) for spec in sessions),
                         key=lambda e: (e["season"], e["round_number"], e["session_code"])):
        raise ValueError("Corpus source changed during registration")
    result = {"schema_version": CORPUS_VERSION, "purpose": purpose, "role": "DEVELOPMENT",
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "adapter_version": __version__,
              "implementation_sha256": file_sha256(Path(__file__)), "canonical_table_schema": TABLE_VERSION,
              "canonical_schema_sha256": _schema_fingerprint(), "training_ready": False,
              "benchmark_frozen": False, "session_count": len(entries),
              "event_count": len({e["event_id"] for e in entries}), "entries": entries,
              "limitations": ["Retrospective development evidence; no causal feature availability or model accuracy claim.",
                              "No benchmark membership or dense public training authorization.",
                              "Requires source evidence under an explicit root; hashes do not authenticate cache authors."]}
    result["content_sha256"] = payload_sha256(result)
    write_manifest(destination, result)
    return result


def verify_event_corpus(path: str | Path, evidence_root: str | Path) -> dict:
    """Revalidate every bound archive and canonical bundle offline under a relocated root."""
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest.get("content_sha256") != payload_sha256({k: v for k, v in manifest.items() if k != "content_sha256"}):
        raise ValueError("Corpus manifest content hash mismatch")
    if (manifest.get("schema_version") != CORPUS_VERSION or manifest.get("role") != "DEVELOPMENT"
            or manifest.get("training_ready") is not False or manifest.get("benchmark_frozen") is not False
            or manifest.get("canonical_table_schema") != TABLE_VERSION
            or manifest.get("canonical_schema_sha256") != _schema_fingerprint()):
        raise ValueError("Unsupported corpus schema or scope")
    entries = [_entry(Path(evidence_root).resolve(), CorpusSession(**e["spec"])) for e in manifest["entries"]]
    _membership(entries)
    if (entries != manifest["entries"] or len(entries) != manifest["session_count"]
            or len({e["event_id"] for e in entries}) != manifest["event_count"]):
        raise ValueError("Corpus membership or bound source evidence changed")
    return manifest
