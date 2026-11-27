"""Assess the incremental predictive value of relative outlap pace for R041."""

import argparse
from pathlib import Path

from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_outlap_support import EVENTS
from audit_compound_outlap_support import run as audit_coverage
from audit_compound_race_context import check_result
from compound_field_evolution import score
from compound_sector_traffic import load_sources
from confirm_compound_multiseason import canonical_file_sha
from prepare_compound_pit_exit import BASE, FOLDER

PROTOCOL = BASE / "research/protocols/COMPOUND_OUTLAP_PACE_V32.md"


def evaluate(data, control, base, coverage):
    """Fit each test race using the other races and saved pre-cutoff inputs."""
    check_seal(coverage)
    if coverage["cohort_sha256"] != data["content_sha256"]:
        raise ValueError("Outlap coverage comes from a different cohort")
    records = {
        row["index"]: (event, row)
        for event, race in coverage["races"].items()
        for row in race["records"]
    }
    if set(records) != set(range(len(data["cases"]))):
        raise ValueError("Incomplete outlap forecast inputs")
    vectors = []
    for index, (row, x) in enumerate(zip(data["cases"], base, strict=True)):
        event, observation = records[index]
        if event != str(row["session"]):
            raise ValueError("Unexpected outlap observation race")
        relative = observation.get("outlap_relative_s")
        if relative is not None and (
            observation["outlap_end_s"] > row["forecast_at_s"]
            or any(
                peer["end_s"] > row["forecast_at_s"] for peer in observation["peers"]
            )
        ):
            raise ValueError("Outlap input exceeds cutoff")
        vectors.append(
            x + [relative if relative is not None else 0.0, float(relative is not None)]
        )
    result = score(data, vectors)
    previous = set(control["results"]["nomination_practice_ridge"]["failed_events"])
    failed = set(result["failed_events"])
    gains, losses = sorted(previous - failed), sorted(failed - previous)
    focus = sorted(set(EVENTS) - failed)
    flags = {
        "development_qualified": result["qualified"],
        "new_holdout_acquisition_allowed": result["qualified"],
    }
    return {
        "result": result,
        "supported": sum(
            r.get("outlap_relative_s") is not None for _, r in records.values()
        ),
        "gained_events": gains,
        "lost_events": losses,
        "persistent_failures_passing": focus,
        "continue_direction": len(failed) < len(previous) and bool(focus),
        "audit": check_result(data, seal({"result": result, **flags})),
        **flags,
    }


def run(root):
    data, control, base = load_sources()
    coverage = audit_coverage(
        root, tuple(e for e, s in data["sources"].items() if s["blocks"])
    )
    focus = read_json(FOLDER / "compound-outlap-support.json")
    check_seal(focus)
    if any(coverage["races"][e] != focus["races"][e] for e in EVENTS):
        raise ValueError("Outlap coverage differs from frozen seven-race audit")
    return seal(
        {
            "schema": "compound-outlap-pace-v32",
            "dataset_sha256": data["content_sha256"],
            "control_sha256": control["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(PROTOCOL),
            "coverage": coverage,
            **evaluate(data, control, base, coverage),
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
