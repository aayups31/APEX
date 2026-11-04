"""Fill v8's empty-event coverage gap without changing either forecast head."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import requests
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.compound_conditioned import predict_conditioned
from apexsim.research.compound_crossover_head import predict_event
from apexsim.research.evidence import check_seal, read_json, seal
from confirm_compound_crossover import ENDPOINTS
from confirm_compound_event import score_heads
from confirm_compound_multiseason import BASE, canonical_file_sha
from confirm_compound_reference import build_cases, tables_from_archive
from confirm_compound_v8 import HELDOUT, verify_frozen
from confirm_compound_v8 import hashes as model_hashes

ADDITIONAL = {9850: (23, 1275)}
PANEL = {**HELDOUT, **ADDITIONAL}
MODEL = BASE/"docs/verification/compound-v8-calibration.json"
ORIGINAL = BASE/"docs/verification/compound-v8-original-results.json"
PROTOCOL = BASE/"research/protocols/COMPOUND_V8_COVERAGE_EXTENSION.md"


def hashes() -> dict:
    return {**model_hashes(), **{p.name: canonical_file_sha(p) for p in (Path(__file__), PROTOCOL, ORIGINAL)}}


def check_original(original: dict) -> None:
    """Coverage enrollment cannot replace a supported but failed prediction gate."""
    check_seal(original)
    if len(original["metrics"]) != 2 or {m["session"] for m in original["metrics"]} != set(HELDOUT):
        raise ValueError("Unexpected original confirmation cohort")
    supported = [m for m in original["metrics"] if m["primary"]["blocks"] > 0]
    empty = [m for m in original["metrics"] if m["primary"]["blocks"] == 0]
    if len(supported) != 1 or len(empty) != 1 or not supported[0]["passed"]:
        raise ValueError("Coverage extension cannot replace a supported failed event")
    for metric in empty:
        for key in ("primary", "pairwise_sensitivity"):
            if any(metric[key][k] != 0 for k in ("blocks", "observed", "predicted", "matched")):
                raise ValueError("Empty confirmation contains outcome claims")


def freeze(model: dict, original: dict) -> dict:
    verify_frozen(model)
    check_original(original)
    if original["calibration_sha256"] != model["content_sha256"]:
        raise ValueError("Original confirmation is not bound to the unchanged model")
    return seal({"schema_version": "apex-compound-v8-coverage-freeze", "hashes": hashes(),
                 "calibration_sha256": model["content_sha256"], "original_results_sha256": original["content_sha256"],
                 "additional_events": list(ADDITIONAL), "required_supported_events": 2,
                 "parameter_updates_allowed": False})


def verify(extension: dict, model: dict, original: dict) -> None:
    check_seal(extension)
    if extension != freeze(model, original):
        raise ValueError("Coverage freeze, source, original result or unchanged model mismatch")


def acquire(root: Path, extension: dict, model: dict, original: dict) -> None:
    verify(extension, model, original)
    root.mkdir(parents=True)
    queries = []
    for session, (round_number, _) in ADDITIONAL.items():
        assert_development_event(2025, round_number)
        for endpoint in ENDPOINTS:
            url, params = f"https://api.openf1.org/v1/{endpoint}", {"session_key": session}
            response = requests.get(url, params=params, timeout=45)
            response.raise_for_status()
            rows = response.json()
            if not isinstance(rows, list) or not rows or any(r.get("session_key") != session for r in rows):
                raise ValueError("Invalid coverage-extension response")
            write_manifest(root/f"{session}-{endpoint}.json", rows)
            queries.append({"url": url, "params": params, "retrieved_utc": datetime.now(timezone.utc).isoformat()})
    write_manifest(root/"manifest.json", seal({"files": {p.name: file_sha256(p) for p in root.glob("*.json")},
                                              "queries": queries, "source_and_terms": "https://openf1.org/"}))


def assemble(output: Path, base: Path, extra: Path) -> None:
    """Copy verified parent bytes exclusively; never modify either source archive."""
    output.mkdir(parents=True)
    parents = {}
    for label, root, events in (("original", base, HELDOUT), ("coverage", extra, ADDITIONAL)):
        manifest = read_json(root/"manifest.json")
        check_seal(manifest)
        expected = {f"{s}-{e}.json" for s in events for e in ENDPOINTS}
        if set(manifest["files"]) != expected:
            raise ValueError("Coverage parent archive inventory mismatch")
        for name in sorted(expected):
            if file_sha256(root/name) != manifest["files"][name]:
                raise ValueError("Coverage parent archive hash mismatch")
            (output/name).open("xb").write((root/name).read_bytes())
        parents[label] = manifest
    write_manifest(output/"manifest.json", seal({"files": {p.name: file_sha256(p) for p in output.glob("*.json")},
                                                "parent_manifests": parents}))


def panel_passed(metrics: list[dict]) -> bool:
    supported = [m for m in metrics if m["primary"]["blocks"] > 0]
    return len(supported) >= 2 and all(m["passed"] for m in supported)


def evaluate(extension: dict, model: dict, original: dict, root: Path) -> dict:
    verify(extension, model, original)
    cases, metrics, sources = [], [], {}
    for session, identity in PANEL.items():
        tables, digest = tables_from_archive(root, session, identity)
        rows, support = build_cases(tables, session)
        sources[str(session)] = digest
        for row in rows:
            row.update(predict_conditioned(model["pace_head"], row))
            row.update(predict_event(model["event_head"], row))
            row["prior_prediction_s"] = row["reference_persistence_s"]-9*model["prior_slopes"][row["compounds"][1]]
        primary, sensitivity = score_heads(rows), score_heads(rows, pairwise=True)
        metrics.append({"session": session, **support, "primary": primary, "pairwise_sensitivity": sensitivity,
                        "by_current_compound": {c: score_heads([r for r in rows if r["compounds"][1] == c])
                                                for c in ("SOFT", "MEDIUM", "HARD")},
                        "passed": primary["passed"] and sensitivity["passed"]})
        cases.extend(rows)
    if metrics[:2] != original["metrics"] or [r for r in cases if r["session"] in HELDOUT] != original["cases"]:
        raise ValueError("Original forecasts or cohorts changed during coverage extension")
    return seal({"schema_version": "apex-compound-v8-coverage-results", "calibration_sha256": model["content_sha256"],
                 "coverage_freeze_sha256": extension["content_sha256"], "original_results_sha256": original["content_sha256"],
                 "sources": sources, "metrics": metrics, "cases": cases, "required_supported_events": 2,
                 "unsupported_events": [m["session"] for m in metrics if m["primary"]["blocks"] == 0],
                 "passed": panel_passed(metrics)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("freeze", "acquire", "assemble", "evaluate"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--extra", type=Path)
    args = parser.parse_args()
    if args.stage == "assemble":
        assemble(args.output, args.archive, args.extra)
    else:
        model, original = read_json(MODEL), read_json(ORIGINAL)
        if args.stage == "freeze":
            write_manifest(args.output, freeze(model, original))
        else:
            extension = read_json(args.freeze)
            if args.stage == "acquire":
                acquire(args.output, extension, model, original)
            else:
                write_manifest(args.output, evaluate(extension, model, original, args.archive))
