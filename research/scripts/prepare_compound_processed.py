"""Download and bind buffered processed telemetry only for opened R041 observations."""

from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.jolpica import verify_jolpica_archive
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from apexsim.research.tracing_telemetry import associate_lap, export_samples
from compound_driving_data import lap_summary
from diagnose_compound_decision import ROOT
from inspect_tracing_archive import EVENTS
from prepare_compound_trajectory import OPENED, V9

PINS = {
    2023: "737c84d3ae14b9883a671ca248d015b69cf1cb58",
    2024: "d1543a71370d9b617b627319f8ad80b2f85dfd5e",
    2025: "dfb3ea3f50b69857fe8e40cabe5e899743c59f6a",
}


def calendar_event(event: str, root: Path) -> dict:
    """Resolve exact archived event identity, including cancelled-round renumbering."""
    _, text, race = event.split("_")
    year, number = int(text), int(race[1:])
    assert_development_event(year, number, event_id=event)
    calendar = root / f"jolpica-{year}-20260916"
    verify_jolpica_archive(calendar)
    (result,) = [
        r
        for r in read_json(calendar / "events.json")["events"]
        if r["event_id"] == event
    ]
    return result


def fetch(url: str, cache: Path) -> tuple[dict | None, str]:
    """Publish content-addressed HTTP bodies and immutable URL receipts, with bounded retries."""
    receipt = cache / f"{sha256(url.encode()).hexdigest()}.receipt.json"
    if not receipt.exists():
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=(10, 60))
                if response.status_code not in (200, 404):
                    response.raise_for_status()
                body = response.content
                break
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
        digest = sha256(body).hexdigest()
        target = cache / f"{digest}.body"
        with NamedTemporaryFile(dir=cache, delete=False) as temp:
            temp.write(body)
        try:
            os.link(temp.name, target)
        except FileExistsError:
            pass
        finally:
            Path(temp.name).unlink()
        write_manifest(
            receipt,
            seal({"url": url, "status": response.status_code, "body_sha256": digest}),
        )
    doc = read_json(receipt)
    check_seal(doc)
    target = cache / f"{doc['body_sha256']}.body"
    if doc["url"] != url or file_sha256(target) != doc["body_sha256"]:
        raise ValueError("Processed archive snapshot changed")
    return (json.loads(target.read_bytes()) if doc["status"] == 200 else None), doc[
        "content_sha256"
    ]


