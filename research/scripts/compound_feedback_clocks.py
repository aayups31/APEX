"""Recover the first later retained lap witnessing each completed R041 window."""

import argparse
from itertools import pairwise
from math import isfinite
from pathlib import Path

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from compound_unpaired_windows import opened_field
from diagnose_compound_decision import ROOT


def prepare(root):
    data = read_json(ROOT / "docs/verification/compound-v11-development-data.json")
    check_seal(data)
    clocks = [None] * len(data["cases"])
    for event, source in data["sources"].items():
        stints = {
            (s["driver"], s["stint"]): s for s in opened_field(event, source, root)
        }
        for i, r in enumerate(data["cases"]):
            if str(r["session"]) != event:
                continue
            stint = stints[r["driver"], r["stints"][1]]
            ages = r["ages"][-3:]
            if [stint["values"][a] for a in ages] != r["current_target_s"]:
                raise ValueError("Native feedback target mismatch")
            ends = [stint["ends"][a] for a in ages]
            later = sorted(a for a in stint["ends"] if a > ages[-1])
            witness = stint["ends"][later[0]] if later else None
            times = [r["forecast_at_s"], *ends]
            if witness is not None:
                times.append(witness)
            if not all(isfinite(t) for t in times) or any(
                a >= b for a, b in pairwise(times)
            ):
                raise ValueError("Invalid feedback chronology")
            clocks[i] = {
                "target_ends": ends,
                "witness_age": later[0] if later else None,
                "release_s": witness,
            }
    if any(c is None for c in clocks):
        raise ValueError("Incomplete native clock reconstruction")
    return seal(
        {
            "schema": "feedback-clocks-v16",
            "dataset_sha256": data["content_sha256"],
            "clocks": clocks,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--native-root", type=Path, default=ROOT / ".cache")
    args = parser.parse_args()
    write_manifest(args.output, prepare(args.native_root))
