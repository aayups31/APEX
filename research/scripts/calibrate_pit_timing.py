"""R045 held-out pit timing calibration from verified development archives."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import write_manifest
from apexsim.research.evidence import seal
from confirm_compound_multiseason import BASE, canonical_file_sha

TRAIN = {1: "bahrain", 3: "albert_park", 14: "monza", 15: "marina_bay"}
TEST = {1: "bahrain", 3: "albert_park", 6: "miami", 16: "monza", 18: "marina_bay"}
CHANNELS = ("lane_s", "inlap_proxy_s", "outlap_proxy_s", "total_proxy_s")
PROTOCOL = BASE / "research/protocols/PIT_TIMING_R045.md"
COLUMNS = [
    "DriverNumber",
    "LapNumber",
    "Stint",
    "TrackStatus",
    "Deleted",
    "IsAccurate",
    "LapTime",
    "LapStartTime",
    "Time",
    "PitInTime",
    "PitOutTime",
]


def index_laps(frame):
    drivers = defaultdict(dict)
    for driver, lap, stint, flag, deleted, accurate, *clocks in frame[
        COLUMNS
    ].itertuples(index=False, name=None):
        if pd.isna(driver) or pd.isna(lap) or int(lap) != lap:
            continue
        duration, start, end, pit_in, pit_out = [
            None if pd.isna(t) else t.total_seconds() for t in clocks
        ]
        timed = (
            duration is not None
            and start is not None
            and end is not None
            and duration > 0
            and abs(end - start - duration) <= 0.1
        )
        row = {
            "valid": timed and flag == "1" and deleted is False,
            "accurate": accurate is True,
            "stint": None if pd.isna(stint) else int(stint),
            "duration": duration,
            "start": start,
            "end": end,
            "pit_in": pit_in,
            "pit_out": pit_out,
        }
        if int(lap) in drivers[str(driver)]:
            raise ValueError("Duplicate driver/lap identity in pit timing")
        drivers[str(driver)][int(lap)] = row
    return drivers


def clean(row):
    return (
        row is not None
        and row["valid"]
        and row["accurate"]
        and row["stint"] is not None
        and row["pit_in"] is None
        and row["pit_out"] is None
    )


def extract(frame):
    field = index_laps(frame)
    kept, excluded = [], Counter()
    for driver, laps in sorted(field.items()):
        for n, inlap in sorted(laps.items()):
            if inlap["pit_in"] is None:
                continue
            outlap = laps.get(n + 1)
            if not outlap or outlap["pit_out"] is None:
                excluded["missing_adjacent_exit"] += 1
                continue
            if not (
                inlap["valid"]
                and outlap["valid"]
                and inlap["pit_out"] is None
                and outlap["pit_in"] is None
                and inlap["start"] <= inlap["pit_in"] <= inlap["end"]
                and outlap["start"] <= outlap["pit_out"] <= outlap["end"]
                and abs(inlap["end"] - outlap["start"]) <= 0.1
                and outlap["pit_out"] > inlap["pit_in"]
            ):
                excluded["pit_clock_or_quality_failed"] += 1
                continue
            prefix = [laps.get(k) for k in range(n - 3, n)]
            if not all(clean(r) and r["stint"] == inlap["stint"] for r in prefix):
                excluded["missing_clean_subject_prefix"] += 1
                continue
            controls = []
            for peer, path in sorted(field.items()):
                if peer == driver:
                    continue
                group = [path.get(k) for k in range(n - 3, n + 2)]
                if (
                    all(map(clean, group))
                    and len({r["stint"] for r in group}) == 1
                    and abs(group[-3]["end"] - prefix[-1]["end"]) <= 120
                ):
                    base = median(r["duration"] for r in group[:3])
                    controls.append(
                        {
                            "driver": peer,
                            "changes_s": [r["duration"] - base for r in group[3:]],
                        }
                    )
            if len(controls) < 3:
                excluded["insufficient_clean_peers"] += 1
                continue
            base = median(r["duration"] for r in prefix)
            shifts = [median(c["changes_s"][i] for c in controls) for i in (0, 1)]
            inc_in = inlap["duration"] - base - shifts[0]
            inc_out = outlap["duration"] - base - shifts[1]
            kept.append(
                {
                    "driver": driver,
                    "inlap": n,
                    "base_s": base,
                    "peers": controls,
                    "pit_entry_s": inlap["pit_in"],
                    "pit_exit_s": outlap["pit_out"],
                    "lane_s": outlap["pit_out"] - inlap["pit_in"],
                    "inlap_proxy_s": inc_in,
                    "outlap_proxy_s": inc_out,
                    "total_proxy_s": inc_in + inc_out,
                }
            )
    return kept, dict(excluded)


def load(root, year, round_number):
    assert_development_event(year, round_number)
    name = (
        f"r026-fastf1-2023-r{round_number}-race-20261013"
        if year == 2023
        else f"fastf1-2024-r{round_number}-race-20261011"
    )
    archive = root / name
    manifest = verify_fastf1_archive(archive)
    query = manifest["query"]
    if (query["year"], query["round_number"], query["session"]) != (
        year,
        round_number,
        "R",
    ):
        raise ValueError("Wrong pit timing archive identity")
    rows, excluded = extract(
        pd.read_parquet(archive / "tables/laps.parquet", columns=COLUMNS)
    )
    return {
        "source_sha256": manifest["content_sha256"],
        "stops": rows,
        "exclusions": excluded,
    }


def fit(training):
    """Train circuit and pooled medians from the training season only."""
    grouped = defaultdict(list)
    for event in training.values():
        grouped[event["circuit"]].extend(event["stops"])
    pooled = [r for group in grouped.values() for r in group]
    return {
        "pooled": {k: median(r[k] for r in pooled) for k in CHANNELS},
        "circuits": {
            circuit: {k: median(r[k] for r in rows) for k in CHANNELS}
            for circuit, rows in sorted(grouped.items())
            if len(rows) >= 5
        },
    }


def score(model, evaluation):
    folds = {}
    for name, event in evaluation.items():
        rows = event["stops"]
        values = model["circuits"].get(event["circuit"])
        folds[name] = {
            "supported": len(rows),
            "fallback": values is None,
            "candidate_mae_s": {
                k: mean(abs(r[k] - (values or model["pooled"])[k]) for r in rows)
                if rows
                else None
                for k in CHANNELS
            },
            "pooled_mae_s": {
                k: mean(abs(r[k] - model["pooled"][k]) for r in rows) if rows else None
                for k in CHANNELS
            },
        }
    supported = [f for f in folds.values() if f["supported"]]
    target = "total_proxy_s"
    candidate = mean(f["candidate_mae_s"][target] for f in supported)
    baseline = mean(f["pooled_mae_s"][target] for f in supported)
    wins = sum(
        f["candidate_mae_s"][target] < f["pooled_mae_s"][target] for f in supported
    )
    checks = {
        "five_events_with_five_stops": len(folds) == 5
        and all(f["supported"] >= 5 for f in folds.values()),
        "better_macro_total_mae": candidate < baseline,
        "improves_at_least_three_events": wins >= 3,
    }
    return {
        "folds": folds,
        "macro_total_mae_s": {"candidate": candidate, "pooled": baseline},
        "improved_events": wins,
        "checks": checks,
        "passed": all(checks.values()),
    }


def run(root):
    def season(year, circuits):
        return {
            f"F1_{year}_R{n:02}": {"circuit": circuit, **load(root, year, n)}
            for n, circuit in circuits.items()
        }

    training, held_out = season(2023, TRAIN), season(2024, TEST)
    model = fit(training)
    return seal(
        {
            "schema": "apex-pit-timing-r045-v1",
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(PROTOCOL),
            "training": training,
            "evaluation": held_out,
            "calibration": model,
            "result": score(model, held_out),
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
