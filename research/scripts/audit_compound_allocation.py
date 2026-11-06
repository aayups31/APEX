"""Independent scalar reload of R041 v13 features, checkpoints and event gates."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from statistics import mean, median

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_repair import LABELS, compare, crossing, event_report
from audit_compound_trajectory import features
from diagnose_compound_decision import ROOT


def audit(data: dict, result: dict, sources: list[dict]) -> dict:
    for document in (data, result):
        check_seal(document)
    if result["dataset_sha256"] != data["content_sha256"]:
        raise ValueError("Allocation data seal mismatch")
    for name, digest in result["hashes"].items():
        if (
            sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            != digest
        ):
            raise ValueError("Allocation implementation or nomination source changed")
    allocation = {
        event: (s["issued"], tuple(values))
        for s in sources
        for event, values in s["events"].items()
    }
    if set(allocation) != set(data["sources"]) or len(allocation) != sum(
        len(s["events"]) for s in sources
    ):
        raise ValueError("Conflicting or missing allocation")
    total = 0
    rows = data["cases"]
    compare(sorted(result["recipes"]), ["nominated", "relative"], "recipe inventory")
    compare(result["new_holdout_acquisition_allowed"], result["development_qualified"], "acquisition gate")
    for name, recipe in result["recipes"].items():
        compare([f["event"] for f in recipe["folds"]], sorted(allocation), "fold inventory")
        compare(sorted(recipe["models"]), sorted({str(r["session"]) for r in rows}), "model inventory")
        if sorted(p["index"] for p in recipe["predictions"]) != list(range(len(rows))):
            raise ValueError("Missing or duplicate predictions")
        groups = {}
        for item in recipe["predictions"]:
            r = rows[item["index"]]
            event = str(r["session"])
            if event != item["event"]:
                raise ValueError("Forecast fold mismatch")
            model = recipe["models"][event]
            timestamp = datetime.fromtimestamp(r["forecast_at_s"], tz=timezone.utc)
            published, codes = allocation[event]
            if published >= timestamp.date().isoformat():
                raise ValueError("Unavailable nomination")
            prefix = r["current_prefix_s"]
            ref = r["reference_target_s"]
            center = median(prefix)
            x = features(r, "full")
            x.extend(v - center for v in [*prefix, *ref])
            x.extend(int(c == r["compounds"][0]) for c in ("HARD", "MEDIUM", "SOFT"))
            season = [int(timestamp.year == y) for y in (2023, 2024, 2025)]
            x.extend(season)
            if name == "nominated":
                lookup = dict(zip(("HARD", "MEDIUM", "SOFT"), codes, strict=True))
                identity = [
                    int(i == lookup[c]) for c in r["compounds"] for i in range(1, 7)
                ]
                x.extend(identity)
                x.extend(v * s for s in season for v in identity)
            z = [
                (v - m) / s
                for v, m, s in zip(x, model["center"], model["scale"], strict=True)
            ]
            raw = [
                b + sum(t * w for t, w in zip(z, weights, strict=True)) + center - p
                for p, b, weights in zip(
                    prefix, model["intercept"], model["coefficients"], strict=True
                )
            ]
            laps = [
                p + max(-2.0, min(2.0, d)) for p, d in zip(prefix, raw, strict=True)
            ]
            compare(item["laps_s"], laps, "forecast laps")
            compare(
                item["bounded_laps"], sum(abs(v) > 2.0 for v in raw), "bounded laps"
            )
            vals = [
                median(ref) - median(laps),
                median(a - b for a, b in zip(ref, laps, strict=True)),
            ]
            compare(item["contrasts_s"], vals, "contrasts")
            for j, (start, target) in enumerate(LABELS):
                decision = crossing(r[start], vals[j])
                compare(item["crossings"][j], decision, "crossover")
                baselines = [
                    median(ref) - center,
                    median(a - b for a, b in zip(ref, prefix, strict=True)),
                ]
                groups.setdefault((event, j), []).append(
                    {
                        **r,
                        "predicted_s": vals[j],
                        "predicted_crossover": decision,
                        "reference_persistence_s": baselines[0],
                        "own_error": abs(baselines[j] - r[target]),
                    }
                )
            total += 1
        failed, informative = [], 0
        for fold in recipe["folds"]:
            compare(fold["cases"], data["sources"][fold["event"]]["blocks"], "race denominator")
            metrics = []
            for j in range(2):
                group = groups.get((fold["event"], j), [])
                if group:
                    m = event_report(group)["labels"][j]
                    m["label_reference_mae_s"] = mean(r["own_error"] for r in group)
                    if m["mae_s"] > m["label_reference_mae_s"] + 1e-12:
                        m["passed"] = False
                        m["failure_codes"].append("PACE_WORSE_THAN_LABEL_REFERENCE")
                    metrics.append(m)
            compare(fold["labels"], metrics, "race gates")
            if any(not m["passed"] for m in metrics):
                failed.append(fold["event"])
            informative += bool(metrics) and all(m["observed"] for m in metrics)
        compare(recipe["failed_events"], failed, "failed races")
        compare(recipe["qualified"], not failed and informative >= 2, "qualification")
    compare(
        result["development_qualified"],
        result["recipes"]["nominated"]["qualified"],
        "primary gate",
    )
    return seal(
        {
            "schema": "allocation-scalar-replay-v13",
            "result_sha256": result["content_sha256"],
            "forecasts_verified": total,
            "race_folds_per_recipe": len(allocation),
            "audit_passed": True,
            "scope": "SAVED_CHECKPOINT_INFERENCE_AND_GATES",
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    directory = ROOT / "docs/verification"
    sources = [
        s
        for filename in (
            "compound-nomination-inventory.json",
            "compound-v13-nomination-additions.json",
        )
        for s in read_json(directory / filename)["sources"]
    ]
    write_manifest(
        args.output,
        audit(
            read_json(directory / "compound-v11-development-data.json"),
            read_json(directory / "compound-v13-development.json"),
            sources,
        ),
    )
