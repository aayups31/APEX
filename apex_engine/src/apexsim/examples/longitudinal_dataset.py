"""R030 source-bound native sections and portable input-only scientific replay."""
from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research.longitudinal_data import EVENT_ROLES, LongitudinalSection, extract_sections

GEOMETRY_SEAL = "e22c1c6e0bf35a195120e47e6198c02d38549af4d51d38ef9f400c125d4ba684"
GEOMETRY_INVENTORY = "0caa4285294656c9d223ae4c79348c7f0990ff117c04e6f026947e4d0b7d0162"
VERSION = "apex-longitudinal-dataset-v1"
ARRAYS = ("time_s", "speed_mps", "throttle", "drs_open", "car_rows", "geometry_rows", "warmup_time_s", "warmup_speed_mps")
PROTOCOL = Path(__file__).resolve().parents[4]/"research/protocols/LONGITUDINAL_CALIBRATION.md"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_seal(payload: dict) -> None:
    if payload.get("content_sha256") != payload_sha256({k: v for k, v in payload.items() if k != "content_sha256"}):
        raise ValueError("R030 content seal mismatch")


def sealed_write(path: Path, payload: dict) -> None:
    payload["content_sha256"] = payload_sha256(payload)
    write_manifest(path, payload)


def inventory(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): {"sha256": file_sha256(p), "bytes": p.stat().st_size}
            for p in sorted(root.rglob("*")) if p.is_file() and p != root/"manifest.json"}


def verify_inventory(root: Path, schema: str) -> dict:
    manifest = read_json(root/"manifest.json")
    check_seal(manifest)
    if manifest.get("schema_version") != schema:
        raise ValueError("R030 manifest schema mismatch")
    for name in manifest["files"]:
        p = root/name
        if ("\\" in name or Path(name).is_absolute() or ".." in Path(name).parts
                or p.is_symlink() or not p.resolve().is_relative_to(root.resolve())):
            raise ValueError("R030 unsafe artifact path")
    if inventory(root) != manifest["files"]:
        raise ValueError("R030 artifact inventory/hash mismatch")
    return manifest


def geometry_header(root: Path) -> dict:
    """Guard all source weekends before reading geometry/native payloads."""
    summary, manifest = read_json(root/"summary.json"), read_json(root/"manifest.json")
    for source in summary["sources"]:
        q = source["manifest"]["query"]
        assert_development_event(q["year"], q["round_number"], event_id=source["event_id"])
    check_seal(summary)
    check_seal(manifest)
    if (summary["content_sha256"] != GEOMETRY_SEAL or manifest["content_sha256"] != GEOMETRY_INVENTORY
            or manifest["summary_sha256"] != GEOMETRY_SEAL or not summary["task_closure_eligible"]
            or {s["event_id"] for s in summary["sources"]} != set(EVENT_ROLES)):
        raise ValueError("R030 requires frozen accepted public R029 geometry")
    return summary


def dataset_guard(root: Path) -> dict:
    geometry = geometry_header(root/"geometry")
    expected = {s["event_id"]: s for s in geometry["sources"]}
    for event in EVENT_ROLES:
        manifest = read_json(root/"native"/event/"manifest.json")
        q = manifest["query"]
        assert_development_event(q["year"], q["round_number"], event_id=event)
        check_seal(manifest)
        if manifest["content_sha256"] != expected[event]["archive_sha256"] or q["session"] != "R":
            raise ValueError("R030 native archive/geometry source binding mismatch")
    return geometry


