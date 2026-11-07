"""Replay a chronological stream of same-race peer forecast errors."""

import argparse
from collections import defaultdict
from math import isfinite
from pathlib import Path
from statistics import mean, median

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from diagnose_compound_line import FOLDER, score_forecasts


def race_forecasts(rows, base, clocks, indices):
    windows = defaultdict(list)
    for i in indices:
        r, clock = rows[i], clocks[i]
        if clock["release_s"] is None:
            continue
        if not (
            r["forecast_at_s"]
            < min(clock["target_ends"])
            <= max(clock["target_ends"])
            < clock["release_s"]
        ):
            raise ValueError("Future target cannot be released early")
        key = r["driver"], r["stints"][1], tuple(r["ages"])
        windows[key].append(i)
    queue = []
    for group in windows.values():
        i = group[0]
        if any(
            clocks[j] != clocks[i] or rows[j]["compounds"][1] != rows[i]["compounds"][1]
            for j in group
        ):
            raise ValueError(
                "Inconsistent clock or compound for repeated current window"
            )
        queue.append((clocks[i]["release_s"], group))
    queue.sort()
    latest, forecasts, trace = defaultdict(dict), {}, {}
    cursor = 0
    for i in sorted(indices, key=lambda j: rows[j]["forecast_at_s"]):
        r = rows[i]
        while cursor < len(queue) and queue[cursor][0] < r["forecast_at_s"]:
            _, group = queue[cursor]
            sample = rows[group[0]]
            errors = []
            for j in group:
                if rows[j]["current_target_s"] != sample["current_target_s"]:
                    raise ValueError("Inconsistent completed peer target")
                errors.append(
                    median(
                        a - b
                        for a, b in zip(
                            rows[j]["current_target_s"], base[j]["laps_s"], strict=True
                        )
                    )
                )
            latest[sample["compounds"][1]][sample["driver"]] = (mean(errors), group)
            cursor += 1
        peers = [
            item
            for driver, item in latest[r["compounds"][1]].items()
            if driver != r["driver"]
        ]
        n = len(peers)
        shift = median(v for v, _ in peers) * n / (n + 3) if n else 0.0
        laps = base[i]["laps_s"]
        hits = 0
        if n:
            changes = [
                lap + shift - p
                for lap, p in zip(laps, r["current_prefix_s"], strict=True)
            ]
            if not all(isfinite(d) for d in changes):
                raise ValueError("Nonfinite peer correction")
            hits = sum(abs(d) > 2 for d in changes)
            laps = [
                p + min(2, max(-2, d))
                for p, d in zip(r["current_prefix_s"], changes, strict=True)
            ]
        forecasts[i] = laps, hits
        trace[i] = {"peer_windows": [group for _, group in peers], "shift_s": shift}
    return forecasts, trace


def study():
    data, timing, parent = [
        read_json(FOLDER / name)
        for name in (
            "compound-v11-development-data.json",
            "compound-v16-feedback-clocks.json",
            "compound-v13-development.json",
        )
    ]
    for doc in (data, timing, parent):
        check_seal(doc)
    if (
        not timing["dataset_sha256"]
        == data["content_sha256"]
        == parent["dataset_sha256"]
    ):
        raise ValueError("Feedback data seal mismatch")
    rows, clocks = data["cases"], timing["clocks"]
    control = parent["recipes"]["nominated"]
    base = {p["index"]: p for p in control["predictions"]}
    if len(clocks) != len(rows) or set(base) != set(range(len(rows))):
        raise ValueError("Missing feedback input")
    forecasts, trace = {}, {}
    for event in data["sources"]:
        indices = [i for i, r in enumerate(rows) if str(r["session"]) == event]
        if any(base[i]["event"] != event for i in indices):
            raise ValueError("Feedback forecast belongs to wrong race")
        predicted, peers = race_forecasts(rows, base, clocks, indices)
        forecasts.update(predicted)
        trace.update(peers)
    result = score_forecasts(rows, data["sources"], forecasts)
    oracle = {
        i: (r["current_target_s"] if trace[i]["peer_windows"] else base[i]["laps_s"], 0)
        for i, r in enumerate(rows)
    }
    ceiling = score_forecasts(rows, data["sources"], oracle)
    return seal(
        {
            "schema": "compound-prequential-feedback-v16",
            "clocks_sha256": timing["content_sha256"],
            "control_sha256": parent["content_sha256"],
            "result": result,
            "feedback": [trace[i] for i in range(len(rows))],
            "supported_case_oracle_diagnostic": {
                "folds": ceiling["folds"],
                "failed_events": ceiling["failed_events"],
            },
            "development_qualified": result["qualified"],
            "new_holdout_acquisition_allowed": result["qualified"],
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, study())
