"""Independent event-held-out field span baseline for R049."""

import argparse
from bisect import bisect_right
from pathlib import Path
from statistics import mean, median

import pandas as pd
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_race_model_sources import neutralization_windows
from confirm_compound_crossover import timestamp
from prepare_compound_pit_exit import BASE, FOLDER, MAPPING, tables_from_archive


def activity(rows):
    changes = []
    for row in rows:
        text = (row.get("message") or "").upper()
        flag = row.get("flag")
        if row.get("category") == "SafetyCar" and "DEPLOYED" in text:
            changes.append((timestamp(row["date"]), "6" if "VIRTUAL" in text else "4"))
        elif row.get("scope") == "Track" and "PIT EXIT" not in text:
            code = {"RED": "5", "GREEN": "1", "CLEAR": "1", "CHEQUERED": "0"}.get(flag)
            if code:
                changes.append((timestamp(row["date"]), code))
    return sorted(changes)


def match(tables):
    changes = activity(tables["race_control"])
    times = [t for t, _ in changes]
    pit_markers = {
        (row["driver_number"], row["lap_number"])
        for row in tables["laps"]
        if row["is_pit_out_lap"] is True
    }
    data = []
    for row in tables["laps"]:
        duration = row["lap_duration"]
        if not row["date_start"] or duration is None or duration <= 0:
            continue
        start = timestamp(row["date_start"])
        end = start + duration
        driver, lap = row["driver_number"], row["lap_number"]
        a, b = bisect_right(times, start), bisect_right(times, end)
        good = (a == 0 or changes[a - 1][1] == "1") and all(
            code == "1" for _, code in changes[a:b]
        )
        data.append(
            {
                "DriverNumber": driver,
                "LapNumber": lap,
                "LapStartTime": pd.to_timedelta(start, unit="s"),
                "Time": pd.to_timedelta(end, unit="s"),
                "TrackStatus": "1" if good else "other",
                "PitInTime": start if (driver, lap + 1) in pit_markers else None,
                "PitOutTime": start if (driver, lap) in pit_markers else None,
            }
        )
    status = pd.DataFrame(changes, columns=["Time", "Status"])
    status["Time"] = pd.to_timedelta(status.Time, unit="s")
    return neutralization_windows(pd.DataFrame(data), status)


def score(windows):
    rows = []
    for event, episodes in sorted(windows.items()):
        for episode in episodes:
            if not episode["supported"] or episode["field_span_s"][0] <= 0:
                continue
            mode = episode["mode"]
            training = {}
            for other, others in windows.items():
                matches = [
                    x["field_span_s"]
                    for x in others
                    if other != event
                    and x["supported"]
                    and x["mode"] == mode
                    and x["field_span_s"][0] > 0
                ]
                if matches:
                    training[other] = [
                        median(span[i] / span[0] for span in matches) for i in (1, 2)
                    ]
            if len(training) < 2:
                continue
            before, during, after = episode["field_span_s"]
            predictions = [
                before * median(values[i] for values in training.values())
                for i in (0, 1)
            ]
            rows.append(
                {
                    "event": event,
                    "mode": mode,
                    "train_events": sorted(training),
                    "before_s": before,
                    "actual_s": [during, after],
                    "predicted_s": predictions,
                }
            )
    metrics = {}
    for mode in ("4", "6"):
        subset = [r for r in rows if r["mode"] == mode]
        metrics[mode] = {
            "scored_episodes": len(subset),
            "candidate_mae_s": [
                mean(abs(r["predicted_s"][i] - r["actual_s"][i]) for r in subset)
                for i in (0, 1)
            ]
            if subset
            else None,
            "persistence_mae_s": [
                mean(abs(r["before_s"] - r["actual_s"][i]) for r in subset)
                for i in (0, 1)
            ]
            if subset
            else None,
        }
    return {"predictions": rows, "metrics": metrics}


def run(root):
    prior = read_json(FOLDER / "race-model-source-audit.json")
    cohort = read_json(FOLDER / "compound-v24-cohort.json")
    for data in (prior, cohort):
        check_seal(data)
    windows = {
        e: r["race_control"]["matched_field_windows"] for e, r in prior["races"].items()
    }
    sources = {e: r["source_sha256"] for e, r in prior["races"].items()}
    for event, source in cohort["sources"].items():
        if source["provider"] != "OPENF1":
            continue
        session = int(event)
        number, meeting, folder = MAPPING[session]
        tables, digest = tables_from_archive(root / folder, session, (number, meeting))
        if digest != source["archive_sha256"]:
            raise ValueError("Race control source differs from opened cohort")
        windows[event] = match(tables)
        sources[event] = digest
    return seal(
        {
            "schema": "apex-r049-neutralization-span-v1",
            "sources": sources,
            "windows": windows,
            **score(windows),
            "qualified_per_car_calibration": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=BASE / ".cache")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.native_root))
