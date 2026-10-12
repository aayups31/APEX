"""R024 source-bound motion proxies; no measured wheel-energy claim or filling."""
from __future__ import annotations

import json
import platform
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from itertools import pairwise
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.data.fastf1_archive import verify_fastf1_archive
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research import tyre_energy
from apexsim.research.tyre_energy import WHEEL_NAMES, TyreEnergyInputs, estimate_wheel_tyre_energy

VERSION = "apex-tyre-energy-proxy-v1"
EVENTS = ("F1_2024_R01", "F1_2024_R03", "F1_2024_R06", "F1_2024_R16", "F1_2024_R18")


@dataclass(frozen=True)
class ProxyDatasetConfig:
    """Frozen support/vehicle PRIORs, seconds/metres/radians/SI throughout."""
    drivers: tuple[str, ...] = ("4", "44")
    car_history: int = 5
    position_history: int = 7
    max_gap_s: float = .5
    max_position_lag_s: float = .35
    min_car_span_s: float = .4
    min_position_span_s: float = .8
    max_history_span_s: float = 2.
    min_speed_mps: float = 5.
    max_speed_mps: float = 105.
    min_geometry_speed_ratio: float = .5
    max_geometry_speed_ratio: float = 1.5
    max_longitudinal_accel_mps2: float = 30.
    max_lateral_accel_mps2: float = 60.
    max_heading_rate_rad_s: float = 1.5
    max_steering_rad: float = .6
    mass_kg: float = 900.
    wheelbase_m: float = 3.6
    min_wheel_normal_load_n: float = 50.

    def __post_init__(self) -> None:
        values = [v for k, v in asdict(self).items() if k != "drivers"]
        if (not self.drivers or len(set(self.drivers)) != len(self.drivers)
                or any(not isinstance(d, str) or not d.isdigit() for d in self.drivers)
                or type(self.car_history) is not int or self.car_history < 2
                or type(self.position_history) is not int or self.position_history < 3
                or not np.isfinite(values).all() or min(values) <= 0
                or self.min_wheel_normal_load_n < 50
                or self.min_speed_mps >= self.max_speed_mps
                or self.min_geometry_speed_ratio >= self.max_geometry_speed_ratio):
            raise ValueError("Invalid tyre-energy proxy support/vehicle priors")


# Canonical fields have one unambiguous truth label and unit. All measured wheel
# quantities remain nullable UNKNOWN, separate from the four PROXY targets.
FIELDS = {
    **{name: (pa.string(), "RECONSTRUCTED", "1") for name in
       ("event_id", "session_id", "track_id", "driver_id", "segment_id", "sequence_id", "compound")},
    **{name: (pa.int64(), "RECONSTRUCTED", "1") for name in
       ("sample_id", "lap_number", "native_car_row", "car_history_start_row", "position_history_start_row", "native_position_row")},
    **{name: (pa.float64(), "RECONSTRUCTED", "s") for name in ("time_s", "dt_s", "position_time_s", "position_lag_s")},
    "speed_kmh": (pa.float64(), "MEASURED", "km/h"),
    "throttle_percent": (pa.float64(), "MEASURED", "%"),
    "brake_applied": (pa.bool_(), "MEASURED", "1"),
    "speed_mps": (pa.float64(), "RECONSTRUCTED", "m/s"),
    "throttle": (pa.float64(), "RECONSTRUCTED", "1"),
    "longitudinal_accel_mps2": (pa.float64(), "RECONSTRUCTED", "m/s^2"),
    "geometry_speed_mps": (pa.float64(), "RECONSTRUCTED", "m/s"),
    "heading_rate_rad_s": (pa.float64(), "RECONSTRUCTED", "rad/s"),
    "curvature_proxy_inv_m": (pa.float64(), "PROXY", "1/m"),
    "lateral_accel_proxy_mps2": (pa.float64(), "PROXY", "m/s^2"),
    "steering_rad_proxy": (pa.float64(), "PROXY", "rad"),
    "brake_pressure_proxy": (pa.float64(), "PROXY", "1"),
    "mass_prior_kg": (pa.float64(), "PRIOR", "kg"),
    **{f"tyre_energy_{w}_kj": (pa.float64(), "PROXY", "kJ") for w in WHEEL_NAMES},
    **{f"tyre_power_{w}_kw": (pa.float64(), "PROXY", "kW") for w in WHEEL_NAMES},
    **{f"measured_{quantity}_{w}": (pa.float64(), "UNKNOWN", unit)
       for quantity, unit in (("wheel_force_n", "N"), ("slip_speed_mps", "m/s"), ("tyre_energy_kj", "kJ")) for w in WHEEL_NAMES},
}
UNKNOWN = {name for name, (_, label, _) in FIELDS.items() if label == "UNKNOWN"}


