"""Calibrate and test the R041 prefix-only traffic forecast."""
import argparse
import tempfile
from itertools import combinations, groupby
from pathlib import Path

import numpy as np
import requests
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_traffic import audit
from confirm_compound_crossover import ENDPOINTS, HORIZON, sign_change, stint_rows

EVENTS = {10014: (4, 1257), 9971: (9, 1262)}
PROTOCOL = Path(__file__).resolve().parents[1]/"protocols/COMPOUND_TRAFFIC_V3.md"


def hashes():
    root = Path(__file__).parent
    return {p.name: file_sha256(p) for p in (Path(__file__), PROTOCOL, root/"audit_compound_traffic.py",
                                           root/"confirm_compound_crossover.py")}


def share(window):
    if any(lap["samples"] < 5 for lap in window):
        return None
    return sum(lap["close_samples"] for lap in window)/sum(lap["samples"] for lap in window)


def fit(results, diagnostic, prior):
    for item in (results, diagnostic, prior):
        check_seal(item)
    if diagnostic["results_sha256"] != results["content_sha256"] or results["calibration_sha256"] != prior["content_sha256"]:
        raise ValueError("Development artifacts are not bound")
    x, y, relative, residual = [], [], [], []
    contexts = {case_key(row): row for row in diagnostic["cases"]}
    if len(contexts) != len(results["cases"]) or set(contexts) != {case_key(row) for row in results["cases"]}:
        raise ValueError("Development traffic rows do not align")
    for case in results["cases"]:
        context = contexts[case_key(case)]
        a, b = [[share(w) for w in s] for s in context["traffic_samples"]]
        if None in a+b:
            continue
        x.extend((a[0], b[0]))
        y.extend((a[1], b[1]))
        relative.append((a[1]-b[1])-(a[0]-b[0]))
        residual.append(case["actual_s"]-case["predicted_s"])
    x, y = np.asarray(x), np.asarray(y)
    centered = x-x.mean()
    if len(relative) < 10 or centered@centered <= 0:
        raise ValueError("Insufficient development traffic support")
    slope = float(np.clip(centered@(y-y.mean())/(centered@centered), 0, 1))
    dx = np.asarray(relative)
    penalty = max(0., float(dx@residual/(dx@dx+1)))
    return seal({"hashes": hashes(), "development_sha256": results["content_sha256"],
                     "traffic_sha256": diagnostic["content_sha256"], "slopes": prior["slopes"],
                     "traffic_slope": slope, "traffic_offset": float(y.mean()-slope*x.mean()),
                     "seconds_per_share": penalty, "calibration_blocks": len(relative)})


def case_key(row):
    return row["session"], row["driver"], tuple(row["stints"]), tuple(row["ages"])


def predict(frozen, prefix, compounds, traffic):
    left, right = traffic
    future = np.clip(frozen["traffic_offset"]+frozen["traffic_slope"]*np.asarray(traffic), 0, 1)
    a, b = compounds
    base = prefix+HORIZON*(frozen["slopes"][a]-frozen["slopes"][b])
    return float(base+frozen["seconds_per_share"]*(future[0]-future[1]-left+right)), future.tolist()


def acquire(root):
    root.mkdir(parents=True)
    intervals = root/"intervals"
    intervals.mkdir()
    for session, (round_number, _) in EVENTS.items():
        assert_development_event(2025, round_number)
        for endpoint in (*ENDPOINTS, "intervals"):
            response = requests.get(f"https://api.openf1.org/v1/{endpoint}", params={"session_key": session}, timeout=45)
            response.raise_for_status()
            rows = response.json()
            if not isinstance(rows, list) or not rows or any(r.get("session_key") != session for r in rows):
                raise ValueError("Invalid race response")
            path = intervals/f"{session}.json" if endpoint == "intervals" else root/f"{session}-{endpoint}.json"
            write_manifest(path, rows)
    write_manifest(root/"manifest.json", seal({"files": {p.name: file_sha256(p) for p in root.glob("*.json")},
                   "intervals": {p.name: file_sha256(p) for p in intervals.glob("*.json")}}))


