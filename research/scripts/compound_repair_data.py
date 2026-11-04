"""Append opened v9 confirmation to development; never acquire fresh payloads."""
from __future__ import annotations

from pathlib import Path

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.research.evidence import check_seal, read_json, seal
from confirm_compound_multiseason import BASE


def opened_data() -> dict:
    base = read_json(BASE/"docs/verification/compound-v9-development-data.json")
    extra = read_json(BASE/"docs/verification/compound-v9-results.json")
    for item in (base, extra):
        check_seal(item)
    fields = tuple(base["cases"][0])
    sources = dict(base["sources"])
    if set(sources) & set(extra["sources"]):
        raise ValueError("Opened confirmation overlaps development event identities")
    for event in sources:
        if event.startswith("F1_"):
            _, year, round_text = event.split("_")
            assert_development_event(int(year), int(round_text[1:]), event_id=event)
    for metric in extra["metrics"]:
        sources[str(metric["session"])] = {"provider": "OPENF1", "archive_sha256": extra["sources"][str(metric["session"])],
            "blocks": metric["cases"], "unsupported_pairs": metric["unsupported_pairs"],
            "unavailable_reference_blocks": metric["unavailable_reference_blocks"]}
    cases = [*base["cases"], *[{k: r[k] for k in fields} for r in extra["cases"]]]
    return seal({"schema_version": "apex-compound-repair-opened-data-v10", "cases": cases,
                 "sources": {key: sources[key] for key in sorted(sources)},
                 "parents": [base["content_sha256"], extra["content_sha256"]],
                 "scope": "PREVIOUSLY_OPENED_DEVELOPMENT_ONLY_NOT_INDEPENDENT_CONFIRMATION"})


if __name__ == "__main__":
    import argparse

    from apexsim.provenance import write_manifest

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, opened_data())