def sample_schema() -> pa.Schema:
    return pa.schema([pa.field(name, dtype, nullable=name in UNKNOWN,
                              metadata={b"truth_label": label.encode(), b"unit": unit.encode()})
                      for name, (dtype, label, unit) in FIELDS.items()], metadata={b"apex.schema_version": VERSION.encode()})


def motion_from_positions(times: np.ndarray, xy_m: np.ndarray) -> tuple[float, float]:
    """Quadratic fit using only the supplied past; returns speed and signed heading rate."""
    t, xy = np.asarray(times, float), np.asarray(xy_m, float)
    if (t.ndim != 1 or len(t) < 3 or xy.shape != (len(t), 2) or not np.isfinite(t).all()
            or not np.isfinite(xy).all() or np.any(np.diff(t) <= 0)):
        raise ValueError("Motion fit requires finite increasing past position samples")
    tau = t - t[-1]
    coefficients, _, rank, _ = np.linalg.lstsq(np.column_stack((np.ones(len(t)), tau, tau**2)), xy, rcond=None)
    velocity, acceleration = coefficients[1], 2 * coefficients[2]
    speed = np.linalg.norm(velocity)
    if rank != 3 or speed <= 1e-8:
        raise ValueError("Unsupported stationary/rank-deficient position history")
    omega = (velocity[0] * acceleration[1] - velocity[1] * acceleration[0]) / speed**2
    return float(speed), float(omega)


def _seconds(frame: pd.DataFrame) -> np.ndarray:
    if "SessionTime" not in frame:
        raise ValueError("Native telemetry lacks SessionTime")
    values = frame["SessionTime"].dt.total_seconds().to_numpy()
    if not np.isfinite(values).all() or np.any(np.diff(values) <= 0):
        raise ValueError("Native telemetry times must be finite and strictly increasing")
    return values


def _loads(x: TyreEnergyInputs) -> np.ndarray:
    """Unclipped R006 load equation; reject support requiring its 50 N projection."""
    front = x.front_weight_fraction * x.mass_kg * 9.81 - x.mass_kg * x.longitudinal_accel_mps2 * x.cg_height_m / x.wheelbase_m
    rear = x.mass_kg * 9.81 - front
    transfer = x.mass_kg * x.lateral_accel_mps2 * x.cg_height_m / x.track_width_m
    return np.array([front/2 + x.front_weight_fraction*transfer/2, front/2 - x.front_weight_fraction*transfer/2,
                     rear/2 + (1-x.front_weight_fraction)*transfer/2, rear/2 - (1-x.front_weight_fraction)*transfer/2])


