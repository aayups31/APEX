"""Freeze and independently evaluate the R041 completed-reference forecast."""
from __future__ import annotations

import argparse
import platform
from datetime import datetime, timezone
from itertools import combinations, groupby
from pathlib import Path

import numpy as np
import requests
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research import compound_reference
from apexsim.research.compound_reference import fit_drift, predict_reference
from apexsim.research.evidence import check_seal, read_json, seal
from confirm_compound_crossover import ENDPOINTS, sign_change, stint_rows, timestamp
from confirm_compound_traffic import normalize_race_control

DEVELOPMENT = {9912: (16, 1268), 9839: (24, 1276), 10014: (4, 1257), 9971: (9, 1262)}
HELDOUT = {9963: (10, 1263), 9955: (11, 1264)}
PROTOCOL = Path(__file__).resolve().parents[1]/"protocols/COMPOUND_REFERENCE_V4.md"


def hashes() -> dict:
    """Bind the complete local source path and protocol used by this candidate."""
    return {p.name: file_sha256(p) for p in (
        Path(__file__), PROTOCOL, Path(compound_reference.__file__),
        Path(__file__).with_name("confirm_compound_crossover.py"),
        Path(__file__).with_name("confirm_compound_traffic.py"))}


def tables_from_archive(root: Path, session: int, identity: tuple[int, int]) -> tuple[dict, str]:
    """Validate immutable source files, event reservation and native race identity."""
    round_number, meeting = identity
    assert_development_event(2025, round_number)
    manifest = read_json(root/"manifest.json")
    check_seal(manifest)
    tables = {}
    for endpoint in ENDPOINTS:
        name = f"{session}-{endpoint}.json"
        if file_sha256(root/name) != manifest["files"][name]:
            raise ValueError("Reference source archive hash mismatch")
        rows = read_json(root/name)
        if not isinstance(rows, list) or not rows or any(r.get("session_key") != session for r in rows):
            raise ValueError("Invalid native session identity in source table")
        tables[endpoint] = rows
    native, = tables["sessions"]
    if (native["year"], native["meeting_key"], native["session_name"], native["session_key"]) != (
            2025, meeting, "Race", session):
        raise ValueError("Reference race identity mismatch")
    tables["race_control"] = normalize_race_control(tables["race_control"])
    return tables, manifest["content_sha256"]


def build_cases(tables: dict, session: int) -> tuple[list[dict], dict]:
    """Build the retained retrospective cohort, checking all reference timestamps."""
    native = {}
    for row in tables["laps"]:
        key = (row["driver_number"], row["lap_number"])
        if key in native:
            raise ValueError("Duplicate native driver/lap key")
        native[key] = row
    by_stint = {}
    for row in tables["stints"]:
        by_stint[(row["driver_number"], row["stint_number"])] = row

    def end_time(driver: int, stint: int, age: int) -> float:
        meta = by_stint[(driver, stint)]
        lap = age-meta["tyre_age_at_start"]+meta["lap_start"]-1
        row = native[(driver, lap)]
        return timestamp(row["date_start"])+row["lap_duration"]

    cases, unsupported, unavailable = [], 0, 0
    for driver, stints in sorted(stint_rows(tables).items()):
        for (i, a, x), (j, b, y) in combinations(sorted(stints), 2):
            if a == b:
                continue
            count = 0
            for _, group in groupby(enumerate(sorted(x.keys() & y.keys())), lambda row: row[1]-row[0]):
                ages = [age for _, age in group]
                for offset in range(0, len(ages)-11, 12):
                    block = ages[offset:offset+12]
                    first, last = block[:3], block[-3:]
                    forecast_at = max(end_time(driver, j, k) for k in first)
                    reference_end = max(end_time(driver, i, k) for k in first+last)
                    if reference_end > forecast_at:
                        unavailable += 1
                        continue
                    xp, yp, xt, yt = ([v[k] for k in window] for v, window in
                                      ((x, first), (y, first), (x, last), (y, last)))
                    cases.append({"session": session, "driver": driver, "stints": [i, j],
                                  "compounds": [a, b], "ages": block,
                                  "reference_target_s": xt, "current_prefix_s": yp, "current_target_s": yt,
                                  "forecast_at_s": forecast_at, "reference_end_s": reference_end,
                                  "prefix_s": float(np.median(xp)-np.median(yp)),
                                  "actual_s": float(np.median(xt)-np.median(yt)),
                                  "pairwise_prefix_s": float(np.median(np.asarray(xp)-yp)),
                                  "pairwise_actual_s": float(np.median(np.asarray(xt)-yt))})
                    count += 1
            unsupported += count == 0
    return cases, {"unsupported_pairs": unsupported, "unavailable_reference_blocks": unavailable}


