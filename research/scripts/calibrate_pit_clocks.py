"""R045 circuit calibration anchored by measured pit timing components."""

import argparse
from pathlib import Path
from statistics import median

import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from calibrate_pit_timing import (
    BASE,
    COLUMNS,
    TRAIN,
    canonical_file_sha,
    index_laps,
    score,
)

PROTOCOL = BASE / "research/protocols/PIT_TIMING_CLOCKS_R045.md"
EVIDENCE = BASE / "docs/verification/pit-timing-r045-v1.json"


def extract_clocks(frame):
    clock_pairs = []
    for driver, laps in sorted(index_laps(frame).items()):
        for n, entry in sorted(laps.items()):
            exit_lap = laps.get(n + 1)
            if not (
                exit_lap
                and entry["valid"]
                and exit_lap["valid"]
                and entry["pit_in"] is not None
                and exit_lap["pit_out"] is not None
                and entry["pit_out"] is None
                and exit_lap["pit_in"] is None
                and entry["start"] <= entry["pit_in"] <= entry["end"]
                and exit_lap["start"] <= exit_lap["pit_out"] <= exit_lap["end"]
                and abs(entry["end"] - exit_lap["start"]) <= 0.1
                and exit_lap["pit_out"] > entry["pit_in"]
            ):
                continue
            clock_pairs.append(
                {
                    "driver": driver,
                    "inlap": n,
                    "before_line_s": entry["end"] - entry["pit_in"],
                    "after_line_s": exit_lap["pit_out"] - entry["end"],
                    "lane_s": exit_lap["pit_out"] - entry["pit_in"],
                }
            )
    return clock_pairs


def fit(pooled, by_circuit):
    rows = [r for group in by_circuit.values() for r in group]
    before = median(r["before_line_s"] for r in rows)
    after = median(r["after_line_s"] for r in rows)
    circuits = {}
    for circuit, group in by_circuit.items():
        if len(group) < 5:
            continue
        pre = median(r["before_line_s"] for r in group) - before
        post = median(r["after_line_s"] for r in group) - after
        circuits[circuit] = {
            "lane_s": median(r["lane_s"] for r in group),
            "inlap_proxy_s": pooled["inlap_proxy_s"] + pre,
            "outlap_proxy_s": pooled["outlap_proxy_s"] + post,
            "total_proxy_s": pooled["total_proxy_s"] + pre + post,
        }
    return {"pooled": pooled, "circuits": circuits}


def run(root):
    prior = read_json(EVIDENCE)
    check_seal(prior)
    clocks = {}
    for n, circuit in TRAIN.items():
        assert_development_event(2023, n)
        folder = root / f"r026-fastf1-2023-r{n}-race-20261013"
        manifest = verify_fastf1_archive(folder)
        old = prior["training"][f"F1_2023_R{n:02}"]
        if (old["circuit"], old["source_sha256"]) != (
            circuit,
            manifest["content_sha256"],
        ):
            raise ValueError("R045 clock-training source differs from the frozen study")
        clocks[circuit] = extract_clocks(
            pd.read_parquet(folder / "tables/laps.parquet", columns=COLUMNS)
        )
    model = fit(prior["calibration"]["pooled"], clocks)
    return seal(
        {
            "schema": "apex-pit-timing-clock-r045-v2",
            "parent_sha256": prior["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(PROTOCOL),
            "training_clocks": clocks,
            "calibration": model,
            "result": score(model, prior["evaluation"]),
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
