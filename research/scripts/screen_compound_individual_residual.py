"""Measure individual pace-change predictability after removing matched field change."""

import argparse
from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path
from statistics import mean, median

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from confirm_compound_multiseason import canonical_file_sha
from prepare_compound_pit_exit import BASE, FOLDER
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


def panel(rows, contexts, summaries):
    groups = defaultdict(dict)
    eligible = 0
    for i, (row, ctx, groups_of_laps) in enumerate(
        zip(rows, contexts, summaries, strict=True)
    ):
        prefix_laps = groups_of_laps[0]
        if (
            len(prefix_laps) != 3
            or min(lap["coverage"] for lap in prefix_laps) < 0.9
            or not ctx["future_peer_counts"][0]
        ):
            continue
        eligible += 1
        key = str(row["session"]), row["driver"], row["stints"][1]
        ages = tuple(row["ages"])
        if len(ages) != 12 or any(b != a + 1 for a, b in pairwise(ages)):
            raise ValueError(
                "Individual screen requires a contiguous twelve-age window"
            )
        prefix = row["current_prefix_s"]
        center = median(prefix)
        timing = [v - center for v in prefix] + [center, ages[0]]
        timing += [int(row["compounds"][1] == c) for c in ("HARD", "MEDIUM", "SOFT")]
        timing += ctx["causal"][:6]
        means = [lap["means"] for lap in prefix_laps]
        native = [mean(v) for v in zip(*means, strict=True)] + [
            b - a for a, b in zip(means[0], means[-1], strict=True)
        ]
        target = median(row["current_target_s"]) - center - ctx["future_diagnostic"][0]
        item = {"timing": timing, "native": native, "target": target}
        previous = groups[key].setdefault(ages, (i, item))
        if item != previous[1]:
            raise ValueError("Repeated individual window has inconsistent evidence")
    selected = []
    for key, windows in sorted(groups.items()):
        last = -1
        for ages, (i, item) in sorted(windows.items()):
            if ages[0] > last:
                selected.append({"index": i, "event": key[0], **item})
                last = ages[-1]
    return eligible, selected


def forecasts(rows, event, include_native):
    train = [r for r in rows if r["event"] != event]
    test = [r for r in rows if r["event"] == event]
    counts = Counter(r["event"] for r in train)
    weights = [len(train) / (len(counts) * counts[r["event"]]) for r in train]

    def matrix(records):
        return np.asarray(
            [r["timing"] + (r["native"] if include_native else []) for r in records]
        )

    x = matrix(train)
    scaler = StandardScaler().fit(x, sample_weight=weights)
    model = Ridge(alpha=10.0, solver="svd").fit(
        scaler.transform(x), [r["target"] for r in train], sample_weight=weights
    )
    return model.predict(scaler.transform(matrix(test))).tolist()


def run():
    data, field, native, control = [
        read_json(FOLDER / f"compound-{name}.json")
        for name in (
            "v24-cohort",
            "v28-development",
            "v24-telemetry",
            "v24-development",
        )
    ]
    for doc in (data, field, native, control):
        check_seal(doc)
    if (
        field["dataset_sha256"] != data["content_sha256"]
        or native["dataset_sha256"] != data["content_sha256"]
        or control["telemetry_sha256"] != native["content_sha256"]
        or control["content_sha256"] != field["control_sha256"]
    ):
        raise ValueError("Individual residual sources changed")
    eligible, rows = panel(data["cases"], field["contexts"], native["lap_summaries"])
    folds, predictions = {}, []
    for event in sorted({r["event"] for r in rows}):
        test = [r for r in rows if r["event"] == event]
        timing, telemetry = [
            forecasts(rows, event, use_native) for use_native in (False, True)
        ]
        fold = [
            {
                "event": event,
                "index": r["index"],
                "target": r["target"],
                "zero": 0.0,
                "timing": t,
                "telemetry": n,
            }
            for r, t, n in zip(test, timing, telemetry, strict=True)
        ]
        predictions.extend(fold)
        folds[event] = {
            k: mean(abs(p[k] - p["target"]) for p in fold)
            for k in ("zero", "timing", "telemetry")
        }
    macro = {
        k: mean(f[k] for f in folds.values()) for k in ("zero", "timing", "telemetry")
    }
    wins = {
        k: sum(f["telemetry"] < f[k] for f in folds.values())
        for k in ("zero", "timing")
    }
    return seal(
        {
            "scope": "DEVELOPMENT_INDIVIDUAL_RESIDUAL_SCREEN",
            "dataset_sha256": data["content_sha256"],
            "field_sha256": field["content_sha256"],
            "native_sha256": native["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(
                BASE / "research/protocols/COMPOUND_INDIVIDUAL_RESIDUAL_SCREEN.md"
            ),
            "eligible_comparisons": eligible,
            "disjoint_windows": len(rows),
            "supported_races": len(folds),
            "fold_mae_s": folds,
            "macro_mae_s": macro,
            "telemetry_race_wins": wins,
            "predictions": predictions,
            "expand_training": macro["telemetry"] < min(macro["timing"], macro["zero"])
            and 2 * wins["timing"] > len(folds),
            "qualifies_crossover": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, run())
