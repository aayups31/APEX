"""Evaluate an expanded training-only pit timing set on the frozen R045 test."""

import argparse
from pathlib import Path

import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from calibrate_pit_timing import BASE, COLUMNS, canonical_file_sha, extract, fit, score

PROTOCOL = BASE / "research/protocols/PIT_TIMING_EXPANDED_R045.md"
PARENT = BASE / "docs/verification/pit-timing-r045-v1.json"
ADDITIONS = {
    (2022, 3): "albert_park",
    (2022, 5): "miami",
    (2022, 17): "marina_bay",
}


def evaluate(parent, added):
    """Fit only historical records, then evaluate both frozen comparators."""
    expected = {f"F1_{y}_R{n:02}": circuit for (y, n), circuit in ADDITIONS.items()}
    if {event: item["circuit"] for event, item in added.items()} != expected:
        raise ValueError("Expanded pit training inventory changed")
    if parent["training"].keys() & added.keys() or (
        (parent["training"].keys() | added.keys()) & parent["evaluation"].keys()
    ):
        raise ValueError("Held-out pit records overlap training")
    model = fit({**parent["training"], **added})
    expanded = score(model, parent["evaluation"])
    # Score the same candidate with the original baseline, including on fallback circuits.
    frozen = score(
        {
            "pooled": parent["calibration"]["pooled"],
            "circuits": {
                e["circuit"]: model["circuits"].get(e["circuit"], model["pooled"])
                for e in parent["evaluation"].values()
            },
        },
        parent["evaluation"],
    )
    for event, fold in frozen["folds"].items():
        fold["fallback"] = expanded["folds"][event]["fallback"]
    return {
        "calibration": model,
        "comparison_original_pool": frozen,
        "comparison_expanded_pool": expanded,
        "passed": frozen["passed"] and expanded["checks"]["better_macro_total_mae"],
    }


def run(root):
    parent = read_json(PARENT)
    check_seal(parent)
    added = {}
    for (year, number), circuit in ADDITIONS.items():
        assert_development_event(year, number)
        archive = root / f"r045-fastf1-{year}-r{number}"
        manifest = verify_fastf1_archive(archive)
        query = manifest["query"]
        if (query["year"], query["round_number"], query["session"]) != (
            year,
            number,
            "R",
        ):
            raise ValueError("Expanded pit archive identity changed")
        stops, exclusions = extract(
            pd.read_parquet(archive / "tables/laps.parquet", columns=COLUMNS)
        )
        added[f"F1_{year}_R{number:02}"] = {
            "circuit": circuit,
            "stops": stops,
            "exclusions": exclusions,
            "source_sha256": manifest["content_sha256"],
        }
    return seal(
        {
            "schema": "apex-pit-timing-r045-v3",
            "parent_sha256": parent["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(PROTOCOL),
            "training_additions": added,
            **evaluate(parent, added),
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
