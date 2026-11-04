"""Freeze, acquire and prospectively evaluate the bounded R041 v9 candidate."""
from __future__ import annotations

import argparse
import gzip
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.compound_bounded import causal_weather, predict_bounded
from apexsim.research.compound_conditioned import fit_conditioned, predict_conditioned
from apexsim.research.compound_crossover_head import predict_event
from apexsim.research.evidence import check_seal, read_json, seal
from compound_bounded_common import environment, source_hashes
from confirm_compound_crossover import ENDPOINTS, timestamp
from confirm_compound_multiseason import BASE, canonical_file_sha
from confirm_compound_reference import build_cases, tables_from_archive
from diagnose_compound_adaptation import field_stints
from diagnose_compound_bounded import event_metrics, pace_metrics
from prepare_compound_bounded import field_context

HELDOUT = {10006: (3, 1256), 10022: (5, 1258), 9947: (12, 1277), 9858: (22, 1274)}
DATA = BASE/"docs/verification/compound-v9-development-data.json"
DEVELOPMENT = BASE/"docs/verification/compound-v9-development.json.gz"
SUMMARY = BASE/"docs/verification/compound-v9-development-summary.json"


def hashes() -> dict:
    paths = [Path(__file__), Path(__file__).with_name("audit_compound_bounded_confirmation.py"),
             Path(__file__).with_name("audit_compound_context.py"), Path(__file__).with_name("audit_compound_bounded.py"),
             BASE/"research/protocols/COMPOUND_BOUNDED_CONFIRMATION_V9.md",
             BASE/"docs/architecture/adr-0011-compound-negative-controls.md", DATA, SUMMARY]
    return {**source_hashes(), **{p.name: canonical_file_sha(p) for p in paths},
            DEVELOPMENT.name: file_sha256(DEVELOPMENT)}


def calibrate() -> dict:
    data, summary = read_json(DATA), read_json(SUMMARY)
    development = json.loads(gzip.decompress(DEVELOPMENT.read_bytes()))
    for document in (data, summary, development):
        check_seal(document)
    if (not development["development_qualified"] or not summary["development_qualified"]
            or development["dataset_sha256"] != data["content_sha256"]
            or summary["results_sha256"] != development["content_sha256"]
            or summary["compressed_file_sha256"] != file_sha256(DEVELOPMENT)
            or data["implementation_sha256_lf"] != source_hashes()
            or any(str(e) in data["sources"] for e in HELDOUT)):
        raise ValueError("Bounded candidate lacks source-bound qualification or has heldout overlap")
    return seal({"schema_version": "apex-compound-bounded-confirmation-v9-calibration", "hashes": hashes(),
                 "development_sha256": development["content_sha256"], "dataset_sha256": data["content_sha256"],
                 "heldout_events": list(HELDOUT), "pace_head": development["pace_head"],
                 "event_head": development["event_head"], "unbounded_head": fit_conditioned(data["cases"]),
                 "required_informative_events": 2, "negative_control_policy": "ZERO_FALSE_ALARMS_AND_BOTH_PACE_BASELINES",
                 "environment": environment(), "production_promotion": False})


def verify_frozen(frozen: dict) -> None:
    check_seal(frozen)
    if frozen["hashes"] != hashes() or frozen["heldout_events"] != list(HELDOUT) or frozen["required_informative_events"] != 2:
        raise ValueError("Frozen bounded implementation, split or enrollment mismatch")


