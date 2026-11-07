"""Measure crossover-label sensitivity under the three R021 fuel priors."""

import argparse
from math import isclose
from pathlib import Path

from apexsim.provenance import write_manifest
from apexsim.research.compound_readiness import LABELS, crossing
from apexsim.research.evidence import check_seal, read_json, seal
from compound_line_proximity import archive_laps
from diagnose_compound_decision import ROOT, contrasts

COEFFICIENTS = (0.020, 0.030, 0.040)


def reconstruct(laps, coefficient):
    """Adjust only the fuel time coefficient, holding all native observations fixed."""
    values = []
    for group in laps:
        projected = []
        for number, duration, pace in group:
            if number < 1 or int(number) != number:
                raise ValueError("Invalid native fuel lap")
            mass = max(0.0, 105.0 - 1.4 * (number - 1))
            if not isclose(duration - 0.030 * mass, pace, abs_tol=1e-10, rel_tol=0):
                raise ValueError("Native fuel correction differs from original pace")
            projected.append(pace + (0.030 - coefficient) * mass)
        values.append(projected)
    ref_prefix, current_prefix, ref_target, current_target = values
    prefix = contrasts(ref_prefix, current_prefix)
    target = contrasts(ref_target, current_target)
    return {
        "prefix_s": prefix,
        "target_s": target,
        "observed": [crossing(a, b) for a, b in zip(prefix, target, strict=True)],
    }


def audit(root):
    directory = ROOT / "docs/verification"
    data, timing = [
        read_json(directory / f)
        for f in (
            "compound-v11-development-data.json",
            "compound-v16-feedback-clocks.json",
        )
    ]
    for doc in (data, timing):
        check_seal(doc)
    if timing["dataset_sha256"] != data["content_sha256"] or len(
        timing["clocks"]
    ) != len(data["cases"]):
        raise ValueError("Unbound current target clocks")
    result = []
    for event, source in data["sources"].items():
        native = archive_laps(root, event, source)
        lookup = {
            (end, driver): (lap, duration) for end, driver, lap, duration in native
        }
        if len(native) != len(lookup):
            raise ValueError("Ambiguous native timing-line join")
        for i, r in enumerate(data["cases"]):
            if str(r["session"]) != event:
                continue
            current = [
                {"end_s": t, "pace_s": p}
                for t, p in zip(
                    timing["clocks"][i]["target_ends"],
                    r["current_target_s"],
                    strict=True,
                )
            ]
            groups = [
                [(*lookup[obs["end_s"], r["driver"]], obs["pace_s"]) for obs in samples]
                for samples in (
                    r["reference_history"][:3],
                    r["current_history"][-3:],
                    r["reference_history"][-3:],
                    current,
                )
            ]
            cases = [reconstruct(groups, c) for c in COEFFICIENTS]
            for j, (start, target) in enumerate(LABELS):
                primary = cases[1]
                if (
                    abs(r[start] - primary["prefix_s"][j]) > 1e-10
                    or abs(r[target] - primary["target_s"][j]) > 1e-10
                    or crossing(r[start], r[target]) != primary["observed"][j]
                ):
                    raise ValueError("Primary crossover label changed during recovery")
            result.append(
                {"index": i, "event": event, "windows": groups, "sensitivity": cases}
            )
    result.sort(key=lambda r: r["index"])
    if [r["index"] for r in result] != list(range(len(data["cases"]))):
        raise ValueError("Incomplete fuel sensitivity cohort")
    return seal(
        {
            "schema": "compound-crossover-fuel-sensitivity",
            "scope": "DIAGNOSTIC_ONLY_ORIGINAL_GATE_PRESERVED",
            "coefficients_s_per_kg": COEFFICIENTS,
            "dataset_sha256": data["content_sha256"],
            "clocks_sha256": timing["content_sha256"],
            "cases": result,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=ROOT / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, audit(args.native_root))
