"""R041 frozen pace and direct crossover-event confirmation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests
import sklearn
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research import compound_crossover_head
from apexsim.research.compound_conditioned import fit_conditioned, predict_conditioned
from apexsim.research.compound_crossover_head import crossover, fit_event, predict_event
from apexsim.research.evidence import check_seal, read_json, seal
from confirm_compound_conditioned import HELDOUT as V5
from confirm_compound_conditioned import TRAIN
from confirm_compound_conditioned import hashes as conditioned_hashes
from confirm_compound_crossover import ENDPOINTS
from confirm_compound_reference import build_cases, score, tables_from_archive

DEVELOPMENT = {**TRAIN, **V5}
HELDOUT = {9920: (15, 1267), 9896: (18, 1270)}
PROTOCOL = Path(__file__).resolve().parents[1]/"protocols/COMPOUND_EVENT_V6.md"
ADR = Path(__file__).resolve().parents[2]/"docs/architecture/adr-0010-crossover-event-head.md"


def hashes() -> dict:
    return {**conditioned_hashes(), **{p.name: file_sha256(p) for p in
            (Path(__file__), PROTOCOL, ADR, Path(compound_crossover_head.__file__))}}


def event_counts(rows: list[dict], decisions: list[bool], *, pairwise: bool = False) -> dict:
    prefix, target = (("pairwise_prefix_s", "pairwise_actual_s") if pairwise else ("prefix_s", "actual_s"))
    observed = sum(crossover(r[prefix], r[target]) for r in rows)
    predicted = sum(decisions)
    matched = sum(d and crossover(r[prefix], r[target]) for r, d in zip(rows, decisions, strict=True))
    return {"observed": observed, "predicted": predicted, "matched": matched,
            "min_precision_recall": matched/max(observed, predicted, 1)}


def calibrate() -> dict:
    rows, sources = [], {}
    for session, identity in DEVELOPMENT.items():
        folder = ("r041-openf1-confirmation" if session in (9912, 9839) else
                  "r041-traffic-holdout" if session in (10014, 9971) else
                  "r041-reference-holdout" if session in (9963, 9955) else "r041-conditioned-holdout")
        tables, digest = tables_from_archive(Path(".cache")/folder, session, identity)
        cases, _ = build_cases(tables, session)
        rows.extend(cases)
        sources[str(session)] = digest
    grid = []
    for c in (.1, 1., 10.):
        validation, scores = [], []
        for session in DEVELOPMENT:
            training = [r for r in rows if r["session"] != session]
            testing = [r for r in rows if r["session"] == session]
            head = fit_event(training, c)
            validation.extend(testing)
            scores.extend(predict_event(head, r)["crossover_score"] for r in testing)
        for threshold in (.3, .4, .5, .6, .7):
            decisions = [s >= threshold for s in scores]
            counts = [event_counts(validation, decisions, pairwise=p) for p in (False, True)]
            folds = [{"session": s, "counts": [event_counts([r for r in validation if r["session"] == s],
                      [d for r, d in zip(validation, decisions, strict=True) if r["session"] == s], pairwise=p)
                      for p in (False, True)]} for s in DEVELOPMENT]
            grid.append({"c": c, "threshold": threshold, "counts": counts, "folds": folds,
                         "selection_score": min(r["min_precision_recall"] for r in counts)})
    selected = min(grid, key=lambda r: (-r["selection_score"], r["c"], abs(r["threshold"]-.5)))
    if (selected["c"], selected["threshold"]) != (.1, .5):
        raise ValueError("Event development selection does not reproduce protocol")
    prior = read_json(Path("docs/verification/compound-v2-calibration.json"))
    check_seal(prior)
    return seal({"schema_version": "apex-compound-event-v6-calibration", "hashes": hashes(),
                 "development_sources": sources, "development_events": list(DEVELOPMENT), "heldout_events": list(HELDOUT),
                 "pace_head": fit_conditioned(rows), "event_head": fit_event(rows), "development_grid": grid,
                 "prior_slopes": prior["slopes"], "prior_sha256": prior["content_sha256"],
                 "numpy": np.__version__, "sklearn": sklearn.__version__})


def verify_frozen(frozen: dict) -> None:
    check_seal(frozen)
    if frozen["hashes"] != hashes() or frozen["heldout_events"] != list(HELDOUT):
        raise ValueError("Frozen event implementation or split mismatch")


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
                raise ValueError("Invalid event holdout response")
            write_manifest(root/f"{session}-{endpoint}.json", rows)
            queries.append({"url": url, "params": params, "retrieved_utc": datetime.now(timezone.utc).isoformat()})
    write_manifest(root/"manifest.json", seal({"files": {p.name: file_sha256(p) for p in root.glob("*.json")},
                                              "queries": queries, "source_and_terms": "https://openf1.org/"}))


def score_heads(rows: list[dict], *, pairwise: bool = False) -> dict:
    metrics = score(rows, pairwise=pairwise)
    counts = event_counts(rows, [r["predicted_crossover"] for r in rows], pairwise=pairwise)
    prefix = "pairwise_prefix_s" if pairwise else "prefix_s"
    return {**metrics, "point_predicted": metrics["predicted"], "point_matched": metrics["matched"], **counts,
            "event_point_disagreements": sum(r["predicted_crossover"] != crossover(r[prefix], r["predicted_s"]) for r in rows),
            "passed": bool(rows) and counts["observed"] > 0 and counts["predicted"] > 0
            and counts["min_precision_recall"] >= .5
            and metrics["mae_s"] <= min(metrics["contrast_persistence_mae_s"], metrics["reference_persistence_mae_s"])}


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
    return seal({"schema_version": "apex-compound-event-v6-results", "calibration_sha256": frozen["content_sha256"],
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