def acquire(root: Path, frozen: dict) -> None:
    """Acquire only the predeclared panel, preserving partial attempts on failure."""
    verify_frozen(frozen)
    root.mkdir(parents=True)
    queries = []
    try:
        for session, (round_number, _) in HELDOUT.items():
            assert_development_event(2025, round_number)
            for endpoint in ENDPOINTS:
                url, params = f"https://api.openf1.org/v1/{endpoint}", {"session_key": session}
                for attempt in range(3):
                    try:
                        response = requests.get(url, params=params, timeout=45)
                        response.raise_for_status()
                        rows = response.json()
                        break
                    except requests.RequestException:
                        if attempt == 2:
                            raise
                        time.sleep(2.*(attempt+1))
                if not isinstance(rows, list) or not rows or any(r.get("session_key") != session for r in rows):
                    raise ValueError("Invalid bounded confirmation source response")
                write_manifest(root/f"{session}-{endpoint}.json", rows)
                queries.append({"url": url, "params": params, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                                "attempts": attempt+1})
                time.sleep(2.1)  # Below the documented 30 historical requests/minute.
        write_manifest(root/"manifest.json", seal({"files": {p.name: file_sha256(p) for p in root.glob("*.json")},
            "queries": queries, "calibration_sha256": frozen["content_sha256"], "source_and_terms": "https://openf1.org/"}))
    except Exception as error:
        write_manifest(root/"failure.json", seal({"queries": queries, "error_type": type(error).__name__,
                       "calibration_sha256": frozen["content_sha256"], "complete": False}))
        raise


def metrics(rows: list[dict]) -> dict:
    """Retain both-label pace/event gates and explicit zero-event controls."""
    if not rows:
        return {"cases": 0, "pace": None, "events": None, "passed_labels": [False, False],
                "informative": False, "passed": False, "disposition": "INCONCLUSIVE_FOR_SUPPORT"}
    pace, counts = pace_metrics(rows, rows), event_metrics(rows, [r["predicted_crossover"] for r in rows])
    gates = [p["mae_s"] <= min(p["reference_mae_s"], p["contrast_mae_s"])
             and (c["predicted"] == 0 if c["observed"] == 0 else c["predicted"] > 0 and c["min_precision_recall"] >= .5)
             for p, c in zip(pace, counts, strict=True)]
    return {"cases": len(rows), "pace": pace, "events": counts, "passed_labels": gates,
            "informative": all(c["observed"] > 0 for c in counts), "passed": all(gates),
            "disposition": "PASS" if all(gates) else "FAIL", "fallback_cases": sum(r["fallback"] for r in rows),
            "bounded_cases": sum(r["correction_bounded"] for r in rows),
            "unbounded_ridge_mae_s": [sum(abs(r["unbounded_prediction_s"]-r[t]) for r in rows)/len(rows)
                                      for t in ("actual_s", "pairwise_actual_s")]}


def evaluate(frozen: dict, root: Path) -> dict:
    verify_frozen(frozen)
    cases, reports, sources = [], [], {}
    for session, identity in HELDOUT.items():
        tables, digest = tables_from_archive(root, session, identity)
        rows, support = build_cases(tables, session)
        field = field_stints(tables)
        weather = [{"at_s": timestamp(r["date"]), "track_temperature_c": r.get("track_temperature")} for r in tables["weather"]]
        for row in rows:
            row["context"] = {**causal_weather(weather, row["forecast_at_s"]), "field_windows": field_context(row, field)}
            row.update(predict_bounded(frozen["pace_head"], row))
            row.update(predict_event(frozen["event_head"], row))
            row["unbounded_prediction_s"] = predict_conditioned(frozen["unbounded_head"], row)["predicted_s"]
        reports.append({"session": session, **support, **metrics(rows),
                        "by_current_compound": {c: metrics([r for r in rows if r["compounds"][1] == c])
                                                for c in ("SOFT", "MEDIUM", "HARD")}})
        sources[str(session)] = digest
        cases.extend(rows)
    supported = [m for m in reports if m["cases"]]
    informative = [m["session"] for m in supported if m["informative"]]
    passed = len(informative) >= frozen["required_informative_events"] and all(m["passed"] for m in supported)
    return seal({"schema_version": "apex-compound-bounded-confirmation-v9-results", "hashes": frozen["hashes"],
                 "calibration_sha256": frozen["content_sha256"], "sources": sources, "metrics": reports, "cases": cases,
                 "informative_events": informative, "unsupported_events": [m["session"] for m in reports if not m["cases"]],
                 "failed_supported_events": [m["session"] for m in supported if not m["passed"]],
                 "required_informative_events": 2, "passed": passed, "production_promotion": False})


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