def extract_snapshots(root: Path) -> tuple[list[LongitudinalSection], list[dict], list[dict]]:
    """Extract all source-selected sections, preserving every rejected native row."""
    geometry = dataset_guard(root)
    verify_inventory(root/"geometry", "apex-reference-geometry-manifest-v1")
    cars, laps = {}, {}
    for source in geometry["sources"]:
        event = source["event_id"]
        manifest = read_json(root/"native"/event/"manifest.json")
        for name in ("tables/laps.parquet", "tables/car_data/4.parquet", "tables/car_data/44.parquet"):
            path = root/"native"/event/name
            if file_sha256(path) != manifest["files"][name]["sha256"]:
                raise ValueError("R030 native table hash differs from frozen archive")
        laps[event] = pd.read_parquet(root/"native"/event/"tables/laps.parquet")
        for driver in ("4", "44"):
            cars[event, driver] = pd.read_parquet(root/"native"/event/f"tables/car_data/{driver}.parquet")
    sections, quality, rejections = [], [], []
    for track in ("bahrain", "monza"):
        metadata = read_json(root/"geometry"/f"{track}_lap_metadata.json")
        with (np.load(root/"geometry"/f"{track}_lap_inputs.npz", allow_pickle=False) as native,
              np.load(root/"geometry"/f"{track}_geometry_predictions.npz", allow_pickle=False) as model):
            for lap in metadata:
                event, driver, key = lap["event_id"], lap["driver_id"], lap["lap_id"]
                row = laps[event].iloc[lap["native_row"]]
                if (str(row.DriverNumber) != driver or int(row.LapNumber) != lap["lap_number"]
                        or abs(row.LapStartTime.total_seconds()-lap["lap_start_s"]) > 1e-6
                        or abs(row.Time.total_seconds()-lap["lap_end_s"]) > 1e-6):
                    raise ValueError("R030 native lap identity/timing differs from frozen geometry")
                observed = {"time_s": native[key+"_time"], "native_parents": native[key+"_native_parents"],
                            "curvature_1pm": model[key+"_curvature_1pm"], "distance_m": model[key+"_distance_m"]}
                current, q, rejected = extract_sections(cars[event, driver], lap, observed)
                sections.extend(current)
                quality.append(q)
                rejections.extend(rejected)
    sections.sort(key=lambda s: (s.metadata["event_id"], s.metadata["driver_id"], s.metadata["lap_number"], s.car_rows[0]))
    return sections, quality, rejections


def save_sections(root: Path, sections: list[LongitudinalSection]) -> None:
    write_manifest(root/"section_metadata.json", [s.metadata for s in sections])
    np.savez_compressed(root/"sections.npz", **{f"s{i}_{name}": getattr(s, name) for i, s in enumerate(sections) for name in ARRAYS})


def load_sections(root: Path) -> list[LongitudinalSection]:
    metadata = read_json(root/"section_metadata.json")
    with np.load(root/"sections.npz", allow_pickle=False) as arrays:
        if set(arrays.files) != {f"s{i}_{name}" for i in range(len(metadata)) for name in ARRAYS}:
            raise ValueError("R030 section array inventory mismatch")
        return [LongitudinalSection(m, *(arrays[f"s{i}_{name}"] for name in ARRAYS)) for i, m in enumerate(metadata)]


def source_summary(sections: list[LongitudinalSection], quality: list[dict]) -> dict:
    cells = {}
    for section in sections:
        key = section.metadata["role"]+"/"+section.cell
        cells.setdefault(key, []).append(section)
    coverage = {key: {"sections": len(values), "laps": len({s.metadata["lap_id"] for s in values}),
                      "intervals": sum(len(s.time_s)-1 for s in values),
                      "closed_intervals": sum(len(s.time_s)-1 for s in values if s.drs_open[0] == 0),
                      "open_intervals": sum(len(s.time_s)-1 for s in values if s.drs_open[0] == 1)} for key, values in cells.items()}
    required = ["train/"+track+"/"+driver for track in ("bahrain", "monza") for driver in ("4", "44")]
    passed = all(coverage.get(key, {}).get("intervals", 0) >= 100 and coverage[key]["laps"] >= 5 for key in required)
    passed &= all(coverage.get("test/monza/"+d, {}).get("sections", 0) >= 10
                  and coverage["test/monza/"+d]["laps"] >= 5 for d in ("4", "44"))
    passed &= all(coverage.get("validation/bahrain/"+d, {}).get("sections", 0) > 0 for d in ("4", "44"))
    counts: Counter = Counter()
    for q in quality:
        counts.update(q["rejection_counts"])
    return {"source_gate_passed": bool(passed), "sections": len(sections), "selected_source_laps": len(quality),
            "coverage": coverage, "native_lap_rows": sum(q["native_lap_rows"] for q in quality),
            "eligible_rows": sum(q["eligible_rows"] for q in quality), "rejection_counts": dict(counts)}


