"""Test contemporaneous field pace and separately score future-field information."""

import argparse
from bisect import bisect_right
from collections import defaultdict
from math import log1p
from pathlib import Path
from statistics import median

import numpy as np
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_driving import base_vector
from audit_compound_race_context import check_result
from audit_compound_repair import compare
from audit_compound_same_phase_support import clean_field
from confirm_compound_multiseason import canonical_file_sha
from diagnose_compound_line import evaluate
from diagnose_compound_pit_exit import replay_checkpoint
from prepare_compound_pit_exit import BASE, FOLDER


def index_field(field):
    """Index clean laps so a missing age cannot silently join two runs."""
    laps = defaultdict(list)
    stints = {}
    for stint in field:
        driver, number = stint["driver"], stint["stint"]
        if (driver, number) in stints:
            raise ValueError("Duplicate field stint")
        stints[driver, number] = stint
        previous = None
        for age, end in sorted(stint["ends"].items()):
            if int(age) != age:
                raise ValueError("Nonintegral native tyre age")
            if previous is not None and end <= previous:
                raise ValueError("Nonmonotone field lap clock")
            laps[driver].append((end, number, int(age)))
            previous = end
    clocks = {}
    for driver, entries in laps.items():
        entries.sort()
        clocks[driver] = [item[0] for item in entries]
        if len(set(clocks[driver])) != len(entries):
            raise ValueError("Ambiguous driver lap clock")
    return laps, clocks, stints


def snapshot(index, subject, cutoff):
    laps, clocks, stints = index
    peers = {}
    for driver, times in clocks.items():
        if driver == subject:
            continue
        pos = bisect_right(times, cutoff) - 1
        if pos < 0 or cutoff - times[pos] > 150:
            continue
        end, number, age = laps[driver][pos]
        stint = stints[driver, number]
        if any(a not in stint["ends"] for a in range(age - 5, age + 1)):
            continue
        values = [stint["values"][a] for a in range(age - 5, age + 1)]
        level = median(values[-3:])
        peers[driver] = {
            "stint": number,
            "age": age,
            "end": end,
            "compound": stint["compound"],
            "level": level,
            "change": level - median(values[:3]),
        }
    return peers


def summarize(pairs, compound):
    result = []
    for values in ([v for _, v in pairs], [v for c, v in pairs if c == compound]):
        center = median(values) if values else 0.0
        mad = median(abs(v - center) for v in values) if values else 0.0
        result.extend([center, mad, log1p(len(values))])
    return result


def causal_context(index, row):
    subject, cutoff = row["driver"], row["forecast_at_s"]
    current, reference = row["current_history"], row["reference_history"]
    a, b = row["compounds"]
    clocks = (
        (current[-1]["end_s"], b),
        (reference[2]["end_s"], a),
        (reference[-1]["end_s"], a),
    )
    if clocks[0][0] != cutoff or any(end > cutoff for end, _ in clocks):
        raise ValueError("Invalid field context forecast clock")
    features, counts = [], []
    for end, compound in clocks:
        peers = snapshot(index, subject, end)
        pairs = [(p["compound"], p["change"]) for p in peers.values()]
        features.extend(summarize(pairs, compound))
        counts.append([len(pairs), sum(c == compound for c, _ in pairs)])
    return features, counts


def future_field_diagnostic(index, row):
    """Privileged peer information used exclusively for a diagnostic fit."""
    subject, cutoff = row["driver"], row["forecast_at_s"]
    stints = index[2]
    future = stints[subject, row["stints"][1]]["ends"][row["ages"][-1]]
    if future <= cutoff:
        raise ValueError("Invalid diagnostic horizon")
    prior = snapshot(index, subject, cutoff)
    later = snapshot(index, subject, future)
    pairs = []
    for driver in sorted(prior.keys() & later.keys()):
        p, q = prior[driver], later[driver]
        if p["stint"] != q["stint"]:
            continue
        ends = stints[driver, p["stint"]]["ends"]
        if ends[q["age"] - 2] <= cutoff or any(
            a not in ends for a in range(p["age"], q["age"] + 1)
        ):
            continue
        pairs.append((p["compound"], q["level"] - p["level"]))
    compound = row["compounds"][1]
    return summarize(pairs, compound), [
        len(pairs),
        sum(c == compound for c, _ in pairs),
    ]


def score(data, matrix):
    rows = data["cases"]
    result = evaluate(rows, data["sources"], np.asarray(matrix))
    for p in result["predictions"]:
        i = p["index"]
        laps, hits = replay_checkpoint(
            result["models"][p["event"]], matrix[i], rows[i]["current_prefix_s"]
        )
        compare(laps, p["laps_s"], "field checkpoint")
        compare(hits, p["bounded_laps"], "field bounds")
    return result


def run(root):
    data, control, practice, nominations = [
        read_json(FOLDER / f"compound-{name}.json")
        for name in (
            "v24-cohort",
            "v24-development",
            "v17-practice-trends",
            "v21-nominations",
        )
    ]
    for doc in (data, control, practice, nominations):
        check_seal(doc)
    if (
        control["dataset_sha256"],
        control["practice_sha256"],
        control["nominations_sha256"],
    ) != (
        data["content_sha256"],
        practice["content_sha256"],
        nominations["content_sha256"],
    ):
        raise ValueError("Field evolution cohort or control sources changed")
    allocation = {
        event: (source["issued"], codes)
        for source in nominations["sources"]
        for event, codes in source["events"].items()
    }
    rows = data["cases"]
    contexts = [None] * len(rows)
    for event, source in data["sources"].items():
        index = index_field(clean_field(root, event, source))
        for i, row in enumerate(rows):
            if str(row["session"]) == event:
                features, counts = causal_context(index, row)
                diagnostic, matched = future_field_diagnostic(index, row)
                contexts[i] = {
                    "causal": features,
                    "peer_counts": counts,
                    "future_diagnostic": diagnostic,
                    "future_peer_counts": matched,
                }
    base = [base_vector(r, allocation, practice["events"]) for r in rows]
    matrices = [x + c["causal"] for x, c in zip(base, contexts, strict=True)]
    causal = score(data, matrices)
    diagnostic = score(
        data,
        [x + c["future_diagnostic"] for x, c in zip(matrices, contexts, strict=True)],
    )
    flags = {
        "development_qualified": causal["qualified"],
        "new_holdout_acquisition_allowed": causal["qualified"],
    }
    return seal(
        {
            "schema": "compound-field-evolution-v28",
            "dataset_sha256": data["content_sha256"],
            "control_sha256": control["content_sha256"],
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "protocol_sha256_lf": canonical_file_sha(
                BASE / "research/protocols/COMPOUND_FIELD_EVOLUTION_V28.md"
            ),
            "contexts": contexts,
            "result": causal,
            "audit": check_result(data, seal({"result": causal, **flags})),
            "future_field_diagnostic_only": diagnostic,
            **flags,
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
