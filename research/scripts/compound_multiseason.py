"""R041 source-bound multi-season development cases; no fresh test acquisition."""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations, groupby
from pathlib import Path

import numpy as np
import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.data.jolpica import verify_jolpica_archive
from apexsim.data.tyre_dataset import FuelPrior, segment_native_laps
from apexsim.provenance import file_sha256
from apexsim.research.evidence import read_json

ARCHIVES = [Path(f".cache/fastf1-2024-r{r}-race-20261011") for r in (1, 3, 6, 16, 18)] + [
    Path(f".cache/r026-fastf1-2023-r{r}-race-20261013") for r in (1, 3, 14, 15)]


def fastf1_cases(root: Path) -> tuple[list[dict], dict]:
    """Recover genuinely known reference times from sealed native lap tables.

    FastF1 timestamps are parsed source values. Corrected pace retains the R021
    fuel prior. Rain/unknown weather, non-green, inaccurate and pit laps are
    excluded; gaps remain gaps after merging segments of the same actual stint.
    """
    metadata = read_json(root/"manifest.json")
    query = metadata["query"]
    year, round_number = query["year"], query["round_number"]
    assert_development_event(year, round_number)
    if query["session"] != "R":
        raise ValueError("Multi-season compound study requires race sources")
    manifest = verify_fastf1_archive(root)
    calendar = Path(f".cache/jolpica-{year}-20260916")
    calendar_manifest = verify_jolpica_archive(calendar)
    events = read_json(calendar/"events.json")["events"]
    event, = [e for e in events if e["season"] == year and e["round_number"] == round_number]
    frame = pd.read_parquet(root/"tables/laps.parquet")
    weather = pd.read_parquet(root/"tables/weather_data.parquet")
    segments, _ = segment_native_laps(frame, {**event, "track_id": event["circuit_id"]}, FuelPrior())
    samples = sorted((r["Time"].total_seconds(), r["Rainfall"]) for r in weather.to_dict("records")
                     if pd.notna(r["Time"]))
    stints, compounds = defaultdict(dict), {}
    rejected_weather = 0
    for segment in segments:
        driver, stint, compound = segment["driver"], segment["stint"], segment["compound"]
        key = (driver, stint)
        if key in compounds and compounds[key] != compound:
            raise ValueError("Conflicting native compound within a stint")
        compounds[key] = compound
        for row in segment["rows"]:
            native = frame.iloc[row["native_row"]]
            if pd.isna(native["LapStartDate"]) or pd.isna(native["LapStartTime"]):
                continue
            start = native["LapStartTime"].total_seconds()
            end = start+row["observed_s"]
            previous = [wet for time, wet in samples if time <= start]
            if (not previous or previous[-1] not in (False, np.False_)
                    or any(wet not in (False, np.False_) for time, wet in samples if start < time < end)):
                rejected_weather += 1
                continue
            # Native FastF1 UTC dates are sometimes timezone-naive; interpretation
            # as UTC is a source convention, never the workstation timezone.
            date = pd.Timestamp(native["LapStartDate"])
            date = date.tz_localize("UTC") if date.tzinfo is None else date.tz_convert("UTC")
            value = {"pace_s": row["corrected_s"], "end_s": date.timestamp()+row["observed_s"], "lap": row["lap"]}
            age = row["tyre_age"]
            if age in stints[key] and stints[key][age] != value:
                raise ValueError("Conflicting native tyre age within a stint")
            stints[key][age] = value
    cases, unsupported = [], 0
    for driver in sorted({d for d, _ in stints}):
        indices = sorted(i for d, i in stints if d == driver)
        for i, j in combinations(indices, 2):
            a, b = compounds[(driver, i)], compounds[(driver, j)]
            if a == b:
                continue
            x, y = stints[(driver, i)], stints[(driver, j)]
            count = 0
            for _, group in groupby(enumerate(sorted(x.keys() & y.keys())), lambda row: row[1]-row[0]):
                ages = [age for _, age in group]
                for offset in range(0, len(ages)-11, 12):
                    block = ages[offset:offset+12]
                    first, last = block[:3], block[-3:]
                    reference_end = max(x[k]["end_s"] for k in first+last)
                    forecast_at = max(y[k]["end_s"] for k in first)
                    if reference_end > forecast_at:
                        raise ValueError("Native reference occurs after forecast time")
                    xp, yp, xt, yt = ([v[k]["pace_s"] for k in window] for v, window in
                                      ((x, first), (y, first), (x, last), (y, last)))
                    cases.append({"session": event["event_id"], "driver": int(driver), "stints": [i, j],
                                  "compounds": [a, b], "ages": block, "reference_target_s": xt,
                                  "current_prefix_s": yp, "current_target_s": yt,
                                  "reference_end_s": reference_end, "forecast_at_s": forecast_at,
                                  "prefix_s": float(np.median(xp)-np.median(yp)),
                                  "actual_s": float(np.median(xt)-np.median(yt)),
                                  "pairwise_prefix_s": float(np.median(np.asarray(xp)-yp)),
                                  "pairwise_actual_s": float(np.median(np.asarray(xt)-yt))})
                    count += 1
            unsupported += count == 0
    if verify_fastf1_archive(root)["content_sha256"] != manifest["content_sha256"]:
        raise ValueError("Native multi-season archive changed during read")
    return cases, {"event_id": event["event_id"], "archive_sha256": manifest["content_sha256"],
                   "calendar_sha256": calendar_manifest["content_sha256"],
                   "lap_table_sha256": file_sha256(root/"tables/laps.parquet"), "blocks": len(cases),
                   "unsupported_pairs": unsupported, "weather_rejections": rejected_weather,
                   "truth": "FASTF1_PARSED_SOURCE; FUEL_CORRECTED_PACE_PROXY"}
