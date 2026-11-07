"""Acquire only practice laps for the opened R041 weekends; support offline reruns."""

import argparse
import json
import os
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.jolpica import verify_jolpica_archive
from apexsim.data.openf1_http import DownloadPolicy, OpenF1Client
from apexsim.provenance import write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from diagnose_compound_decision import ROOT
from prepare_compound_trajectory import OPENED, V9, tables_from_archive

ENDPOINTS = ("laps", "stints", "weather", "race_control")


def snapshot(folder, name, endpoint, query, client):
    path = folder / name
    if not path.exists():
        if client is None:
            raise ValueError(f"Missing offline practice snapshot {name}")
        body, meta = client.get(endpoint, query)
        if meta["status_code"] != 200:
            raise ValueError(
                f"Practice query {query} {endpoint} returned HTTP {meta['status_code']}"
            )
        rows = json.loads(body)
        if not isinstance(rows, list):
            raise ValueError("Unexpected practice API response")
        doc = seal(
            {
                "endpoint": endpoint,
                "query": query,
                "http_body_sha256": sha256(body).hexdigest(),
                "rows": rows,
                "response": meta,
            }
        )
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=folder, delete=False
        ) as temp:
            json.dump(doc, temp)
        try:
            os.link(temp.name, path)
        except FileExistsError:
            pass
        finally:
            Path(temp.name).unlink()
    doc = read_json(path)
    check_seal(doc)
    if doc["endpoint"] != endpoint or doc["query"] != query:
        raise ValueError("Practice snapshot query mismatch")
    return doc["rows"], doc["content_sha256"]


def race_weekend(event, source, root):
    if source["provider"] == "OPENF1":
        lookup = {
            **OPENED,
            **{k: (*v, "r041-v9-confirmation-20261104") for k, v in V9.items()},
        }
        number, meeting, folder = lookup[int(event)]
        tables, digest = tables_from_archive(
            root / folder, int(event), (number, meeting)
        )
        if digest != source["archive_sha256"]:
            raise ValueError("Weekend identity source mismatch")
        race = tables["sessions"][0]
        return 2025, datetime.fromisoformat(race["date_start"]).date(), meeting
    if source["provider"] != "FASTF1":
        raise ValueError("Unknown R041 race provider")
    _, year, rd = event.split("_")
    assert_development_event(int(year), int(rd[1:]), event_id=event)
    folder = root / f"jolpica-{year}-20260916"
    verify_jolpica_archive(folder)
    (race,) = [
        r for r in read_json(folder / "events.json")["events"] if r["event_id"] == event
    ]
    return int(year), date.fromisoformat(race["race_date"]), None


def select_session(sessions, year, race_day, meeting):
    eligible = [
        s
        for s in sessions
        if s["year"] == year
        and s["session_type"] == "Practice"
        and s["session_name"] in ("Practice 1", "Practice 2")
        and not s.get("is_cancelled")
        and s.get("date_end")
        and 1 <= (race_day - datetime.fromisoformat(s["date_end"]).date()).days <= 4
        and (meeting is None or s["meeting_key"] == meeting)
    ]
    if not eligible:
        return None
    if len({s["meeting_key"] for s in eligible}) != 1:
        raise ValueError("Ambiguous practice weekend")
    best = max(s["session_name"] for s in eligible)
    (selected,) = [s for s in eligible if s["session_name"] == best]
    return selected


def prepare(folder, native_root, client):
    data = read_json(ROOT / "docs/verification/compound-v11-development-data.json")
    check_seal(data)
    folder.mkdir(parents=True, exist_ok=True)
    calendars, events = {}, {}
    for event, source in data["sources"].items():
        year, day, meeting = race_weekend(event, source, native_root)
        if year not in calendars:
            calendars[year] = snapshot(
                folder,
                f"{year}-practice.json",
                "sessions",
                {"year": year, "session_type": "Practice"},
                client,
            )
        sessions, digest = calendars[year]
        selected = select_session(sessions, year, day, meeting)
        meta = {
            "session": selected,
            "calendar_sha256": digest,
            "race_date": day.isoformat(),
            "tables": {},
        }
        if selected:
            key = selected["session_key"]
            for endpoint in ENDPOINTS:
                records, binding = snapshot(
                    folder,
                    f"{key}-{endpoint}.json",
                    endpoint,
                    {"session_key": key},
                    client,
                )
                if any(
                    (r["meeting_key"], r["session_key"])
                    != (selected["meeting_key"], key)
                    for r in records
                ):
                    raise ValueError("Practice session identity mismatch")
                meta["tables"][endpoint] = binding
        events[event] = meta
    return seal(
        {
            "schema": "practice-weekends-v17",
            "dataset_sha256": data["content_sha256"],
            "events": events,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--native-root", type=Path, default=ROOT / ".cache")
    parser.add_argument("--acquire", action="store_true")
    args = parser.parse_args()
    client = OpenF1Client(DownloadPolicy()) if args.acquire else None
    try:
        write_manifest(args.output, prepare(args.snapshots, args.native_root, client))
    finally:
        if client:
            client.close()