def canonical_proxy_samples(car: pd.DataFrame, positions: pd.DataFrame, segments: list[dict], laps: pd.DataFrame,
                            config: ProxyDatasetConfig | None = None) -> tuple[list[dict], list[dict]]:
    """One native driver stream; backward-only reconstruction, named exclusion for every row."""
    cfg = config or ProxyDatasetConfig()
    if not segments:
        raise ValueError("No eligible stint segments for this driver")
    for s in segments:
        assert_development_event(s["season"], s["round_number"], event_id=s["event_id"])
    if len({(s["event_id"], s["driver"]) for s in segments}) != 1:
        raise ValueError("Canonical proxy conversion requires one event/driver stream")
    if not {"Speed", "Throttle", "Brake", "Source"}.issubset(car) or not {"X", "Y", "Status", "Source"}.issubset(positions):
        raise ValueError("Missing native car/position proxy fields")
    ct, pt = _seconds(car), _seconds(positions)
    speed = car["Speed"].to_numpy(float) / 3.6
    xy = positions[["X", "Y"]].to_numpy(float) * .1
    lap_lookup = {}
    for segment in segments:
        for row in segment["rows"]:
            native = row["native_row"]
            lap = laps.iloc[native]
            if str(lap["DriverNumber"]) != segment["driver"] or int(lap["LapNumber"]) != row["lap"] or lap["Compound"] != segment["compound"]:
                raise ValueError("Eligible mask/native lap identity mismatch")
            start, end = lap["LapStartTime"].total_seconds(), lap["Time"].total_seconds()
            if not np.isfinite([start, end]).all() or end <= start:
                raise ValueError("Invalid eligible native lap interval")
            if row["lap"] in lap_lookup:
                raise ValueError("Duplicate eligible driver/lap")
            lap_lookup[row["lap"]] = (start, end, segment)
    intervals = sorted(lap_lookup.items(), key=lambda item: item[1][0])
    if any(a[1][1] > b[1][0] for a, b in pairwise(intervals)):
        raise ValueError("Overlapping eligible lap intervals")
    starts = np.array([item[1][0] for item in intervals])
    ends = np.array([item[1][1] for item in intervals])
    assignments = np.searchsorted(starts, ct, side="right") - 1
    position_indices = np.searchsorted(pt, ct, side="right") - 1
    first = segments[0]
    event, driver = first["event_id"], first["driver"]
    output, rejected = [], []
    segment_starts = {}
    for _, (start, _, segment) in intervals:
        segment_starts.setdefault(segment["segment_id"], start)
    car_sources, pos_sources = car["Source"].to_numpy(), positions["Source"].to_numpy()
    statuses = positions["Status"].to_numpy()
    throttles, brakes = car["Throttle"].to_numpy(), car["Brake"].to_numpy()
    active, run_number, previous_native = None, 0, -2
    for i, time in enumerate(ct):
        def reject(reason: str, native_row: int = i) -> None:
            rejected.append({"event_id": event, "driver_id": driver, "native_car_row": native_row, "reason": reason})
        assignment = assignments[i]
        if assignment < 0 or time >= ends[assignment]:
            reject("outside_eligible_lap")
            continue
        lap_number, (_, _, segment) = intervals[assignment]
        segment_start = segment_starts[segment["segment_id"]]
        c0, p1 = i - cfg.car_history + 1, position_indices[i]
        p0 = p1 - cfg.position_history + 1
        if c0 < 0 or p0 < 0 or ct[c0] < segment_start or pt[p0] < segment_start:
            reject("segment_history_warmup")
            continue
        if (not np.all(car_sources[c0:i+1] == "car") or not np.all(pos_sources[p0:p1+1] == "pos")
                or not np.all(statuses[p0:p1+1] == "OnTrack")):
            reject("unsupported_native_source_or_position_status")
            continue
        if (max(np.diff(ct[c0:i+1])) > cfg.max_gap_s or max(np.diff(pt[p0:p1+1])) > cfg.max_gap_s
                or not cfg.min_car_span_s <= ct[i]-ct[c0] <= cfg.max_history_span_s
                or not cfg.min_position_span_s <= pt[p1]-pt[p0] <= cfg.max_history_span_s
                or not 0 <= time-pt[p1] <= cfg.max_position_lag_s):
            reject("history_gap_span_or_position_lag")
            continue
        throttle, brake = throttles[i], brakes[i]
        if (not np.isfinite(speed[c0:i+1]).all() or not cfg.min_speed_mps <= speed[i] <= cfg.max_speed_mps
                or not np.isfinite(throttle) or not 0 <= throttle <= 100 or not isinstance(brake, (bool, np.bool_))):
            reject("unsupported_speed_or_controls")
            continue
        tau = ct[c0:i+1] - ct[i]
        centered = tau - tau.mean()
        ax = float(centered @ speed[c0:i+1] / (centered @ centered))
        try:
            geometry_speed, omega = motion_from_positions(pt[p0:p1+1], xy[p0:p1+1])
        except ValueError:
            reject("unsupported_position_fit")
            continue
        curvature = omega / geometry_speed
        ay, steering = -speed[i] * omega, float(np.arctan(cfg.wheelbase_m * curvature))
        if (not cfg.min_geometry_speed_ratio <= geometry_speed / speed[i] <= cfg.max_geometry_speed_ratio
                or abs(ax) > cfg.max_longitudinal_accel_mps2 or abs(ay) > cfg.max_lateral_accel_mps2
                or abs(omega) > cfg.max_heading_rate_rad_s or abs(steering) > cfg.max_steering_rad):
            reject("unsupported_motion_envelope")
            continue
        dt = float(ct[i] - ct[i-1])
        inputs = TyreEnergyInputs(float(speed[i]), ax, float(ay), steering, float(throttle/100), float(brake), dt,
                                  mass_kg=cfg.mass_kg, wheelbase_m=cfg.wheelbase_m)
        if min(_loads(inputs)) < cfg.min_wheel_normal_load_n:
            reject("wheel_load_requires_projection")
            continue
        energy = estimate_wheel_tyre_energy(inputs).as_array()
        if not np.isfinite(energy).all() or min(energy) < 0:
            raise ValueError("Nonfinite/negative proxy energy")
        if active != segment["segment_id"] or i != previous_native + 1:
            run_number += 1
        active, previous_native = segment["segment_id"], i
        row = {"event_id": event, "session_id": event+"_R_FASTF1", "track_id": segment["track_id"], "driver_id": driver,
               "segment_id": active, "sequence_id": f"{event}_{driver}_{run_number}", "compound":segment["compound"], "sample_id": len(output),
               "lap_number": lap_number, "native_car_row": i, "car_history_start_row": c0,
               "position_history_start_row": int(p0), "native_position_row": int(p1), "time_s": float(time),
               "dt_s": dt, "position_time_s": float(pt[p1]), "position_lag_s": float(time-pt[p1]),
               "speed_kmh": float(car["Speed"].iloc[i]), "throttle_percent": float(throttle), "brake_applied": bool(brake),
               "speed_mps": float(speed[i]), "throttle": float(throttle/100), "longitudinal_accel_mps2": ax,
               "geometry_speed_mps": geometry_speed, "heading_rate_rad_s": omega, "curvature_proxy_inv_m": curvature,
               "lateral_accel_proxy_mps2": float(ay), "steering_rad_proxy": steering, "brake_pressure_proxy": float(brake),
               "mass_prior_kg": cfg.mass_kg, **{k: None for k in UNKNOWN}}
        row.update({f"tyre_energy_{w}_kj": float(v) for w, v in zip(WHEEL_NAMES, energy, strict=True)})
        row.update({f"tyre_power_{w}_kw": float(v/dt) for w, v in zip(WHEEL_NAMES, energy, strict=True)})
        output.append(row)
    return output, rejected


