"""Count which crossover errors change when the same model sees the observed field."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from apexsim.provenance import write_manifest
from apexsim.research.compound_readiness import LABELS, crossing
from apexsim.research.evidence import check_seal, read_json, seal
from diagnose_compound_line import FOLDER


def audit():
    data, previous, actual, fuel = [
        read_json(FOLDER / f"compound-{name}.json")
        for name in (
            "v24-cohort",
            "v28-development",
            "v29-development",
            "v24-residual-audit",
        )
    ]
    for doc in (data, previous, actual, fuel):
        check_seal(doc)
    if any(
        d["dataset_sha256"] != data["content_sha256"] for d in (previous, actual, fuel)
    ) or (previous["content_sha256"] != actual["parent_sha256"]):
        raise ValueError("Field diagnostic parents disagree")

    def ordered(result):
        return sorted(result["predictions"], key=lambda p: p["index"])

    predicted = ordered(actual["result"])
    privileged = ordered(previous["future_field_diagnostic_only"])
    totals, events = defaultdict(Counter), defaultdict(Counter)
    for i, (row, a, b, f, context) in enumerate(
        zip(
            data["cases"],
            predicted,
            privileged,
            fuel["cases"],
            previous["contexts"],
            strict=True,
        )
    ):
        event = str(row["session"])
        if any((p["index"], p["event"]) != (i, event) for p in (a, b, f)):
            raise ValueError("Ambiguous field comparison")
        for j, (start, target) in enumerate(LABELS):
            truth = crossing(row[start], row[target])
            if truth != f["observed"][j]:
                raise ValueError("Fuel audit outcome changed")
            x, y = a["crossings"][j] != truth, b["crossings"][j] != truth
            key = {
                (False, False): "both_correct",
                (False, True): "introduced_by_observed_field",
                (True, False): "fixed_by_observed_field",
                (True, True): "both_wrong",
            }[x, y]
            totals["all"][key] += 1
            events[event][key] += 1
            if f["stable"][j]:
                totals["fuel_stable"][key] += 1
                if context["future_peer_counts"][0]:
                    totals["fuel_stable_with_matched_future_peer"][key] += 1
                    if x and y:
                        events[event]["stable_matched_both_wrong"] += 1
    return seal(
        {
            "scope": "PAIRED_DIAGNOSTIC_ONLY_SAME_DOWNSTREAM_CHECKPOINT",
            "forecast_sha256": actual["content_sha256"],
            "future_field_study_sha256": previous["content_sha256"],
            "fuel_audit_sha256": fuel["content_sha256"],
            "counts": dict(totals),
            "per_event": dict(events),
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    write_manifest(parser.parse_args().output, audit())
