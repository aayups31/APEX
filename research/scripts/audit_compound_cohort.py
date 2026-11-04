"""Independent complete OpenF1/FastF1 denominator audit of opened R041 events."""
from __future__ import annotations

import argparse
import math
from bisect import bisect_right
from collections import Counter, defaultdict
from itertools import combinations, groupby
from numbers import Real
from pathlib import Path
from statistics import median

import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_bounded_confirmation import EVENTS as V9
from audit_compound_context import OPENED, utc


def enumerate_cases(tables: dict, session: int) -> tuple[list[dict], dict]:
    """Enumerate every eligible lap/pair/block without candidate cohort helpers."""
    controls = []
    for raw in tables["race_control"]:
        message = (raw.get("message") or "").upper()
        deployment = raw.get("category") == "SafetyCar" and "DEPLOYED" in message
        if raw.get("scope") != "Track" and not deployment:
            continue
        flag = raw.get("flag")
        if flag in ("YELLOW", "DOUBLE YELLOW", "RED", "GREEN", "CLEAR"):
            controls.append((utc(raw["date"]), flag not in ("GREEN", "CLEAR")))
        if "DEPLOYED" in message and ("SAFETY CAR" in message or "VSC" in message):
            controls.append((utc(raw["date"]), True))
    controls.sort()
    control_times = [t for t, _ in controls]
    weather = sorted((utc(r["date"]), r.get("rainfall")) for r in tables["weather"])
    weather_times = [t for t, _ in weather]
    laps = {}
    for r in tables["laps"]:
        key = r["driver_number"], r["lap_number"]
        if key in laps:
            raise ValueError("Independent cohort duplicate driver/lap")
        laps[key] = r
    stints, exclusions, seen = defaultdict(list), Counter(), set()
    for meta in tables["stints"]:
        identity = meta["driver_number"], meta["stint_number"]
        if identity in seen:
            raise ValueError("Independent cohort duplicate stint identity")
        seen.add(identity)
        if (meta["compound"] not in ("SOFT", "MEDIUM", "HARD") or meta.get("tyre_age_at_start") is None
                or type(meta.get("lap_start")) is not int or type(meta.get("lap_end")) is not int):
            exclusions["unsupported_stint_metadata"] += 1
            continue
        values = {}
        for (driver, lap), raw in laps.items():
            if driver != identity[0] or not meta["lap_start"] <= lap <= meta["lap_end"]:
                continue
            reason = None
            duration = raw.get("lap_duration")
            if lap in (meta["lap_start"], meta["lap_end"]):
                reason = "stint_boundary"
            elif raw.get("is_pit_out_lap") is not False:
                reason = "pit_out_or_unknown"
            elif duration is None or not isinstance(duration, (int, float)) or not 0 < duration < float("inf"):
                reason = "invalid_duration"
            elif not raw.get("date_start"):
                reason = "missing_start_clock"
            if reason:
                exclusions[reason] += 1
                continue
            start = utc(raw["date_start"])
            end = start+duration
            wi, ci = bisect_right(weather_times, start)-1, bisect_right(control_times, start)-1
            if wi < 0 or weather[wi][1] != 0:
                reason = "wet_or_unknown_at_start"
            elif any(wet != 0 for t, wet in weather if start < t < end):
                reason = "wet_during_lap"
            elif ci >= 0 and controls[ci][1]:
                reason = "global_flag_at_start"
            elif any(bad for t, bad in controls if start < t < end):
                reason = "global_flag_during_lap"
            if reason:
                exclusions[reason] += 1
                continue
            age = meta["tyre_age_at_start"]+lap-meta["lap_start"]+1
            if age in values:
                raise ValueError("Independent cohort duplicate retained tyre age")
            values[age] = (duration-max(0., 105.-1.4*(lap-1))*.03, end)
            exclusions["retained_lap"] += 1
        stints[identity[0]].append((identity[1], meta["compound"], values))
    cases, report = enumerate_pairs(stints, session)
    return cases, {**report, "lap_exclusions": dict(exclusions)}


