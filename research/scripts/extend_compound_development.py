"""Append opened v7 races to development, keeping the earlier corpus immutable."""
from __future__ import annotations

import argparse
from pathlib import Path

import diagnose_compound_multiseason as diagnostic
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from confirm_compound_multiseason import HELDOUT, TRAINING, canonical_file_sha
from confirm_compound_reference import build_cases, tables_from_archive


def additions(root: Path) -> dict:
    base = read_json(TRAINING)
    check_seal(base)
    rows, sources = [], {}
    for session, identity in HELDOUT.items():
        tables, digest = tables_from_archive(root, session, identity)
        cases, _ = build_cases(tables, session)
        rows.extend(cases)
        sources[str(session)] = {"archive_sha256": digest, "blocks": len(cases), "provider": "OPENF1"}
    return seal({"schema_version": "apex-compound-opened-training-additions-v8",
                 "base_training_sha256": base["content_sha256"], "sources": sources, "cases": rows,
                 "source_sha256_lf": canonical_file_sha(Path(__file__))})


def combine(addition: dict) -> dict:
    base = read_json(TRAINING)
    for item in (base, addition):
        check_seal(item)
    if addition["base_training_sha256"] != base["content_sha256"] or set(base["sources"]) & set(addition["sources"]):
        raise ValueError("Training extension overlaps or is bound to another base")
    return seal({"scope": "OPENED_TWENTY_SUPPORTED_EVENT_DEVELOPMENT_ONLY",
                 "base_training_sha256": base["content_sha256"], "addition_sha256": addition["content_sha256"],
                 "sources": {**base["sources"], **addition["sources"]}, "cases": base["cases"]+addition["cases"]})


def compare(addition: dict) -> dict:
    data = combine(addition)
    results = diagnostic.compare(data)
    payload = {k: v for k, v in results.items() if k != "content_sha256"}
    payload.update(scope="TWENTY_SUPPORTED_EVENT_DEVELOPMENT_NOT_CONFIRMATION",
                   source_sha256_lf=canonical_file_sha(Path(__file__)))
    return seal(payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "compare"))
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--additions", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, additions(args.archive) if args.stage == "prepare" else compare(read_json(args.additions)))
