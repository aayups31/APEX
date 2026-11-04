"""R041 freeze and independently confirm the expanded multi-season model."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import requests
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.compound_conditioned import fit_conditioned, predict_conditioned
from apexsim.research.compound_crossover_head import fit_event, predict_event
from apexsim.research.evidence import check_seal, read_json, seal
from confirm_compound_crossover import ENDPOINTS
from confirm_compound_event import score_heads
from confirm_compound_event import hashes as event_hashes
from confirm_compound_reference import build_cases, tables_from_archive

HELDOUT = {9888: (19, 1271), 9877: (20, 1272)}
BASE = Path(__file__).resolve().parents[2]
TRAINING = BASE/"docs/verification/compound-multiseason-training.json"
SELECTION = BASE/"docs/verification/compound-multiseason-development.json"
PROTOCOL = BASE/"research/protocols/COMPOUND_MULTISEASON_V7.md"


def canonical_file_sha(path: Path) -> str:
    """Bind text content across Git's LF/CRLF checkouts; native files stay byte-exact."""
    return sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def hashes() -> dict:
    paths = []
    for name in event_hashes():
        candidates = [BASE/folder/name for folder in (
            "research/scripts", "research/protocols", "apex_engine/src/apexsim/research", "docs/architecture")]
        matches = [p for p in candidates if p.is_file()]
        if len(matches) != 1:
            raise ValueError("Ambiguous frozen source dependency")
        paths.extend(matches)
    paths.extend((Path(__file__), PROTOCOL, TRAINING, SELECTION,
        Path(__file__).with_name("compound_multiseason.py"),
        Path(__file__).with_name("diagnose_compound_multiseason.py")))
    return {p.name: canonical_file_sha(p) for p in paths}


def calibrate() -> dict:
    data, selection = read_json(TRAINING), read_json(SELECTION)
    for document in (data, selection):
        check_seal(document)
    if selection["dataset_sha256"] != data["content_sha256"]:
        raise ValueError("Multi-season selection is not bound to training data")
    chosen = min(selection["comparisons"], key=lambda r: (-r["selection_score"], r["c"], abs(r["threshold"]-.5)))
    if chosen["c"] != 10. or abs(chosen["threshold"]-.54) > 1e-12 or chosen["selection_score"] < .5:
        raise ValueError("Multi-season development does not reproduce frozen selection")
    event = fit_event(data["cases"], chosen["c"])
    event["threshold"] = chosen["threshold"]
    prior = read_json(BASE/"docs/verification/compound-v2-calibration.json")
    check_seal(prior)
    return seal({"schema_version": "apex-compound-multiseason-v7-calibration", "hashes": hashes(),
                 "source_hash_normalization": "UTF8_TEXT_LF_NEWLINES_ONLY; NATIVE_ARCHIVES_BYTE_EXACT",
                 "training_sha256": data["content_sha256"], "selection_sha256": selection["content_sha256"],
                 "heldout_events": list(HELDOUT), "pace_head": fit_conditioned(data["cases"]), "event_head": event,
                 "source_count": len(data["sources"]), "training_cases": len(data["cases"]),
                 "prior_slopes": prior["slopes"], "prior_sha256": prior["content_sha256"]})


def verify_frozen(frozen: dict) -> None:
    check_seal(frozen)
    if frozen["hashes"] != hashes() or frozen["heldout_events"] != list(HELDOUT):
        raise ValueError("Frozen multi-season implementation or split mismatch")


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
                raise ValueError("Invalid multi-season confirmation response")
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
    return seal({"schema_version": "apex-compound-multiseason-v7-results", "calibration_sha256": frozen["content_sha256"],
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