def enumerate_pairs(stints: dict, session: int | str) -> tuple[list[dict], dict]:
    """Independent deterministic matched-age block enumeration for both providers."""
    cases, pairs, unavailable = [], [], 0
    for driver, entries in sorted(stints.items()):
        for (i, a, x), (j, b, y) in combinations(sorted(entries), 2):
            if a == b:
                continue
            overlap = sorted(set(x) & set(y))
            runs = [[age for _, age in group] for _, group in groupby(enumerate(overlap), lambda v: v[1]-v[0])]
            count = 0
            blocked = 0
            for run in runs:
                for offset in range(0, len(run)-11, 12):
                    ages = run[offset:offset+12]
                    first, last = ages[:3], ages[-3:]
                    cutoff = max(y[k][1] for k in first)
                    reference = max(x[k][1] for k in first+last)
                    if reference > cutoff:
                        unavailable += 1
                        blocked += 1
                        continue
                    xp, yp, xt, yt = ([v[k][0] for k in window] for v, window in
                                      ((x, first), (y, first), (x, last), (y, last)))
                    cases.append({"session": session, "driver": driver, "stints": [i, j], "compounds": [a, b], "ages": ages,
                        "reference_target_s": xt, "current_prefix_s": yp, "current_target_s": yt,
                        "forecast_at_s": cutoff, "reference_end_s": reference, "prefix_s": median(xp)-median(yp),
                        "actual_s": median(xt)-median(yt), "pairwise_prefix_s": median(u-v for u, v in zip(xp, yp, strict=True)),
                        "pairwise_actual_s": median(u-v for u, v in zip(xt, yt, strict=True))})
                    count += 1
            reason = ("SUPPORTED" if count else "REFERENCE_UNAVAILABLE" if blocked else
                      "NO_COMMON_RETAINED_AGES" if not overlap else "COMMON_AGE_RUN_SHORTER_THAN_TWELVE")
            pairs.append({"driver": driver, "stints": [i, j], "compounds": [a, b], "overlap_ages": len(overlap),
                          "maximum_common_run": max(map(len, runs), default=0), "cases": count, "disposition": reason})
    return cases, {"cases": len(cases), "unsupported_pairs": sum(not p["cases"] for p in pairs),
                   "unavailable_reference_blocks": unavailable, "pairs": pairs}


def enumerate_fastf1(root: Path, session: str) -> tuple[list[dict], dict]:
    """Independently rebuild strict native quality segments before dry filtering."""
    metadata = read_json(root/"manifest.json")
    query = metadata["query"]
    assert_development_event(query["year"], query["round_number"], event_id=session)
    if query["session"] != "R":
        raise ValueError("Independent cohort requires native race data")
    verify_fastf1_archive(root)
    frame = pd.read_parquet(root/"tables/laps.parquet")
    weather = pd.read_parquet(root/"tables/weather_data.parquet").to_dict("records")
    samples = sorted((r["Time"].total_seconds(), r["Rainfall"]) for r in weather if pd.notna(r["Time"]))
    accepted, exclusions = [], Counter()
    for row in frame.to_dict("records"):
        driver = pd.to_numeric(row["DriverNumber"], errors="coerce")
        identities = (driver, row["LapNumber"], row["Stint"])
        identity_valid = all(isinstance(v, Real) and not isinstance(v, bool)
                             and math.isfinite(v) and v > 0 and v % 1 == 0 for v in identities)
        duration = row["LapTime"].total_seconds() if pd.notna(row["LapTime"]) else float("nan")
        age = row["TyreLife"]
        quality = (identity_valid and math.isfinite(duration) and duration > 0
                   and row["IsAccurate"] is True and row["Deleted"] is False and row["TrackStatus"] == "1"
                   and pd.isna(row["PitInTime"]) and pd.isna(row["PitOutTime"])
                   and row["Compound"] in ("SOFT", "MEDIUM", "HARD")
                   and isinstance(age, (int, float)) and math.isfinite(age) and age >= 0)
        if quality:
            accepted.append((str(int(driver)), int(row["LapNumber"]), int(row["Stint"]), row))
        else:
            exclusions["native_quality_mask"] += 1
    segments, active = [], []
    for item in sorted(accepted, key=lambda v: (v[0], v[1])):
        if active and (item[0] != active[-1][0] or item[1] != active[-1][1]+1 or item[2] != active[-1][2]
                       or item[3]["Compound"] != active[-1][3]["Compound"]):
            segments.append(active)
            active = []
        active.append(item)
    if active:
        segments.append(active)
    groups, compounds = defaultdict(dict), {}
    for segment in segments:
        if len(segment) < 6:
            exclusions["segment_shorter_than_six"] += len(segment)
            continue
        for driver, lap, stint, row in segment:
            key = driver, stint
            compounds[key] = row["Compound"]
            if pd.isna(row["LapStartDate"]) or pd.isna(row["LapStartTime"]):
                exclusions["missing_clock"] += 1
                continue
            duration = row["LapTime"].total_seconds()
            start = row["LapStartTime"].total_seconds()
            previous = [wet for t, wet in samples if t <= start]
            if (not previous or previous[-1] is not False
                    or any(wet is not False for t, wet in samples if start < t < start+duration)):
                exclusions["wet_or_unknown_weather"] += 1
                continue
            mass = 105.-1.4*(lap-1)
            if mass < 0:
                raise ValueError("Independent cohort unsupported fuel prior")
            groups[key][row["TyreLife"]] = (duration-mass*.03, utc(row["LapStartDate"])+duration)
            exclusions["retained_lap"] += 1
    stints = defaultdict(list)
    for (driver, stint), values in groups.items():
        stints[int(driver)].append((stint, compounds[(driver, stint)], values))
    cases, report = enumerate_pairs(stints, session)
    return cases, {**report, "lap_exclusions": dict(exclusions)}


