"""R041 appended multi-season freeze and independent Miami/Imola confirmation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import requests
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.compound_conditioned import fit_conditioned, predict_conditioned
from apexsim.research.compound_crossover_head import fit_event, predict_event
from apexsim.research.evidence import check_seal, read_json, seal
from confirm_compound_crossover import ENDPOINTS
from confirm_compound_event import score_heads
from confirm_compound_multiseason import BASE, canonical_file_sha
from confirm_compound_multiseason import hashes as base_hashes
from confirm_compound_reference import build_cases, tables_from_archive
from extend_compound_development import combine

HELDOUT = {10033: (6, 1259), 9987: (7, 1260)}
ADDITIONS = BASE/"docs/verification/compound-v8-training-additions.json"
SELECTION = BASE/"docs/verification/compound-v8-development.json"
PROTOCOL = BASE/"research/protocols/COMPOUND_EXTENDED_V8.md"


def hashes() -> dict:
    return {**base_hashes(), **{p.name: canonical_file_sha(p) for p in
            (Path(__file__), PROTOCOL, ADDITIONS, SELECTION, Path(__file__).with_name("extend_compound_development.py"))}}


def calibrate() -> dict:
    addition, selection = read_json(ADDITIONS), read_json(SELECTION)
    data = combine(addition)
    check_seal(selection)
    if selection["dataset_sha256"] != data["content_sha256"] or any(r["session"] in HELDOUT for r in data["cases"]):
        raise ValueError("Training extension mismatch or heldout overlap")
    chosen = min(selection["comparisons"], key=lambda r: (-r["selection_score"], r["c"], abs(r["threshold"]-.5)))
    if chosen["c"] != .1 or abs(chosen["threshold"]-.49) > 1e-12 or chosen["selection_score"] < .5:
        raise ValueError("Extended development does not reproduce frozen selection")
    head = fit_event(data["cases"], chosen["c"])
    head["threshold"] = chosen["threshold"]
    prior = read_json(BASE/"docs/verification/compound-v2-calibration.json")
    check_seal(prior)
    return seal({"schema_version": "apex-compound-extended-v8-calibration", "hashes": hashes(),
                 "training_sha256": data["content_sha256"], "selection_sha256": selection["content_sha256"],
                 "source_hash_normalization": "UTF8_TEXT_LF_NEWLINES_ONLY; NATIVE_ARCHIVES_BYTE_EXACT",
                 "heldout_events": list(HELDOUT), "pace_head": fit_conditioned(data["cases"]), "event_head": head,
                 "source_count": len(data["sources"]), "training_cases": len(data["cases"]),
                 "prior_slopes": prior["slopes"], "prior_sha256": prior["content_sha256"]})


def verify_frozen(frozen: dict) -> None:
    check_seal(frozen)
    if frozen["hashes"] != hashes() or frozen["heldout_events"] != list(HELDOUT):
        raise ValueError("Frozen extended implementation or split mismatch")


def acquire(root: Path, frozen: dict) -> None:
    verify_frozen(frozen)
    root.mkdir(parents=True)
    queries = []
    for session, (round_number, _) in HELDOUT.items():
        assert_development_event(2025, round_number)
        for endpoint in ENDPOINTS:
            url, params = f"https://api.openf1.org/v1/{endpoint}", {"session_key": session}
            response = requests.get(url, params=params, timeout=45)
            response.raise_for_status()
            rows = response.json()
            if not isinstance(rows, list) or not rows or any(r.get("session_key") != session for r in rows):
                raise ValueError("Invalid extended confirmation response")
            write_manifest(root/f"{session}-{endpoint}.json", rows)
            queries.append({"url": url, "params": params, "retrieved_utc": datetime.now(timezone.utc).isoformat()})
    write_manifest(root/"manifest.json", seal({"files": {p.name: file_sha256(p) for p in root.glob("*.json")},
                                              "queries": queries, "source_and_terms": "https://openf1.org/"}))


def evaluate(frozen: dict, root: Path) -> dict:
    verify_frozen(frozen)
    cases, metrics, sources = [], [], {}
    for session, identity in HELDOUT.items():
        tables, digest = tables_from_archive(root, session, identity)
        rows, support = build_cases(tables, session)
        sources[str(session)] = digest
        for row in rows:
            row.update(predict_conditioned(frozen["pace_head"], row))
            row.update(predict_event(frozen["event_head"], row))
            row["prior_prediction_s"] = row["reference_persistence_s"]-9*frozen["prior_slopes"][row["compounds"][1]]
        primary, sensitivity = score_heads(rows), score_heads(rows, pairwise=True)
        metrics.append({"session": session, **support, "primary": primary, "pairwise_sensitivity": sensitivity,
                        "by_current_compound": {c: score_heads([r for r in rows if r["compounds"][1] == c])
                                                for c in ("SOFT", "MEDIUM", "HARD")},
                        "passed": primary["passed"] and sensitivity["passed"]})
        cases.extend(rows)
    return seal({"schema_version": "apex-compound-extended-v8-results", "calibration_sha256": frozen["content_sha256"],
                 "sources": sources, "metrics": metrics, "cases": cases, "passed": all(m["passed"] for m in metrics)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("fit", "acquire", "evaluate"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen", type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if args.stage == "fit":
        write_manifest(args.output, calibrate())
    elif args.stage == "acquire":
        acquire(args.output, read_json(args.frozen))
    else:
        write_manifest(args.output, evaluate(read_json(args.frozen), args.archive))
