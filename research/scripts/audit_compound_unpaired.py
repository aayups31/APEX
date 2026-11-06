"""Independently solve the v14 ridge equations and replay each reported forecast."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_repair import LABELS, compare, crossing, event_report
from diagnose_compound_decision import ROOT
from diagnose_compound_unpaired import unique_rows


def audit() -> dict:
    folder = ROOT / "docs/verification"
    data, extra, base, result = (
        read_json(folder / name)
        for name in (
            "compound-v11-development-data.json",
            "compound-v14-training-windows.json",
            "compound-v13-development.json",
            "compound-v14-development.json",
        )
    )
    for obj in (data, extra, base, result):
        check_seal(obj)
    compare(extra["parent_sha256"], data["content_sha256"], "native parent")
    compare(result["additional_sha256"], extra["content_sha256"], "extra binding")
    compare(result["v13_result_sha256"], base["content_sha256"], "base binding")
    sources = [
        s
        for name in (
            "compound-nomination-inventory.json",
            "compound-v13-nomination-additions.json",
        )
        for s in read_json(folder / name)["sources"]
    ]
    codes = {
        e: dict(zip(("HARD", "MEDIUM", "SOFT"), values, strict=True))
        for s in sources
        for e, values in s["events"].items()
    }

    def vector(row: dict) -> list:
        compound = row["compounds"][1]
        prefix = row["current_prefix_s"]
        year = datetime.fromtimestamp(row["forecast_at_s"], tz=timezone.utc).year
        return [
            *[v - median(prefix) for v in prefix],
            median(prefix),
            row["ages"][0],
            *[int(compound == c) for c in ("HARD", "MEDIUM", "SOFT")],
            *[int(codes[str(row["session"])][compound] == n) for n in range(1, 7)],
            *[int(year == y) for y in (2023, 2024, 2025)],
        ]

    paired = unique_rows(data["cases"])
    pools = {
        "paired": paired,
        "expanded": unique_rows([*paired, *extra["additional_windows"]]),
    }
    compare(sorted(result["recipes"]), sorted(pools), "recipes")
    compare(result["paired_windows"], len(paired), "paired training size")
    compare(
        result["expanded_windows"], len(pools["expanded"]), "expanded training size"
    )
    previous = {p["index"]: p for p in base["recipes"]["nominated"]["predictions"]}
    count = 0
    for name, recipe in result["recipes"].items():
        compare(
            [f["event"] for f in recipe["folds"]],
            sorted(data["sources"]),
            "fold inventory",
        )
        pool = pools[name]
        reconstructed = {}
        for event, model in recipe["models"].items():
            training = [r for r in pool if r["session"] != event]
            x = np.array([vector(r) for r in training])
            y = np.array(
                [
                    np.array(r["current_target_s"]) - median(r["current_prefix_s"])
                    for r in training
                ]
            )
            sizes = Counter(r["session"] for r in training)
            w = np.array(
                [len(training) / (len(sizes) * sizes[r["session"]]) for r in training]
            )
            center = np.average(x, axis=0, weights=w)
            scale = np.sqrt(np.average((x - center) ** 2, axis=0, weights=w))
            scale[np.ptp(x, axis=0) == 0] = 1.0
            z = (x - center) / scale
            y_center = np.average(y, axis=0, weights=w)
            beta = np.linalg.solve(
                z.T @ (w[:, None] * z) + 10 * np.eye(z.shape[1]),
                z.T @ (w[:, None] * (y - y_center)),
            ).T
            expected = {
                "center": center.tolist(),
                "scale": scale.tolist(),
                "coefficients": beta.tolist(),
                "intercept": y_center.tolist(),
            }
            compare(model, expected, "ridge normal equations")
            reconstructed[event] = expected
        compare(
            sorted(p["index"] for p in recipe["predictions"]),
            list(range(len(data["cases"]))),
            "case denominator",
        )
        groups = {}
        for saved in recipe["predictions"]:
            row = data["cases"][saved["index"]]
            event = str(row["session"])
            compare(saved["event"], event, "case event")
            m = reconstructed[event]
            z = (np.array(vector(row)) - m["center"]) / m["scale"]
            raw = (
                np.array(m["coefficients"]) @ z
                + m["intercept"]
                + median(row["current_prefix_s"])
                - row["current_prefix_s"]
            )
            aux = np.array(row["current_prefix_s"]) + np.clip(raw, -2, 2)
            laps = (aux + previous[saved["index"]]["laps_s"]) / 2
            ref = row["reference_target_s"]
            values = [
                median(ref) - median(laps),
                median(a - b for a, b in zip(ref, laps, strict=True)),
            ]
            compare(saved["auxiliary_laps_s"], aux.tolist(), "auxiliary laps")
            compare(saved["laps_s"], laps.tolist(), "blended laps")
            compare(saved["auxiliary_bound_hits"], int(sum(abs(raw) > 2)), "bounds")
            compare(saved["contrasts_s"], values, "contrasts")
            baselines = [
                median(ref) - median(row["current_prefix_s"]),
                median(
                    a - b for a, b in zip(ref, row["current_prefix_s"], strict=True)
                ),
            ]
            for j, (prefix, target) in enumerate(LABELS):
                decision = crossing(row[prefix], values[j])
                compare(saved["crossings"][j], decision, "decision")
                groups.setdefault((event, j), []).append(
                    {
                        **row,
                        "predicted_s": values[j],
                        "predicted_crossover": decision,
                        "reference_persistence_s": baselines[0],
                        "own_error": abs(baselines[j] - row[target]),
                    }
                )
            count += 1
        failures, informative = [], 0
        for fold in recipe["folds"]:
            event = fold["event"]
            compare(fold["cases"], data["sources"][event]["blocks"], "race denominator")
            compare(
                fold["training_windows"],
                sum(r["session"] != event for r in pool),
                "training event exclusion",
            )
            metrics = []
            for j in range(2):
                group = groups.get((event, j), [])
                if group:
                    metric = event_report(group)["labels"][j]
                    metric["label_reference_mae_s"] = mean(
                        r["own_error"] for r in group
                    )
                    if metric["mae_s"] > metric["label_reference_mae_s"] + 1e-12:
                        metric["passed"] = False
                        metric["failure_codes"].append(
                            "PACE_WORSE_THAN_LABEL_REFERENCE"
                        )
                    metrics.append(metric)
            compare(fold["labels"], metrics, "race gates")
            if any(not m["passed"] for m in metrics):
                failures.append(event)
            informative += bool(metrics) and all(m["observed"] for m in metrics)
        compare(recipe["failed_events"], failures, "failed races")
        compare(recipe["qualified"], not failures and informative >= 2, "qualification")
    compare(
        result["development_qualified"],
        result["recipes"]["expanded"]["qualified"],
        "primary",
    )
    compare(
        result["new_holdout_acquisition_allowed"],
        result["development_qualified"],
        "holdout permission",
    )
    return seal(
        {
            "schema": "compound-unpaired-independent-audit-v14",
            "result_sha256": result["content_sha256"],
            "forecasts_verified": count,
            "independent_ridge_solves": sum(
                len(r["models"]) for r in result["recipes"].values()
            ),
            "audit_passed": True,
            "scope": "INDEPENDENT_RIDGE_EQUATIONS_CHECKPOINTS_AND_EVENT_GATES",
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, audit())
