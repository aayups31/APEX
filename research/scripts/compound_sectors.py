"""Extract native splits and replay the registered R041 sector comparison."""

import argparse
from hashlib import sha256
from math import isfinite, log1p
from pathlib import Path
from statistics import mean, median

import numpy as np
import pandas as pd
from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import write_manifest
from apexsim.research.compound_allocation import features, inventory
from apexsim.research.evidence import check_seal, read_json, seal
from audit_compound_context import utc
from audit_compound_driving import base_vector
from audit_compound_race_context import check_result
from audit_compound_repair import compare
from diagnose_compound_decision import ROOT
from diagnose_compound_line import FOLDER, evaluate
from prepare_compound_trajectory import OPENED, V9, tables_from_archive


def sector_record(duration: float, sectors: list) -> dict | None:
    """Keep measured positive splits whose sum reconciles to the raw lap."""
    if (
        len(sectors) != 3
        or not all(s is not None and isfinite(s) and s > 0 for s in sectors)
        or not isfinite(duration)
        or duration <= 0
        or abs(sum(sectors) - duration) > 0.05
    ):
        return None
    return {"duration_s": duration, "sectors_s": sectors}


def native_sectors(root: Path, event: str, source: dict) -> dict:
    if source["provider"] == "OPENF1":
        sessions = {
            **OPENED,
            **{k: (*v, "r041-v9-confirmation-20261104") for k, v in V9.items()},
        }
        number, meeting, folder = sessions[int(event)]
        tables, digest = tables_from_archive(
            root / folder, int(event), (number, meeting)
        )
        laps = [
            (
                r["driver_number"],
                utc(r["date_start"]),
                r["lap_duration"],
                [r.get(f"duration_sector_{i}") for i in (1, 2, 3)],
            )
            for r in tables["laps"]
            if r["date_start"] and r["lap_duration"] is not None
        ]
    elif source["provider"] == "FASTF1":
        _, year, race = event.split("_")
        number = int(race[1:])
        assert_development_event(int(year), number, event_id=event)
        folder = (
            f"fastf1-2024-r{number}-race-20261011"
            if year == "2024"
            else f"r026-fastf1-2023-r{number}-race-20261013"
        )
        archive = root / folder
        manifest = verify_fastf1_archive(archive)
        query = manifest["query"]
        if (query["year"], query["round_number"], query["session"]) != (
            int(year),
            number,
            "R",
        ):
            raise ValueError("Wrong FastF1 sector race identity")
        digest = manifest["content_sha256"]
        columns = [
            "DriverNumber",
            "LapStartDate",
            "LapTime",
            "Sector1Time",
            "Sector2Time",
            "Sector3Time",
        ]
        frame = pd.read_parquet(archive / "tables/laps.parquet", columns=columns)
        laps = [
            (
                int(d),
                utc(start),
                duration.total_seconds(),
                [None if pd.isna(v) else v.total_seconds() for v in splits],
            )
            for d, start, duration, *splits in frame.dropna(
                subset=columns[:3]
            ).itertuples(index=False, name=None)
        ]
    else:
        raise ValueError("Unknown sector provider")
    if digest != source["archive_sha256"]:
        raise ValueError("Sector archive differs from frozen cohort")
    indexed = {}
    for driver, start, duration, sectors in laps:
        key = driver, start + duration
        if key in indexed:
            raise ValueError("Ambiguous native sector clock")
        indexed[key] = sector_record(duration, sectors)
    return indexed


def link(row: dict, indexed: dict) -> list:
    """Link only known histories. The current future lap values are irrelevant."""
    groups = (
        row["current_history"][-3:],
        row["reference_history"][:3],
        row["reference_history"][-3:],
    )
    if any(len(g) != 3 for g in groups):
        raise ValueError("Wrong sector window shape")
    result = []
    for group in groups:
        known = []
        for lap in group:
            end = lap["end_s"]
            if end > row["forecast_at_s"]:
                raise ValueError("Future native sector observation")
            sample = indexed[row["driver"], end]
            known.append({"end_s": end, "split": sample})
        result.append(known)
    return result


def extract(data: dict, root: Path) -> dict:
    check_seal(data)
    groups = [None] * len(data["cases"])
    for event, source in data["sources"].items():
        indexed = native_sectors(root, event, source)
        for i, row in enumerate(data["cases"]):
            if str(row["session"]) == event:
                groups[i] = link(row, indexed)
    if any(g is None for g in groups):
        raise ValueError("Incomplete sector case inventory")
    return seal(
        {
            "schema": "compound-sector-data-v22",
            "dataset_sha256": data["content_sha256"],
            "groups": groups,
        }
    )


