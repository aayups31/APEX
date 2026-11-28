"""Count near-cutoff R041 radio observations in a pinned transcript projection."""

import argparse
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from prepare_compound_pit_exit import FOLDER

REVISION = "a0b99e1a325d92d63b574541a24902a660a352ea"
PROJECTED_SHA256 = "6e406def5431fc94a52ce5a278dd2084aa060776ed7fd37cf96f7436b8c1a5f6"
RACES = {
    "9850": "2025_Qatar_Grand_Prix",
    "9877": "2025_Mexico_City_Grand_Prix",
    "9912": "2025_Italian_Grand_Prix",
    "9928": "2025_Hungarian_Grand_Prix",
    "9998": "2025_Chinese_Grand_Prix",
    "F1_2023_R15": "2023_Singapore_Grand_Prix",
    "F1_2024_R16": "2024_Italian_Grand_Prix",
}
TOPIC = re.compile(r"\b(?:tyres?|tires?|grip|grain(?:ing|ed)|blister(?:ing|ed)?|overheat(?:ing|ed)?)\b", re.I)
SYMPTOM = re.compile(
    r"\b(?:grain(?:ing|ed)|blister(?:ing|ed)?|overheat(?:ing|ed)?|"
    r"(?:no|losing|lost|low)\s+grip|(?:tyres?|tires?)\s+(?:are\s+)?(?:gone|dead|overheating))\b",
    re.I,
)


def run(path):
    cohorts = read_json(FOLDER / "compound-v24-cohort.json")
    check_seal(cohorts)
    digest = file_sha256(path)
    if digest != PROJECTED_SHA256:
        raise ValueError("Radio transcript projection differs from the pinned input")
    clips = read_json(path)
    index = defaultdict(list)
    for clip in clips:
        if clip["race_id"] not in RACES.values():
            continue
        stamp = datetime.fromisoformat(clip["message_timestamp"])
        if stamp.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError("Radio join requires UTC timestamps")
        text = clip["transcription"] or ""
        key = clip["race_id"], clip["session_date"], clip["racing_number"]
        index[key].append((stamp.timestamp(), bool(TOPIC.search(text)), bool(SYMPTOM.search(text))))
    counts = {race: {"cases": 0, "any_clip": 0, "tyre_topic": 0, "explicit_symptom": 0} for race in RACES}
    for row in cohorts["cases"]:
        event = str(row["session"])
        if event not in RACES:
            continue
        cutoff = row["forecast_at_s"]
        day = datetime.fromtimestamp(cutoff, timezone.utc).date().isoformat()
        start = max(cutoff - 600, row["current_history"][0]["end_s"])
        matches = [
            (topic, symptom)
            for stamp, topic, symptom in index[RACES[event], day, str(row["driver"])]
            if start <= stamp <= cutoff - 30
        ]
        stats = counts[event]
        stats["cases"] += 1
        stats["any_clip"] += bool(matches)
        stats["tyre_topic"] += any(topic for topic, _ in matches)
        stats["explicit_symptom"] += any(symptom for _, symptom in matches)
    return seal(
        {
            "schema": "compound-radio-coverage-v1",
            "cohort_sha256": cohorts["content_sha256"],
            "source": "https://huggingface.co/datasets/MikCil/f1-team-radio",
            "revision": REVISION,
            "transcript_columns_sha256": digest,
            "source_clips": len(clips),
            "cases": {event: {"race": RACES[event], **stats} for event, stats in counts.items()},
            "totals": {key: sum(stats[key] for stats in counts.values()) for key in counts["9850"]},
            "predictive_value_tested": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcripts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.transcripts))