def prepare_longitudinal_dataset(geometry: Path, archives: list[Path], output: Path) -> dict:
    """Freeze native source preflight before fitting; completed inputs are never overwritten."""
    if output.exists():
        raise FileExistsError("R030 dataset output must be fresh")
    if any(output.resolve().is_relative_to(p.resolve()) for p in (geometry, *archives)):
        raise ValueError("R030 output must be outside immutable inputs")
    reference = geometry_header(geometry)
    verify_inventory(geometry, "apex-reference-geometry-manifest-v1")
    expected = {s["event_id"]: s["archive_sha256"] for s in reference["sources"]}
    sources = {}
    # All query identities guarded before any native table or cache is hashed/read.
    for path in archives:
        manifest = read_json(path/"manifest.json")
        q = manifest["query"]
        event = f"F1_{q['year']}_R{q['round_number']:02d}"
        assert_development_event(q["year"], q["round_number"], event_id=event)
        if event not in expected or event in sources or q["session"] != "R":
            raise ValueError("R030 requires four unique exact development race archives")
        sources[event] = path
    if set(sources) != set(expected):
        raise ValueError("R030 frozen source cohort is incomplete")
    for event, path in sources.items():
        if verify_fastf1_archive(path)["content_sha256"] != expected[event]:
            raise ValueError("R030 native archive seal differs from R029")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(geometry, output/"geometry")
    for event, path in sources.items():
        target = output/"native"/event
        (target/"tables/car_data").mkdir(parents=True)
        for name in ("manifest.json", "tables/laps.parquet", "tables/car_data/4.parquet", "tables/car_data/44.parquet"):
            shutil.copyfile(path/name, target/name)
    shutil.copyfile(PROTOCOL, output/"protocol.md")
    sections, quality, rejections = extract_snapshots(output)
    save_sections(output, sections)
    write_manifest(output/"quality.json", quality)
    write_manifest(output/"rejections.json", rejections)
    summary = {"schema_version": VERSION, "profile": "research", "input_truth": "FASTF1_PARSED_SOURCE",
               "geometry_summary_sha256": GEOMETRY_SEAL, "split": EVENT_ROLES, **source_summary(sections, quality),
               "fitting_performed": False, "promotion": False}
    sealed_write(output/"summary.json", summary)
    sealed_write(output/"manifest.json", {"schema_version": VERSION+"-manifest", "summary_sha256": summary["content_sha256"], "files": inventory(output)})
    return summary


def verify_longitudinal_dataset(root: Path) -> dict:
    """Regenerate source sections and every rejection from portable sealed native tables."""
    dataset_guard(root)
    manifest = verify_inventory(root, VERSION+"-manifest")
    summary = read_json(root/"summary.json")
    check_seal(summary)
    if manifest["summary_sha256"] != summary["content_sha256"] or summary.get("profile") != "research":
        raise ValueError("R030 dataset summary binding mismatch")
    regenerated, quality, rejected = extract_snapshots(root)
    stored = load_sections(root)
    if (len(stored) != len(regenerated) or quality != read_json(root/"quality.json")
            or rejected != read_json(root/"rejections.json")):
        raise ValueError("R030 source accounting replay mismatch")
    for first, second in zip(stored, regenerated, strict=True):
        if first.metadata != second.metadata or any(not np.array_equal(getattr(first, k), getattr(second, k)) for k in ARRAYS):
            raise ValueError("R030 native section scientific replay mismatch")
    for key, value in source_summary(regenerated, quality).items():
        if summary[key] != value:
            raise ValueError("R030 source summary/gate replay mismatch")
    return {"verified": True, "sections": len(stored), "source_gate_passed": summary["source_gate_passed"], "summary_sha256": summary["content_sha256"]}