def sector_vector(groups: list) -> list[float]:
    supported = [all(lap["split"] is not None for lap in group) for group in groups]
    shares = [
        np.asarray([lap["split"]["sectors_s"] for lap in g]) if ok else np.zeros((3, 3))
        for g, ok in zip(groups, supported, strict=True)
    ]
    fractions = [
        s[:, :2] / s.sum(axis=1, keepdims=True) if ok else s[:, :2]
        for s, ok in zip(shares, supported, strict=True)
    ]
    current = fractions[0]
    offsets = [
        current.mean(axis=0) - fractions[j].mean(axis=0)
        if supported[0] and supported[j]
        else np.zeros(2)
        for j in (1, 2)
    ]
    return [
        *(current[-1] - current[0]).tolist(),
        *offsets[0].tolist(),
        *offsets[1].tolist(),
        *map(float, supported),
    ]


def audit(
    result: dict, data: dict, groups: list, nominations: dict, practice: dict
) -> dict:
    """Recompute scalar sector arithmetic and checkpoint forecasts independently."""
    for p in result["predictions"]:
        row = data["cases"][p["index"]]
        checkpoint = result["models"][str(row["session"])]
        window = groups[p["index"]]
        flags = [all(lap["split"] is not None for lap in g) for g in window]
        shares = [
            [
                [
                    v / sum(lap["split"]["sectors_s"])
                    for v in lap["split"]["sectors_s"][:2]
                ]
                for lap in g
            ]
            if ok
            else [[0.0, 0.0]] * 3
            for g, ok in zip(window, flags, strict=True)
        ]
        current = shares[0]
        extra = [current[-1][j] - current[0][j] for j in range(2)]
        extra.extend(
            mean(s[j] for s in current) - mean(s[j] for s in shares[g])
            if flags[0] and flags[g]
            else 0.0
            for g in (1, 2)
            for j in range(2)
        )
        x = base_vector(row, nominations, practice) + extra + list(map(float, flags))
        scaled = [
            (v - c) / s
            for v, c, s in zip(
                x, checkpoint["center"], checkpoint["scale"], strict=True
            )
        ]
        changes = [
            b
            + sum(v * w for v, w in zip(scaled, weights, strict=True))
            + median(row["current_prefix_s"])
            - lap
            for b, weights, lap in zip(
                checkpoint["intercept"],
                checkpoint["coefficients"],
                row["current_prefix_s"],
                strict=True,
            )
        ]
        laps = [
            lap + min(2.0, max(-2.0, delta))
            for lap, delta in zip(row["current_prefix_s"], changes, strict=True)
        ]
        compare(p["laps_s"], laps, "sector checkpoint forecast")
        compare(p["bounded_laps"], sum(abs(v) > 2 for v in changes), "sector bounds")
    return check_result(
        data,
        seal(
            {
                "result": result,
                "development_qualified": result["qualified"],
                "new_holdout_acquisition_allowed": result["qualified"],
            }
        ),
    )


def study(data: dict, observed: dict) -> dict:
    corrected = read_json(FOLDER / "compound-v21-nominations.json")
    practice = read_json(FOLDER / "compound-v17-practice-trends.json")
    previous = read_json(FOLDER / "compound-v21-development.json")
    for doc in (data, observed, corrected, practice, previous):
        check_seal(doc)
    if not (
        data["content_sha256"]
        == observed["dataset_sha256"]
        == previous["dataset_sha256"]
        == practice["dataset_sha256"]
        and corrected["content_sha256"] == previous["correction_sha256"]
    ):
        raise ValueError("Sector study inputs do not share the corrected cohort")
    allocations = inventory(corrected["sources"], set(data["sources"]))
    matrix = []
    for row, groups in zip(data["cases"], observed["groups"], strict=True):
        x = features(row, allocations, True)
        for compound in row["compounds"]:
            item = practice["events"][str(row["session"])][compound]
            x.extend([item["drift_s"] or 0.0, log1p(item["drivers"])])
        matrix.append(x + sector_vector(groups))
    result = evaluate(data["cases"], data["sources"], np.asarray(matrix))
    nominations = {
        event: (source["issued"], codes)
        for source in corrected["sources"]
        for event, codes in source["events"].items()
    }
    gates = audit(result, data, observed["groups"], nominations, practice["events"])
    return seal(
        {
            "schema": "compound-sector-model-v22",
            "dataset_sha256": data["content_sha256"],
            "sector_sha256": observed["content_sha256"],
            "control_sha256": previous["content_sha256"],
            "implementation_sha256_lf": sha256(
                Path(__file__).read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest(),
            "result": result,
            "independent_checkpoint_and_gate_audit": gates,
            "new_holdout_acquisition_allowed": result["qualified"],
            "candidate_accepted": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-root", type=Path, default=ROOT / ".cache")
    parser.add_argument(
        "--sectors",
        type=Path,
        help="Use a sealed sector extraction instead of reading native archives",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cohort = read_json(FOLDER / "compound-v11-development-data.json")
    document = (
        study(cohort, read_json(args.sectors))
        if args.sectors
        else extract(cohort, args.native_root)
    )
    write_manifest(args.output, document)