def validate_samples(table: pa.Table) -> dict:
    """Fail closed on schema/labels/nulls/units/lineage arithmetic, without source filling."""
    if not table.schema.equals(sample_schema(), check_metadata=True) or not len(table):
        raise ValueError("Invalid/empty canonical tyre-energy proxy schema")
    frame = table.to_pandas()
    for name, (dtype, _, _) in FIELDS.items():
        if name in UNKNOWN:
            if frame[name].notna().any():
                raise ValueError("Measured wheel quantities must remain UNKNOWN")
        elif frame[name].isna().any() or (pa.types.is_floating(dtype) and not np.isfinite(frame[name]).all()):
            raise ValueError(f"Missing/nonfinite canonical proxy field: {name}")
    if frame.duplicated(["event_id", "driver_id", "native_car_row"]).any():
        raise ValueError("Duplicate proxy source sample")
    if (frame["dt_s"].le(0).any() or frame["position_lag_s"].lt(0).any()
            or not np.allclose(frame["position_lag_s"], frame["time_s"]-frame["position_time_s"], atol=1e-10, rtol=0)
            or (frame["car_history_start_row"] > frame["native_car_row"]).any()
            or (frame["position_history_start_row"] > frame["native_position_row"]).any()
            or frame[["native_car_row","car_history_start_row","native_position_row","position_history_start_row"]].lt(0).any().any()):
        raise ValueError("Invalid proxy timing or lineage")
    for wheel in WHEEL_NAMES:
        energy, power = frame[f"tyre_energy_{wheel}_kj"], frame[f"tyre_power_{wheel}_kw"]
        if energy.lt(0).any() or not np.allclose(energy, power*frame["dt_s"], rtol=1e-12, atol=1e-12):
            raise ValueError("Invalid proxy energy/power units")
    return {"rows": len(table), "fields": len(FIELDS), "truth_labels_complete": True,
            "measured_wheel_targets": 0, "proxy_wheel_targets": 4, "events": sorted(frame.event_id.unique()),
            "sequences": int(frame.sequence_id.nunique())}