def prepare(cache: Path) -> dict:
    """Preserve all cases, recording rejected input laps without changing target labels."""
    cache.mkdir(parents=True, exist_ok=True)
    folder = ROOT / "docs/verification"
    data = read_json(folder / "compound-v11-development-data.json")
    fuel = read_json(folder / "compound-v17-fuel-sensitivity.json")
    for doc in (data, fuel):
        check_seal(doc)
    if fuel["dataset_sha256"] != data["content_sha256"]:
        raise ValueError("Native identity parent mismatch")
    tasks, associations, origins = {}, [], {}
    mapping = {**OPENED, **{k: (*v, "unused") for k, v in V9.items()}}
    for event, source in data["sources"].items():
        if source["provider"] == "OPENF1":
            year, number = 2025, mapping[int(event)][0]
            name = EVENTS[number]
        else:
            _, text, race = event.split("_")
            year, number = int(text), int(race[1:])
            calendar = calendar_event(event, ROOT / ".cache")
            name = calendar["race_name"].removesuffix(" Grand Prix")
        assert_development_event(year, number)
        indices = [i for i, r in enumerate(data["cases"]) if str(r["session"]) == event]
        base = f"https://raw.githubusercontent.com/TracingInsights/{year}/{PINS[year]}/{name} Grand Prix/Race/"
        origins[event] = {
            "year": year,
            "round": number,
            "commit": PINS[year],
            "cases": len(indices),
            "base_url": base,
            "native_archive_sha256": source["archive_sha256"],
        }
        if not indices:
            continue
        session, session_hash = fetch(base + "session_info.json", cache)
        if (
            session is None
            or session["session_info"]["Name"] != "Race"
            or not session["session_info"]["Path"].startswith(f"{year}/")
            or session["session_info"]["Meeting"]["Name"] != f"{name} Grand Prix"
        ):
            raise ValueError("Wrong exported race identity")
        if source["provider"] == "OPENF1":
            if int(session["session_info"]["Key"]) != int(event):
                raise ValueError("Wrong exported native session key")
        elif session["session_info"]["StartDate"][:10] != calendar["race_date"]:
            raise ValueError("Exported race date differs from verified calendar")
        drivers, driver_hash = fetch(base + "drivers.json", cache)
        if drivers is None:
            raise ValueError("Missing exported driver inventory")
        codes = {}
        for driver in drivers["drivers"]:
            if "dn" in driver:
                identity = int(driver["dn"])
            else:
                legacy, _ = fetch(base + driver["driver"] + "/laptimes.json", cache)
                if legacy is None or len(set(legacy["dNum"])) != 1:
                    raise ValueError("Ambiguous legacy driver number")
                identity = int(legacy["dNum"][0])
            if identity in codes:
                raise ValueError("Duplicate exported driver number")
            codes[identity] = driver["driver"]
        origins[event].update(session_sha256=session_hash, drivers_sha256=driver_hash)
        metadata = {}
        for driver in sorted({data["cases"][i]["driver"] for i in indices}):
            code = codes[driver]
            metadata[driver] = fetch(base + code + "/laptimes.json", cache)
        for i in indices:
            row, record = data["cases"][i], fuel["cases"][i]
            if record["index"] != i or record["event"] != event:
                raise ValueError("Wrong frozen native lap identity")
            histories = (
                row["current_history"][-3:],
                row["reference_history"][:3],
                row["reference_history"][-3:],
            )
            for g, (position, native) in enumerate(
                zip((1, 0, 2), histories, strict=True)
            ):
                stint_pos = 1 if g == 0 else 0
                for j, lap in enumerate(native[:2]):
                    number_lap, duration, _ = record["windows"][position][j]
                    number_lap = int(number_lap)
                    code = codes[row["driver"]]
                    url = base + code + f"/{number_lap}_tel.json"
                    key = f"{year}-{name} Grand Prix-Race-{code}-{number_lap}"
                    tasks[url] = key
                    associations.append(
                        {
                            "case": i,
                            "group": g,
                            "offset": j,
                            "url": url,
                            "key": key,
                            "lap": number_lap,
                            "driver": row["driver"],
                            "compound": row["compounds"][stint_pos],
                            "stint": row["stints"][stint_pos],
                            "age": lap["age"],
                            "start_s": lap["end_s"] - duration,
                            "duration_s": duration,
                            "cutoff_s": row["forecast_at_s"],
                            "metadata": metadata[row["driver"]],
                        }
                    )
        print(f"Prepared identity {event}", flush=True)
    urls = sorted(tasks)
    with ThreadPoolExecutor(max_workers=6) as pool:
        payloads = dict(
            zip(urls, pool.map(lambda u: fetch(u, cache), urls), strict=True)
        )
    summaries = [[[None, None] for _ in range(3)] for _ in data["cases"]]
    rejected, links = [], []
    for item in associations:
        payload, binding = payloads[item["url"]]
        meta, meta_binding = item["metadata"]
        link = {k: v for k, v in item.items() if k != "metadata"}
        link.update(payload_sha256=binding, metadata_sha256=meta_binding)
        try:
            if payload is None or meta is None:
                raise ValueError("Missing archive lap file")
            timing = associate_lap(
                meta,
                **{
                    k: item[k]
                    for k in (
                        "lap",
                        "driver",
                        "compound",
                        "stint",
                        "age",
                        "start_s",
                        "duration_s",
                        "cutoff_s",
                    )
                },
            )
            samples = export_samples(payload, item["key"])
            summary = lap_summary(samples, 1.0, timing["duration_s"] - 1.0)
            link.update(timing)
        except (ValueError, KeyError, TypeError) as error:
            summary = {"coverage": 0.0, "means": [0.0] * 5, "samples": 0}
            link["rejection"] = str(error)
            rejected.append(
                {
                    "case": item["case"],
                    "group": item["group"],
                    "offset": item["offset"],
                    "reason": str(error),
                }
            )
        summaries[item["case"]][item["group"]][item["offset"]] = summary
        links.append(link)
    if any(p is None for groups in summaries for group in groups for p in group):
        raise ValueError("Missing processed case association")
    return seal(
        {
            "schema": "compound-processed-data-v20",
            "dataset_sha256": data["content_sha256"],
            "pins": PINS,
            "origins": origins,
            "unique_requested_files": len(urls),
            "lap_summaries": summaries,
            "links": links,
            "rejected": rejected,
            "native_provenance_known": False,
            "new_holdout_acquisition_allowed": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, prepare(args.cache))
