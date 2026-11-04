"""R041 weighted event-conditioned calibration and fresh confirmation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research import compound_conditioned
from apexsim.research.compound_conditioned import fit_conditioned, predict_conditioned
from apexsim.research.evidence import check_seal, read_json, seal
from confirm_compound_crossover import ENDPOINTS
from confirm_compound_reference import DEVELOPMENT, build_cases, score, tables_from_archive
from confirm_compound_reference import hashes as reference_hashes

TRAIN = {**DEVELOPMENT, 9963: (10, 1263), 9955: (11, 1264)}
HELDOUT = {9998: (2, 1255), 9928: (14, 1266)}
PROTOCOL = Path(__file__).resolve().parents[1]/"protocols/COMPOUND_CONDITIONED_V5.md"


def hashes() -> dict:
    """Bind the conditioned implementation and all inherited preprocessing."""
    return {**reference_hashes(), **{p.name: file_sha256(p) for p in (
        Path(__file__), PROTOCOL, Path(compound_conditioned.__file__))}}


def calibrate() -> dict:
    """Save the complete ridge LOEO selection and fit without fresh labels."""
    rows, sources = [], {}
    for session, identity in TRAIN.items():
        folder = ("r041-openf1-confirmation" if session in (9912, 9839) else
                  "r041-traffic-holdout" if session in (10014, 9971) else "r041-reference-holdout")
        tables, digest = tables_from_archive(Path(".cache")/folder, session, identity)
        cases, _ = build_cases(tables, session)
        rows.extend(cases)
        sources[str(session)] = digest
    grid = []
    for level in range(4):
        for alpha in (1., 10., 100.):
            folds = []
            for session in TRAIN:
                training = [r for r in rows if r["session"] != session]
                validation = [r for r in rows if r["session"] == session]
                fitted = fit_conditioned(training, alpha=alpha, level=level)
                errors = [abs(predict_conditioned(fitted, r)["predicted_s"]-r["actual_s"]) for r in validation]
                folds.append({"session": session, "blocks": len(errors), "mae_s": float(np.mean(errors))})
            grid.append({"alpha": alpha, "level": level, "folds": folds,
                         "macro_mae_s": float(np.mean([r["mae_s"] for r in folds]))})
    selected = min(grid, key=lambda r: (r["macro_mae_s"], r["level"], r["alpha"]))
    if (selected["alpha"], selected["level"]) != (10., 3):
        raise ValueError("Development selection did not reproduce the frozen protocol")
    prior = read_json(Path("docs/verification/compound-v2-calibration.json"))
    check_seal(prior)
    return seal({"schema_version": "apex-compound-conditioned-v5-calibration", "hashes": hashes(),
                 "development_sources": sources, "development_events": list(TRAIN), "heldout_events": list(HELDOUT),
                 "model": fit_conditioned(rows), "development_selection": grid,
                 "prior_slopes": prior["slopes"], "prior_sha256": prior["content_sha256"]})


def verify_frozen(frozen: dict) -> None:
    """Reject changed models, code or experiment splits before any fresh access."""
    check_seal(frozen)
    if frozen["hashes"] != hashes() or frozen["heldout_events"] != list(HELDOUT):
        raise ValueError("Frozen conditioned implementation or split mismatch")


def acquire(root: Path, frozen: dict) -> None:
    """Acquire only the two predeclared fresh events after verifying the freeze."""
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
                raise ValueError("Invalid conditioned holdout response")
            write_manifest(root/f"{session}-{endpoint}.json", rows)
            queries.append({"url": url, "params": params, "retrieved_utc": datetime.now(timezone.utc).isoformat()})
    write_manifest(root/"manifest.json", seal({"files": {p.name: file_sha256(p) for p in root.glob("*.json")},
                                              "queries": queries, "source_and_terms": "https://openf1.org/"}))


def evaluate(frozen: dict, root: Path) -> dict:
    """Evaluate both frozen label gates on exactly the same eligible windows."""
    verify_frozen(frozen)
    cases, metrics, sources = [], [], {}
    for session, identity in HELDOUT.items():
        tables, digest = tables_from_archive(root, session, identity)
        rows, support = build_cases(tables, session)
        sources[str(session)] = digest
        for row in rows:
            row.update(predict_conditioned(frozen["model"], row))
            row["prior_prediction_s"] = row["reference_persistence_s"]-9*frozen["prior_slopes"][row["compounds"][1]]
        primary, sensitivity = score(rows), score(rows, pairwise=True)
        metrics.append({"session": session, **support, "primary": primary, "pairwise_sensitivity": sensitivity,
                        "by_current_compound": {c: score([r for r in rows if r["compounds"][1] == c])
                                                for c in compound_conditioned.COMPOUNDS},
                        "passed": primary["passed"] and sensitivity["passed"]})
        cases.extend(rows)
    return seal({"schema_version": "apex-compound-conditioned-v5-results", "calibration_sha256": frozen["content_sha256"],
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