def build_tyre_energy_dataset(archives: list[Path], pace_dataset: Path, output: Path) -> dict:
    """Offline five-event public builder; benchmark guards precede archive payloads."""
    if output.exists():
        raise FileExistsError(f"Tyre-energy output already exists: {output}")
    if any(output.resolve().is_relative_to(p.resolve()) for p in [*archives, pace_dataset]):
        raise ValueError("Tyre-energy output must be outside frozen inputs")
    mask = json.loads(pace_dataset.read_text(encoding="utf-8"))
    if mask.get("content_sha256") != payload_sha256({k:v for k,v in mask.items() if k!="content_sha256"}):
        raise ValueError("Eligible tyre-pace dataset hash mismatch")
    if mask.get("schema_version") != "apex-tyre-pace-dataset-v1" or {s["event_id"] for s in mask["sources"]} != set(EVENTS):
        raise ValueError("R024 requires the frozen five-event eligible source mask")
    cfg = ProxyDatasetConfig()
    for segment in mask["segments"]:
        assert_development_event(segment["season"],segment["round_number"],event_id=segment["event_id"])
    source_paths = [Path(__file__), Path(tyre_energy.__file__), pace_dataset]
    before = {str(p):file_sha256(p) for p in source_paths}
    rows, rejections, sources, seen = [], [], [], set()
    for archive in archives:
        metadata = json.loads((archive/"manifest.json").read_text(encoding="utf-8"))
        query = metadata["query"]
        assert_development_event(query["year"], query["round_number"])
        event = f"F1_{query['year']}_R{query['round_number']:02d}"
        if event in seen or event not in EVENTS or query["session"] != "R":
            raise ValueError("Duplicate/unsupported R024 development race")
        seen.add(event)
        manifest = verify_fastf1_archive(archive)
        source = next(s for s in mask["sources"] if s["event_id"] == event)
        if manifest["content_sha256"] != source["archive_sha256"]:
            raise ValueError("Eligible mask/archive source binding mismatch")
        laps = pd.read_parquet(archive/"tables/laps.parquet")
        streams = []
        for driver in cfg.drivers:
            car = pd.read_parquet(archive/f"tables/car_data/{driver}.parquet")
            pos = pd.read_parquet(archive/f"tables/pos_data/{driver}.parquet")
            segments = [s for s in mask["segments"] if s["event_id"] == event and s["driver"] == driver]
            accepted, rejected = canonical_proxy_samples(car, pos, segments, laps, cfg)
            rows.extend(accepted)
            rejections.extend(rejected)
            streams.append({"driver_id":driver, "native_car_rows":len(car), "native_position_rows":len(pos),
                            "accepted_rows":len(accepted), "rejected_rows":len(rejected),
                            "rejection_counts":dict(Counter(r["reason"] for r in rejected))})
        if verify_fastf1_archive(archive)["content_sha256"] != manifest["content_sha256"]:
            raise ValueError("Native source changed during proxy conversion")
        sources.append({"event_id":event, "archive_sha256":manifest["content_sha256"], "query":query,
                        "source_manifest":manifest["source_manifest"], "environment":manifest["environment"], "streams":streams,
                        "native_files":{k:v for k,v in manifest["files"].items() if k=="tables/laps.parquet" or k in
                                        {f"tables/{kind}/{driver}.parquet" for kind in ("car_data","pos_data") for driver in cfg.drivers}}})
    if seen != set(EVENTS):
        raise ValueError("R024 requires all five frozen development events")
    table = pa.Table.from_pylist(rows, schema=sample_schema())
    validation = validate_samples(table)
    frame = table.to_pandas()
    if any(sum(s["accepted_rows"] for s in source["streams"]) < 1000 or any(s["accepted_rows"] == 0 for s in source["streams"]) for source in sources):
        raise ValueError("Frozen R024 public event/driver coverage gate failed")
    if before != {str(p):file_sha256(p) for p in source_paths}:
        raise ValueError("Proxy implementation or input mask changed during conversion")
    distributions = []
    for (event, driver, compound), group in frame.groupby(["event_id","driver_id","compound"],sort=True):
        distributions.append({"event_id":event,"driver_id":driver,"compound":compound,"rows":len(group),
                              "dt_s_quantiles":group.dt_s.quantile([0,.5,.95,1]).tolist(),
                              "position_lag_s_quantiles":group.position_lag_s.quantile([0,.5,.95,1]).tolist(),
                              "energy_kj_mean":{w:float(group[f"tyre_energy_{w}_kj"].mean()) for w in WHEEL_NAMES}})
    # With zero aero and unchanged kinematics, force and load scale with mass;
    # load/mean(load) is unchanged, so R006 energy scales linearly. The 50 N
    # support boundary is checked separately rather than hidden by clipping.
    front = .46*cfg.mass_kg*9.81 - cfg.mass_kg*frame.longitudinal_accel_mps2*.32/cfg.wheelbase_m
    rear = cfg.mass_kg*9.81-front
    transfer = cfg.mass_kg*frame.lateral_accel_proxy_mps2*.32/2.
    minimum_load = np.minimum.reduce([front/2+.46*transfer/2,front/2-.46*transfer/2,
                                      rear/2+.54*transfer/2,rear/2-.54*transfer/2])
    sensitivity = []
    for factor in (.9,1.1):
        supported = minimum_load*factor >= cfg.min_wheel_normal_load_n
        sensitivity.append({"mass_prior_kg":cfg.mass_kg*factor,"energy_scaling":factor,
                            "supported_rows":int(supported.sum()),"unsupported_rows":int((~supported).sum()),
                            "energy_kj_mean_supported":{w:float(frame.loc[supported,f"tyre_energy_{w}_kj"].mean()*factor) for w in WHEEL_NAMES},
                            "scope":"analytic conditional mass sensitivity; kinematics/control/other priors fixed; no projection"})
    quality = {"schema_version":VERSION,"validation":validation,"sources":sources,"distributions":distributions,
               "mass_prior_sensitivity":sensitivity,
               "projection_count":0,"imputed_values":0,"training_ready_for_measured_energy":False,
               "target_quality":"PROXY_NOT_MEASURED","coordinate_convention":"mathematical XY right-handed PRIOR; rightward acceleration positive loads left",
               "limitations":["Retrospective clean-lap mask","Native irregular sampling; no proprietary 0.1 s claim",
                              "Steering/lateral acceleration and wheel energy are proxies","Mass/aero/slip/load parameters are PRIORs",
                              "No ground-truth wheel-energy, wear, forecasting skill or production promotion"]}
    output.mkdir(parents=True, exist_ok=False)
    pq.write_table(table, output/"samples.parquet")
    pq.write_table(pa.Table.from_pylist(rejections), output/"rejections.parquet")
    write_manifest(output/"config.json",{"support_and_vehicle_priors":asdict(cfg),
                   "remaining_vehicle_priors":{k:v for k,v in asdict(TyreEnergyInputs(0,0,0,0,0,0,.1)).items()
                                               if k not in ("speed_mps","longitudinal_accel_mps2","lateral_accel_mps2","steering_rad","throttle","brake","dt_s","mass_kg","wheelbase_m")},
                   "field_truth_labels":{k:label for k,(_,label,_) in FIELDS.items()},"field_units":{k:unit for k,(_,_,unit) in FIELDS.items()}})
    write_manifest(output/"quality.json",quality)
    write_manifest(output/"eligible_input.json",mask)
    commit = subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True,check=True).stdout.strip()
    manifest = {"schema_version":VERSION,"eligible_dataset_sha256":mask["content_sha256"],"commit":commit,
                "benchmark_policy_sha256":file_sha256(Path(__file__).parents[1]/"data/benchmark_policy.json"),
                "implementation_sha256":{p.name:before[str(p)] for p in source_paths[:-1]},
                "environment":{"python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__,"pyarrow":pa.__version__},
                "files":{p.name:{"sha256":file_sha256(p),"bytes":p.stat().st_size} for p in sorted(output.iterdir())}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(output/"manifest.json",manifest)
    return {"manifest_sha256":manifest["content_sha256"],**validation}


def read_tyre_energy_dataset(output: Path) -> tuple[pa.Table, dict]:
    """Portable integrity/label/lineage reload, requiring no original archive cache."""
    manifest = json.loads((output/"manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != VERSION or manifest.get("content_sha256") != payload_sha256({k:v for k,v in manifest.items() if k!="content_sha256"}):
        raise ValueError("Invalid tyre-energy dataset manifest hash/schema")
    required = {"samples.parquet","rejections.parquet","config.json","quality.json","eligible_input.json"}
    if set(manifest["files"]) != required or {p.name for p in output.iterdir()} != required|{"manifest.json"}:
        raise ValueError("Tyre-energy dataset inventory mismatch")
    for name, record in manifest["files"].items():
        if file_sha256(output/name) != record["sha256"] or (output/name).stat().st_size != record["bytes"]:
            raise ValueError(f"Tyre-energy artifact hash mismatch: {name}")
    table = pq.read_table(output/"samples.parquet")
    validation = validate_samples(table)
    quality = json.loads((output/"quality.json").read_text(encoding="utf-8"))
    if quality["validation"] != validation or quality["target_quality"] != "PROXY_NOT_MEASURED":
        raise ValueError("Tyre-energy quality/label mismatch")
    mask = json.loads((output/"eligible_input.json").read_text(encoding="utf-8"))
    if mask["content_sha256"] != manifest["eligible_dataset_sha256"] or mask["content_sha256"] != payload_sha256({k:v for k,v in mask.items() if k!="content_sha256"}):
        raise ValueError("Tyre-energy eligible mask binding mismatch")
    frame, excluded = table.to_pandas(), pq.read_table(output/"rejections.parquet").to_pandas()
    source_pairs={(s["event_id"],d["driver_id"]) for s in quality["sources"] for d in s["streams"]}
    if ({tuple(row) for row in frame[["event_id","driver_id"]].drop_duplicates().to_numpy()} != source_pairs
            or {tuple(row) for row in excluded[["event_id","driver_id"]].drop_duplicates().to_numpy()} != source_pairs
            or excluded.duplicated(["event_id","driver_id","native_car_row"]).any()):
        raise ValueError("Tyre-energy source/driver membership mismatch")
    config=json.loads((output/"config.json").read_text(encoding="utf-8"))
    if (config["field_truth_labels"]!={k:label for k,(_,label,_) in FIELDS.items()}
            or config["field_units"]!={k:unit for k,(_,_,unit) in FIELDS.items()}):
        raise ValueError("Tyre-energy field truth/unit contract mismatch")
    for source in quality["sources"]:
        assert_development_event(source["query"]["year"],source["query"]["round_number"],event_id=source["event_id"])
        for stream in source["streams"]:
            accepted = frame[(frame.event_id==source["event_id"]) & (frame.driver_id==stream["driver_id"])]
            rejected = excluded[(excluded.event_id==source["event_id"]) & (excluded.driver_id==stream["driver_id"])]
            if (len(accepted)!=stream["accepted_rows"] or len(rejected)!=stream["rejected_rows"]
                    or set(accepted.native_car_row)|set(rejected.native_car_row)!=set(range(stream["native_car_rows"]))
                    or set(accepted.native_car_row)&set(rejected.native_car_row)
                    or accepted.native_position_row.ge(stream["native_position_rows"]).any()
                    or accepted.position_history_start_row.lt(0).any()
                    or dict(Counter(rejected.reason))!=stream["rejection_counts"]):
                raise ValueError("Tyre-energy native lineage/exclusion accounting mismatch")
    return table, manifest
