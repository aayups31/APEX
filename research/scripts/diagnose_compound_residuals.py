"""Decompose v21 forecast errors and source conflicts without refitting."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from statistics import mean

from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.compound_readiness import LABELS, crossing
from apexsim.research.evidence import check_seal, read_json, seal
from apexsim.research.tracing_telemetry import utc_seconds
from diagnose_compound_decision import ROOT
from diagnose_compound_line import FOLDER, score_forecasts


def source_conflicts(inputs: dict, cache: Path) -> list[dict]:
    """Compare rejected associations with the exact sealed export metadata."""
    conflicts = []
    for link in inputs["links"]:
        if "rejection" not in link:
            continue
        url = link["url"].rsplit("/", 1)[0] + "/laptimes.json"
        receipt = read_json(cache / f"{sha256(url.encode()).hexdigest()}.receipt.json")
        check_seal(receipt)
        body = cache / f"{receipt['body_sha256']}.body"
        if (receipt["url"], receipt["content_sha256"], file_sha256(body)) != (
            url,
            link["metadata_sha256"],
            receipt["body_sha256"],
        ):
            raise ValueError("Rejected association metadata changed")
        metadata = read_json(body)
        index = metadata["lap"].index(link["lap"])
        fields = {
            "driver": "dNum",
            "compound": "compound",
            "stint": "stint",
            "age": "life",
        }
        observed = {name: metadata[key][index] for name, key in fields.items()}
        observed["driver"] = int(observed["driver"])
        conflicts.append(
            {
                "case": link["case"],
                "key": link["key"],
                "group": link["group"],
                "reason": link["rejection"],
                "identity_differences": {
                    k: [link[k], v] for k, v in observed.items() if link[k] != v
                },
                "export_minus_native_start_s": utc_seconds(metadata["lSD"][index])
                - link["start_s"],
                "export_minus_native_duration_s": float(metadata["time"][index])
                - link["duration_s"],
            }
        )
    return conflicts


def diagnose(cache: Path) -> dict:
    data = read_json(FOLDER / "compound-v11-development-data.json")
    inputs = read_json(FOLDER / "compound-v21-processed-data.json")
    saved = read_json(FOLDER / "compound-v21-development.json")
    for doc in (data, inputs, saved):
        check_seal(doc)
    if not (
        data["content_sha256"] == inputs["dataset_sha256"] == saved["dataset_sha256"]
        and inputs["content_sha256"] == saved["processed_sha256"]
    ):
        raise ValueError("Residual inputs use different cohorts")
    rows = data["cases"]
    predictions = [
        {p["index"]: p for p in saved[k]["predictions"]} for k in ("control", "result")
    ]
    if any(set(p) != set(range(len(rows))) for p in predictions):
        raise ValueError("Incomplete residual forecast inventory")
    support = [
        all(lap["coverage"] >= 0.9 for g in groups for lap in g)
        for groups in inputs["lap_summaries"]
    ]
    events = defaultdict(list)
    for i, row in enumerate(rows):
        event = str(row["session"])
        events[event].append(
            {
                "index": i,
                "full_support": support[i],
                "labels": [
                    {
                        "observed": crossing(row[start], row[target]),
                        "control_called": predictions[0][i]["crossings"][j],
                        "processed_called": predictions[1][i]["crossings"][j],
                        "control_residual_s": predictions[0][i]["contrasts_s"][j]
                        - row[target],
                        "processed_residual_s": predictions[1][i]["contrasts_s"][j]
                        - row[target],
                    }
                    for j, (start, target) in enumerate(LABELS)
                ],
            }
        )
    groups = {}
    for flag, name in ((True, "full"), (False, "incomplete")):
        cases = [
            case
            for items in events.values()
            for case in items
            if case["full_support"] == flag
        ]
        groups[name] = {
            "cases": len(cases),
            **{
                f"{recipe}_mae_s": mean(
                    abs(label[f"{recipe}_residual_s"])
                    for case in cases
                    for label in case["labels"]
                )
                for recipe in ("control", "processed")
            },
        }
    # Give missing inputs an optimistic upper bound using actual targets only in this diagnostic.
    oracle = {
        i: (predictions[1][i]["laps_s"], predictions[1][i]["bounded_laps"])
        if full
        else (rows[i]["current_target_s"], 0)
        for i, full in enumerate(support)
    }
    diagnostic = score_forecasts(rows, data["sources"], oracle)
    conflicts = source_conflicts(inputs, cache)
    return seal(
        {
            "schema": "compound-residual-audit-v22",
            "dataset_sha256": data["content_sha256"],
            "processed_sha256": inputs["content_sha256"],
            "model_sha256": saved["content_sha256"],
            "support_groups": groups,
            "by_event": dict(events),
            "source_conflicts": conflicts,
            "conflict_fields": dict(
                Counter(k for item in conflicts for k in item["identity_differences"])
            ),
            "missing_support_oracle_failed_events": diagnostic["failed_events"],
            "oracle_scope": "HINDSIGHT_BOUND_ON_MISSING_INPUT_REPAIR_ONLY",
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache", type=Path, default=ROOT / ".cache/r041-v20-snapshots"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, diagnose(args.cache))