def calibrate() -> dict:
    """Fit only the four previously opened event archives; bind their seals."""
    cases, sources = [], {}
    for session, identity in DEVELOPMENT.items():
        folder = ".cache/r041-openf1-confirmation" if session in (9912, 9839) else ".cache/r041-traffic-holdout"
        tables, digest = tables_from_archive(Path(folder), session, identity)
        rows, _ = build_cases(tables, session)
        cases.extend(rows)
        sources[str(session)] = digest
    prior_path = Path("docs/verification/compound-v2-calibration.json")
    prior = read_json(prior_path)
    check_seal(prior)
    return seal({"schema_version": "apex-compound-reference-v4-calibration", "hashes": hashes(),
                 "development_sources": sources, "development_events": list(DEVELOPMENT),
                 "heldout_events": list(HELDOUT), "drift": fit_drift(cases),
                 "prior_slopes": prior["slopes"], "prior_sha256": prior["content_sha256"],
                 "development_pairs": len(cases), "python": platform.python_version(), "numpy": np.__version__})


def acquire(root: Path) -> None:
    """Fetch fresh race outcomes exclusively, after freezing code and parameters."""
    root.mkdir(parents=True)
    queries = []
    for session, (round_number, _) in HELDOUT.items():
        assert_development_event(2025, round_number)
        for endpoint in ENDPOINTS:
            url = f"https://api.openf1.org/v1/{endpoint}"
            params = {"session_key": session}
            response = requests.get(url, params=params, timeout=45)
            response.raise_for_status()
            rows = response.json()
            if not isinstance(rows, list) or not rows or any(r.get("session_key") != session for r in rows):
                raise ValueError("Invalid heldout response")
            write_manifest(root/f"{session}-{endpoint}.json", rows)
            queries.append({"url": url, "params": params, "retrieved_utc": datetime.now(timezone.utc).isoformat()})
    write_manifest(root/"manifest.json", seal({"files": {p.name: file_sha256(p) for p in root.glob("*.json")},
                                              "queries": queries, "source_and_terms": "https://openf1.org/"}))


def score(cases: list[dict], *, pairwise: bool = False) -> dict:
    """Compare fixed predictions and matched baselines with both label definitions."""
    prefix = "pairwise_prefix_s" if pairwise else "prefix_s"
    actual = "pairwise_actual_s" if pairwise else "actual_s"
    observed = sum(sign_change(c[prefix], c[actual]) for c in cases)
    predicted = sum(sign_change(c[prefix], c["predicted_s"]) for c in cases)
    matched = sum(sign_change(c[prefix], c[actual]) and sign_change(c[prefix], c["predicted_s"]) for c in cases)
    errors = [c["predicted_s"]-c[actual] for c in cases]
    mae = float(np.mean(np.abs(errors))) if cases else None
    old = float(np.mean([abs(c[prefix]-c[actual]) for c in cases])) if cases else None
    reference = float(np.mean([abs(c["reference_persistence_s"]-c[actual]) for c in cases])) if cases else None
    return {"blocks": len(cases), "observed": observed, "predicted": predicted, "matched": matched,
            "mae_s": mae, "rmse_s": float(np.sqrt(np.mean(np.square(errors)))) if cases else None,
            "contrast_persistence_mae_s": old, "reference_persistence_mae_s": reference,
            "prior_mae_s": float(np.mean([abs(c["prior_prediction_s"]-c[actual]) for c in cases])) if cases else None,
            "coverage": float(np.mean([c["lower_s"] <= c[actual] <= c["upper_s"] for c in cases])) if cases else None,
            "mean_width_s": float(np.mean([c["upper_s"]-c["lower_s"] for c in cases])) if cases else None,
            "passed": bool(cases) and observed > 0 and predicted > 0 and 2*matched >= max(observed, predicted)
            and mae <= min(old, reference)}


def evaluate(frozen: dict, root: Path) -> dict:
    """Evaluate a source-bound frozen model with heldout labels kept outside predict."""
    check_seal(frozen)
    if frozen["hashes"] != hashes() or frozen["heldout_events"] != list(HELDOUT):
        raise ValueError("Frozen reference implementation or split mismatch")
    cases, metrics, sources = [], [], {}
    for session, identity in HELDOUT.items():
        tables, digest = tables_from_archive(root, session, identity)
        rows, support = build_cases(tables, session)
        sources[str(session)] = digest
        for row in rows:
            row.update(predict_reference(frozen["drift"], row["compounds"][1], row["reference_target_s"],
                                         row["current_prefix_s"], reference_end_s=row["reference_end_s"],
                                         forecast_at_s=row["forecast_at_s"]))
            row["prior_prediction_s"] = row["reference_persistence_s"]-9*frozen["prior_slopes"][row["compounds"][1]]
        primary, sensitivity = score(rows), score(rows, pairwise=True)
        metrics.append({"session": session, **support, "primary": primary, "pairwise_sensitivity": sensitivity,
                        "by_current_compound": {c: score([r for r in rows if r["compounds"][1] == c])
                                                for c in compound_reference.COMPOUNDS},
                        "passed": primary["passed"] and sensitivity["passed"]})
        cases.extend(rows)
    return seal({"schema_version": "apex-compound-reference-v4-results", "calibration_sha256": frozen["content_sha256"],
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
        acquire(args.output)
    else:
        write_manifest(args.output, evaluate(read_json(args.frozen), args.archive))
