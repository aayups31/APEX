"""Inspect pinned TracingInsights metadata and known R041 lap-file coverage."""

import argparse
from hashlib import sha256
from pathlib import Path

import requests
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from diagnose_compound_decision import ROOT
from prepare_compound_trajectory import OPENED, V9

COMMIT = "dfb3ea3f50b69857fe8e40cabe5e899743c59f6a"
EVENTS = {
    2: "Chinese",
    3: "Japanese",
    4: "Bahrain",
    5: "Saudi Arabian",
    6: "Miami",
    7: "Emilia Romagna",
    9: "Spanish",
    10: "Canadian",
    11: "Austrian",
    12: "British",
    14: "Hungarian",
    15: "Dutch",
    16: "Italian",
    18: "Singapore",
    19: "United States",
    20: "Mexico City",
    22: "Las Vegas",
    23: "Qatar",
    24: "Abu Dhabi",
}


def fetch(url: str, cache: Path) -> tuple[dict, str]:
    """Cache exact HTTP bodies and verify immutable reloads without executing exports."""
    name = sha256(url.encode()).hexdigest()
    body, receipt = cache / f"{name}.json", cache / f"{name}.receipt.json"
    if not receipt.exists():
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        with body.open("xb") as handle:
            handle.write(response.content)
        write_manifest(receipt, seal({"url": url, "sha256": file_sha256(body)}))
    metadata = read_json(receipt)
    check_seal(metadata)
    if metadata["url"] != url or metadata["sha256"] != file_sha256(body):
        raise ValueError("TracingInsights cached response changed")
    return read_json(body), metadata["sha256"]


def investigate(cache: Path) -> dict:
    """Inventory only opened race metadata and the required known-lap paths."""
    cache.mkdir(parents=True, exist_ok=True)
    api = "https://api.github.com/repos/TracingInsights/2025"
    raw = f"https://raw.githubusercontent.com/TracingInsights/2025/{COMMIT}/"
    root, _ = fetch(f"{api}/git/trees/{COMMIT}", cache)
    root_paths = {x["path"]: x for x in root["tree"]}
    data = read_json(ROOT / "docs/verification/compound-v11-development-data.json")
    fuel = read_json(ROOT / "docs/verification/compound-v17-fuel-sensitivity.json")
    for doc in (data, fuel):
        check_seal(doc)
    if fuel["dataset_sha256"] != data["content_sha256"]:
        raise ValueError("Unbound native lap identity")
    lookup = {**OPENED, **{k: (*v, "unused") for k, v in V9.items()}}
    report, all_missing, total = {}, [], 0
    for event, source in data["sources"].items():
        if source["provider"] != "OPENF1":
            continue
        number = lookup[int(event)][0]
        assert_development_event(2025, number)
        folder = f"{EVENTS[number]} Grand Prix"
        tree, _ = fetch(f"{api}/git/trees/{root_paths[folder]['sha']}", cache)
        (race,) = [x for x in tree["tree"] if x["path"] == "Race"]
        files, binding = fetch(f"{api}/git/trees/{race['sha']}?recursive=1", cache)
        if files.get("truncated"):
            raise ValueError("Incomplete race file inventory")
        paths = {x["path"] for x in files["tree"] if x["type"] == "blob"}
        indices = [i for i, r in enumerate(data["cases"]) if str(r["session"]) == event]
        missing, required = [], set()
        if indices:
            drivers, driver_binding = fetch(raw + folder + "/Race/drivers.json", cache)
            codes = {int(d["dn"]): d["driver"] for d in drivers["drivers"]}
            for i in indices:
                r = data["cases"][i]
                if fuel["cases"][i]["index"] != i:
                    raise ValueError("Native lap index mismatch")
                for group in fuel["cases"][i]["windows"][:3]:
                    for lap, _, _ in group:
                        path = f"{codes[r['driver']]}/{int(lap)}_tel.json"
                        required.add(path)
            missing = sorted(required - paths)
        else:
            driver_binding = None
        report[event] = {
            "round": number,
            "folder": folder,
            "cases": len(indices),
            "required_unique_lap_files": len(required),
            "missing": missing,
            "race_tree_sha256": binding,
            "drivers_sha256": driver_binding,
        }
        all_missing.extend((event, p) for p in missing)
        total += len(required)
        print(f"{event}: {len(required)} required, {len(missing)} missing", flush=True)
    return seal(
        {
            "schema": "tracing-archive-r041-inventory",
            "repository": "TracingInsights/2025",
            "commit": COMMIT,
            "dataset_sha256": data["content_sha256"],
            "events": report,
            "required_unique_lap_files": total,
            "missing": all_missing,
            "scope": "FILE_EXISTENCE_ONLY_NOT_NATIVE_OR_PREDICTION_VALIDATION",
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, investigate(args.cache))
