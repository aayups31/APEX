"""Source-bound R021 lap segments; fuel and latent pace are explicitly proxies."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.data.jolpica import verify_jolpica_archive
from apexsim.provenance import file_sha256, payload_sha256


@dataclass(frozen=True)
class FuelPrior:
    initial_kg: float = 105.
    burn_kg_per_lap: float = 1.4
    time_s_per_kg: float = .030

    def effect(self, lap: int) -> float:
        if (type(lap) is not int or lap < 1 or not np.isfinite(list(asdict(self).values())).all()
                or min(asdict(self).values()) < 0):
            raise ValueError("Invalid fuel prior or lap index")
        mass = self.initial_kg - self.burn_kg_per_lap * (lap - 1)
        if mass < 0:
            raise ValueError("Fuel prior cannot support this lap; no clipping is allowed")
        return self.time_s_per_kg * mass


def _integer(value) -> bool:
    return isinstance(value, (int, float, np.number)) and not isinstance(value, (bool, np.bool_)) and np.isfinite(value) and value > 0 and value % 1 == 0


def segment_native_laps(frame: pd.DataFrame, event: dict, prior: FuelPrior) -> tuple[list[dict], list[dict]]:
    """Strict retrospective target-quality mask; no numerical pace outlier trimming."""
    assert_development_event(event["season"], event["round_number"], event_id=event["event_id"])
    required = {"DriverNumber", "LapNumber", "Stint", "Compound", "TyreLife", "LapTime", "IsAccurate",
                "Deleted", "TrackStatus", "PitInTime", "PitOutTime"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing native tyre fields: {sorted(required - set(frame.columns))}")
    accepted, rejected = [], []
    for index, row in enumerate(frame.to_dict("records")):
        reasons = []
        driver = pd.to_numeric(row["DriverNumber"], errors="coerce")
        if not all(_integer(v) for v in (driver, row["LapNumber"], row["Stint"])):
            reasons.append("invalid_driver_lap_stint_identity")
        time = row["LapTime"].total_seconds() if pd.notna(row["LapTime"]) else np.nan
        if not np.isfinite(time) or time <= 0:
            reasons.append("invalid_lap_time")
        if row["IsAccurate"] is not True:
            reasons.append("not_explicitly_accurate")
        if row["Deleted"] is not False:
            reasons.append("deleted_or_unknown")
        if row["TrackStatus"] != "1":
            reasons.append("not_exact_green_status")
        if pd.notna(row["PitInTime"]) or pd.notna(row["PitOutTime"]):
            reasons.append("pit_in_or_outlap")
        if row["Compound"] not in ("SOFT", "MEDIUM", "HARD"):
            reasons.append("non_dry_or_unknown_compound")
        if not isinstance(row["TyreLife"], (int, float)) or not np.isfinite(row["TyreLife"]) or row["TyreLife"] < 0:
            reasons.append("invalid_tyre_age")
        if reasons:
            rejected.append({"native_row": index, "reasons": reasons})
            continue
        lap = int(row["LapNumber"])
        effect = prior.effect(lap)
        accepted.append({"native_row": index, "driver": str(int(driver)), "lap": lap, "stint": int(row["Stint"]),
                         "compound": row["Compound"], "tyre_age": float(row["TyreLife"]),
                         "observed_s": float(time), "fuel_effect_s": effect, "corrected_s": float(time - effect)})
    if len({(r["driver"], r["lap"]) for r in accepted}) != len(accepted):
        raise ValueError("Duplicate driver/lap identity in tyre source")
    segments, active = [], []
    for row in sorted(accepted, key=lambda r: (r["driver"], r["lap"])):
        if active and (row["driver"] != active[-1]["driver"] or row["lap"] != active[-1]["lap"] + 1
                       or row["stint"] != active[-1]["stint"] or row["compound"] != active[-1]["compound"]):
            segments.append(active)
            active = []
        active.append(row)
    if active:
        segments.append(active)
    result = []
    for rows in segments:
        if len(rows) < 6:
            rejected.extend({"native_row": r["native_row"], "reasons": ["segment_shorter_than_six_laps"]} for r in rows)
            continue
        first = rows[0]
        result.append({"segment_id": f"{event['event_id']}_{first['driver']}_{first['stint']}_{first['lap']}",
                       **{k: event[k] for k in ("event_id", "season", "round_number", "track_id", "race_date")},
                       "driver": first["driver"], "compound": first["compound"], "stint": first["stint"], "rows": rows})
    return result, sorted(rejected, key=lambda r: r["native_row"])


def build_tyre_dataset(archives: list[Path], calendar: Path, prior: FuelPrior | None = None) -> dict:
    """Verify public source evidence before segmentation; all archives must be development races."""
    prior = prior or FuelPrior()
    catalog_manifest = verify_jolpica_archive(calendar)
    events = json.loads((calendar / "events.json").read_text(encoding="utf-8"))["events"]
    snapshots, segments, seen = [], [], set()
    for path in archives:
        # Benchmark guard precedes reading any native table/cache payload.
        metadata = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        query = metadata["query"]
        assert_development_event(query["year"], query["round_number"])
        if query["session"] != "R":
            raise ValueError("Tyre study requires race archives")
        manifest = verify_fastf1_archive(path)
        key = query["year"], query["round_number"]
        if key in seen:
            raise ValueError("Duplicate development event archive")
        seen.add(key)
        matches = [e for e in events if (e["season"], e["round_number"]) == key]
        if len(matches) != 1:
            raise ValueError("Race archive cannot be resolved against frozen calendar")
        event = {**matches[0], "track_id": matches[0]["circuit_id"]}
        frame = pd.read_parquet(path / "tables/laps.parquet")
        rows, rejected = segment_native_laps(frame, event, prior)
        if not rows:
            raise ValueError(f"No eligible race segments for {event['event_id']}")
        segments.extend(rows)
        snapshots.append({"event_id": event["event_id"], "race_date": event["race_date"], "query": query,
                          "archive_sha256": manifest["content_sha256"], "archive_manifest_file_sha256": file_sha256(path / "manifest.json"),
                          "lap_table_sha256": manifest["files"]["tables/laps.parquet"]["sha256"],
                          "environment": manifest["environment"], "native_rows": len(frame),
                          "eligible_segments": len(rows), "eligible_laps": sum(len(s["rows"]) for s in rows),
                          "rejected_rows": rejected, "rejection_counts": dict(Counter(r for row in rejected for r in row["reasons"]))})
        if verify_fastf1_archive(path)["content_sha256"] != manifest["content_sha256"]:
            raise ValueError("Race source changed during tyre dataset construction")
    result = {"schema_version": "apex-tyre-pace-dataset-v1", "fuel_prior": asdict(prior),
              "calendar_sha256": catalog_manifest["content_sha256"], "sources": sorted(snapshots, key=lambda r: r["race_date"]),
              "segments": sorted(segments, key=lambda s: (s["race_date"], s["driver"], s["stint"], s["rows"][0]["lap"])),
              "truth_labels": {"lap_values": "FASTF1_PARSED_SOURCE; upstream reconstruction possible", "fuel": "PRIOR",
                               "corrected_pace": "PROXY", "latent_state": "MODEL_ESTIMATE_NOT_PHYSICAL_WEAR"}}
    result["content_sha256"] = payload_sha256(result)
    return result