def audit(data: dict, native_root: Path) -> dict:
    check_seal(data)
    events, audited = [], 0
    mapping = {**OPENED, **{e: (*identity, "r041-v9-confirmation-20261104") for e, identity in V9.items()}}
    for event, source in data["sources"].items():
        if source["provider"] == "FASTF1":
            _, year, round_text = event.split("_")
            year, round_number = int(year), int(round_text[1:])
            assert_development_event(year, round_number)
            name = (f"fastf1-2024-r{round_number}-race-20261011" if year == 2024 else
                    f"r026-fastf1-2023-r{round_number}-race-20261013")
            root = native_root/name
            query = read_json(root/"manifest.json")["query"]
            assert_development_event(query["year"], query["round_number"], event_id=event)
            if verify_fastf1_archive(root)["content_sha256"] != source["archive_sha256"]:
                raise ValueError("Independent cohort native archive mismatch")
            cases, report = enumerate_fastf1(root, event)
            compare_published(data, event, source, cases, report)
            audited += len(cases)
            events.append({"session": event, **report})
            continue
        session = int(event)
        round_number, meeting, folder = mapping[session]
        assert_development_event(2025, round_number)
        root = native_root/folder
        manifest = read_json(root/"manifest.json")
        check_seal(manifest)
        if manifest["content_sha256"] != source["archive_sha256"]:
            raise ValueError("Independent cohort source manifest mismatch")
        tables = {}
        for endpoint in ("sessions", "laps", "stints", "race_control", "weather"):
            name = f"{session}-{endpoint}.json"
            if file_sha256(root/name) != manifest["files"][name]:
                raise ValueError("Independent cohort raw file mismatch")
            tables[endpoint] = read_json(root/name)
            if not tables[endpoint] or any(r.get("session_key") != session for r in tables[endpoint]):
                raise ValueError("Independent cohort native session mismatch")
        identity, = tables["sessions"]
        if (identity["year"], identity["meeting_key"], identity["session_name"]) != (2025, meeting, "Race"):
            raise ValueError("Independent cohort race identity mismatch")
        cases, report = enumerate_cases(tables, session)
        compare_published(data, event, source, cases, report)
        audited += len(cases)
        events.append({"session": session, **report})
    return seal({"schema_version": "apex-compound-full-openf1-cohort-audit-v10", "dataset_sha256": data["content_sha256"],
                 "audit_source_sha256": file_sha256(Path(__file__)), "events": events, "cases_audited": audited,
                 "sources_audited": len(events), "audit_passed": True,
                 "scope": "FULL_OPENF1_AND_FASTF1_ELIGIBILITY_DENOMINATORS"})


def compare_published(data: dict, event: str, source: dict, cases: list[dict], report: dict) -> None:
    def key(row: dict) -> tuple:
        return str(row["session"]), row["driver"], tuple(row["stints"]), tuple(row["ages"])
    expected = [r for r in data["cases"] if str(r["session"]) == event]
    if len(expected) != len({key(r) for r in expected}) or {key(r) for r in expected} != {key(r) for r in cases}:
        raise ValueError("Independent cohort missing/extra/duplicate published case")
    indexed = {key(r): r for r in expected}
    for case in cases:
        if any(indexed[key(case)][k] != v for k, v in case.items()):
            raise ValueError("Independent cohort native case reconstruction mismatch")
    for field in ("unsupported_pairs", "unavailable_reference_blocks"):
        if field in source and source[field] != report[field]:
            raise ValueError(f"Independent cohort denominator mismatch: {field}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("dataset", "native-root", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, audit(read_json(args.dataset), args.native_root))