def evaluate(frozen, root):
    check_seal(frozen)
    if frozen["hashes"] != hashes():
        raise ValueError("Frozen source mismatch")
    manifest = read_json(root/"manifest.json")
    check_seal(manifest)
    cases, unsupported_pairs = [], {}
    for session, (round_number, meeting) in EVENTS.items():
        assert_development_event(2025, round_number)
        tables = {}
        for endpoint in ENDPOINTS:
            name = f"{session}-{endpoint}.json"
            if file_sha256(root/name) != manifest["files"][name]:
                raise ValueError("Race table hash mismatch")
            tables[endpoint] = read_json(root/name)
        name = f"{session}.json"
        if file_sha256(root/"intervals"/name) != manifest["intervals"][name]:
            raise ValueError("Traffic table hash mismatch")
        identity, = tables["sessions"]
        if (identity["year"], identity["meeting_key"], identity["session_name"]) != (2025, meeting, "Race"):
            raise ValueError("Race identity mismatch")
        unsupported_pairs[session] = 0
        for driver, stints in sorted(stint_rows(tables).items()):
            for (i, a, x), (j, b, y) in combinations(stints, 2):
                if a == b:
                    continue
                count = 0
                width = HORIZON+3
                for _, group in groupby(enumerate(sorted(x.keys() & y.keys())), lambda row: row[1]-row[0]):
                    ages = [age for _, age in group]
                    for offset in range(0, len(ages)-width+1, width):
                        block = ages[offset:offset+width]
                        diffs = [x[age]-y[age] for age in block]
                        prefix, target = float(np.median(diffs[:3])), float(np.median(diffs[-3:]))
                        cases.append({"session": session, "driver": driver, "stints": [i, j], "compounds": [a, b], "ages": block,
                                          "prefix_s": prefix, "actual_s": target, "observed_crossover": sign_change(prefix, target)})
                        count += 1
                unsupported_pairs[session] += count == 0
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch)/"cases.json"
        write_manifest(path, seal({"archive_sha256": manifest["content_sha256"], "cases": cases}))
        context = audit(path, root, root/"intervals")
    for case, row in zip(cases, context["cases"], strict=True):
        prefix = [share(s[0]) for s in row["traffic_samples"]]
        future = [share(s[1]) for s in row["traffic_samples"]]
        case.update(traffic_prefix=prefix, traffic_actual=future, supported=None not in prefix)
        if case["supported"]:
            prediction, traffic = predict(frozen, case["prefix_s"], case["compounds"], prefix)
            case.update(predicted_s=prediction, traffic_prediction=traffic,
                        predicted_crossover=sign_change(case["prefix_s"], prediction))
    metrics = []
    for session in EVENTS:
        catalog = [c for c in cases if c["session"] == session]
        supported = [c for c in catalog if c["supported"]]
        observed = sum(c["observed_crossover"] for c in supported)
        predicted = sum(c["predicted_crossover"] for c in supported)
        matched = sum(c["predicted_crossover"] and c["observed_crossover"] for c in supported)
        mae = float(np.mean([abs(c["predicted_s"]-c["actual_s"]) for c in supported])) if supported else None
        baseline = float(np.mean([abs(c["prefix_s"]-c["actual_s"]) for c in supported])) if supported else None
        traffic_errors = [abs(a-b) for c in supported for a, b in zip(c["traffic_prediction"], c["traffic_actual"], strict=True)
                          if b is not None]
        metrics.append({"session": session, "blocks": len(supported), "excluded_prefix": len(catalog)-len(supported),
                            "unsupported_pairs": unsupported_pairs[session], "observed": observed, "predicted": predicted, "matched": matched,
                            "mae_s": mae, "persistence_mae_s": baseline,
                            "traffic_mae": float(np.mean(traffic_errors)) if traffic_errors else None,
                            "passed": observed > 0 and predicted > 0 and 2*matched >= max(observed, predicted) and mae <= baseline})
    return seal({"calibration_sha256": frozen["content_sha256"], "archive_sha256": manifest["content_sha256"],
                     "cases": cases, "metrics": metrics, "passed": all(row["passed"] for row in metrics)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("fit", "acquire", "evaluate"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen", type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    v = Path("docs/verification")
    if args.stage == "acquire":
        acquire(args.output)
    elif args.stage == "fit":
        write_manifest(args.output, fit(*(read_json(v/f"compound-v2-{name}.json") for name in
                                         ("results", "traffic-audit", "calibration"))))
    else:
        write_manifest(args.output, evaluate(read_json(args.frozen), args.archive))
