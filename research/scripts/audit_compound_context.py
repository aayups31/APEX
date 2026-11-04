"""Independently check R041 context timestamps and values against native sources.

Audits every published context association, not the complete excluded-lap or
eligible-field-window denominator. Never imports candidate context builders.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from math import isclose, isfinite
from pathlib import Path
from statistics import median

import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal

OPENED = {
    9912: (16, 1268, "r041-openf1-confirmation"), 9839: (24, 1276, "r041-openf1-confirmation"),
    10014: (4, 1257, "r041-traffic-holdout"), 9971: (9, 1262, "r041-traffic-holdout"),
    9963: (10, 1263, "r041-reference-holdout"), 9955: (11, 1264, "r041-reference-holdout"),
    9998: (2, 1255, "r041-conditioned-holdout"), 9928: (14, 1266, "r041-conditioned-holdout"),
    9920: (15, 1267, "r041-event-holdout"), 9896: (18, 1270, "r041-event-holdout"),
    9888: (19, 1271, "r041-multiseason-holdout-final"), 9877: (20, 1272, "r041-multiseason-holdout-final"),
    10033: (6, 1259, "r041-v8-confirmation-panel"), 9987: (7, 1260, "r041-v8-confirmation-panel"),
    9850: (23, 1275, "r041-v8-confirmation-panel"),
}


def close(actual: float | None, expected: float | None, field: str) -> None:
    if actual is None or expected is None:
        if actual is not expected:
            raise ValueError(f"Independent context audit mismatch: {field}")
    elif not isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-6):
        raise ValueError(f"Independent context audit mismatch: {field}")


def utc(value: object) -> float:
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc).timestamp() if parsed.tzinfo is None else parsed.timestamp()
    date = pd.Timestamp(value)
    return (date.tz_localize("UTC") if date.tzinfo is None else date.tz_convert("UTC")).timestamp()


def audit_case(case: dict, tables: dict, provider: str) -> int:
    """Check native weather and all contributing field laps, returning count."""
    if provider == "OPENF1":
        laps = {(int(r["driver_number"]), r["lap_number"]): r for r in tables["laps"]}
        stints = {(int(r["driver_number"]), r["stint_number"]): r for r in tables["stints"]}
        def lap(driver: int, stint: int, age: float) -> tuple[float, float, float | None, str]:
            meta = stints[(driver, stint)]
            number = age-meta["tyre_age_at_start"]+meta["lap_start"]-1
            raw = laps[(driver, number)]
            duration = raw["lap_duration"]
            pace = duration-max(0., 105.-1.4*(number-1))*.03
            return pace, utc(raw["date_start"])+duration, None, meta["compound"]
        samples = [(utc(r["date"]), r.get("track_temperature")) for r in tables["weather"]]
    elif provider == "FASTF1":
        lookup = {}
        for r in tables["laps"]:
            if any(pd.isna(r[k]) for k in ("DriverNumber", "Stint", "TyreLife")):
                continue
            key = (int(r["DriverNumber"]), int(r["Stint"]), float(r["TyreLife"]))
            if key in lookup:
                raise ValueError("Independent context audit duplicate native age key")
            lookup[key] = r
        def lap(driver: int, stint: int, age: float) -> tuple[float, float, float, str]:
            raw = lookup[(driver, stint, age)]
            duration = raw["LapTime"].total_seconds()
            mass = 105.-1.4*(raw["LapNumber"]-1)
            if mass < 0:
                raise ValueError("Independent context audit unsupported fuel prior")
            return duration-mass*.03, utc(raw["LapStartDate"])+duration, raw["LapStartTime"].total_seconds()+duration, raw["Compound"]
        _, end_utc, end_relative, _ = lap(case["driver"], case["stints"][1], case["ages"][2])
        samples = [(end_utc+r["Time"].total_seconds()-end_relative,
                    float(r["TrackTemp"]) if pd.notna(r["TrackTemp"]) else None)
                   for r in tables["weather"] if pd.notna(r["Time"])]
    else:
        raise ValueError("Independent context audit unknown provider")
    cutoff = case["forecast_at_s"]
    close(cutoff, max(lap(case["driver"], case["stints"][1], a)[1] for a in case["ages"][:3]), "forecast clock")
    known = sorted((t, v) for t, v in samples if t <= cutoff)
    time, temperature, change = None, None, None
    if known and cutoff-known[-1][0] <= 120.:
        time, temperature = known[-1]
        if temperature is None or not isfinite(temperature):
            temperature = None
        else:
            history = [(t, v) for t, v in known if t >= cutoff-600. and v is not None and isfinite(v)]
            change = temperature-history[0][1] if len(history) >= 2 else None
    ctx = case["context"]
    for field, expected in (("weather_at_s", time), ("track_temperature_c", temperature), ("track_change_c", change)):
        close(ctx[field], expected, field)
    seen = set()
    for window in ctx["field_windows"]:
        identity = window["driver"], window["stint"]
        if identity in seen:
            raise ValueError("Independent context audit duplicate field contribution")
        seen.add(identity)
        native = [lap(*identity, age) for age in case["ages"]]
        if any(c != case["compounds"][1] for _, _, _, c in native):
            raise ValueError("Independent context audit wrong field compound")
        available = max(end for _, end, _, _ in native)
        if available > cutoff:
            raise ValueError("Independent context audit future field contribution")
        close(window["available_at_s"], available, "field availability")
        close(window["change_s"], median(v[0] for v in native[-3:])-median(v[0] for v in native[:3]), "field drift")
    return len(seen)


def audit(data: dict, native_root: Path) -> dict:
    check_seal(data)
    count, contributions = 0, 0
    for event, source in data["sources"].items():
        if source["provider"] == "OPENF1":
            session = int(event)
            round_number, meeting, folder = OPENED[session]
            assert_development_event(2025, round_number)
            root = native_root/folder
            manifest = read_json(root/"manifest.json")
            check_seal(manifest)
            if manifest["content_sha256"] != source["archive_sha256"]:
                raise ValueError("Independent context audit archive binding mismatch")
            tables = {}
            for endpoint in ("sessions", "laps", "stints", "weather", "race_control"):
                name = f"{session}-{endpoint}.json"
                if file_sha256(root/name) != manifest["files"][name]:
                    raise ValueError("Independent context audit raw file hash mismatch")
                tables[endpoint] = read_json(root/name)
                if any(r.get("session_key") != session for r in tables[endpoint]):
                    raise ValueError("Independent context audit mixed native sessions")
            identity, = tables["sessions"]
            if (identity["year"], identity["meeting_key"], identity["session_name"]) != (2025, meeting, "Race"):
                raise ValueError("Independent context audit race identity mismatch")
        else:
            _, year_text, round_text = event.split("_")
            year, round_number = int(year_text), int(round_text[1:])
            assert_development_event(year, round_number)
            folder = f"fastf1-2024-r{round_number}-race-20261011" if year == 2024 else f"r026-fastf1-2023-r{round_number}-race-20261013"
            root = native_root/folder
            query = read_json(root/"manifest.json")["query"]
            assert_development_event(query["year"], query["round_number"])
            if (query["year"], query["round_number"], query["session"]) != (year, round_number, "R"):
                raise ValueError("Independent context audit event/query mismatch")
            manifest = verify_fastf1_archive(root)
            if manifest["content_sha256"] != source["archive_sha256"]:
                raise ValueError("Independent context audit native archive mismatch")
            tables = {"laps": pd.read_parquet(root/"tables/laps.parquet").to_dict("records"),
                      "weather": pd.read_parquet(root/"tables/weather_data.parquet").to_dict("records")}
        cases = [r for r in data["cases"] if str(r["session"]) == event]
        if len(cases) != source["blocks"]:
            raise ValueError("Independent context audit source case count mismatch")
        for case in cases:
            contributions += audit_case(case, tables, source["provider"])
            count += 1
    if count != len(data["cases"]):
        raise ValueError("Independent context audit unresolved source cases")
    return seal({"schema_version": "apex-compound-native-context-audit-v9", "dataset_sha256": data["content_sha256"],
                 "audit_source_sha256": file_sha256(Path(__file__)), "sources_verified": len(data["sources"]),
                 "cases_audited": count, "field_contributions_audited": contributions,
                 "future_associations": 0, "audit_passed": True,
                 "scope": "ALL_PUBLISHED_CONTEXT_ASSOCIATIONS_NOT_EXCLUDED_OR_ELIGIBLE_WINDOW_DENOMINATOR"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--native-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, audit(read_json(args.dataset), args.native_root))
