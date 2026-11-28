"""Run the R041 external, cross-session masked tyre-temperature pilot."""

import argparse
from pathlib import Path
from statistics import mean, median

import numpy as np
import pandas as pd
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import check_seal, read_json, seal
from apexsim.research.tyre_thermal import ThermalState, heat_step
from archive_stanford_tyre_runs import files
from confirm_compound_multiseason import canonical_file_sha
from prepare_compound_pit_exit import BASE
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

PROTOCOL = BASE / "research/protocols/COMPOUND_EXTERNAL_THERMAL_V34.md"
STEP = 0.25
WHEELS = ("fl", "fr", "rl", "rr")
TARGETS = tuple(f"tireTemp_{wheel}_degC" for wheel in WHEELS)
CONTROL_COLUMNS = (
    "Ve_mps",
    "Vn_mps",
    "throttleCmd_percent",
    "engine_rpm",
    "brake_fl_bar",
    "posE_m",
    "posN_m",
)
ARMS = ("time_only", "public_controls", "two_node_heat", "hybrid")


def intervals(clock, controls):
    """Return contiguous input grids with a causal zero-order hold."""
    if len(clock) < 2 or not np.isfinite(clock).all() or np.any(np.diff(clock) <= 0):
        raise ValueError("External telemetry clock must be strictly ordered")
    grid = np.arange(np.ceil(clock[0] / STEP), np.floor(clock[-1] / STEP) + 1) * STEP
    latest = np.searchsorted(clock, grid, side="right") - 1
    supported = (grid - clock[latest] <= 0.1) & np.isfinite(controls[latest]).all(axis=1)
    positions = np.flatnonzero(supported)
    groups = np.split(positions, np.flatnonzero(np.diff(positions) > 1) + 1)
    return [latest[group] for group in groups if len(group) > 15 / STEP]


def view(controls):
    """Derive public-compatible features without taking a sensor target."""
    east_speed, north_speed, throttle, rpm, brake, east, north = controls.T
    speed = np.hypot(east_speed, north_speed)
    dx, dy = np.diff(east), np.diff(north)
    heading = np.unwrap(np.arctan2(dy, dx))
    moving_vectors = np.hypot(dx, dy) >= 0.5
    ax = np.clip(np.diff(speed, prepend=speed[0]) / STEP, -30, 30)
    ay = np.zeros_like(speed)
    ay[2:] = np.clip(speed[2:] * np.diff(heading) / STEP, -30, 30) * moving_vectors[1:] * moving_vectors[:-1]
    public = np.column_stack(
        (speed, throttle / 100, rpm / 1000, brake > 5, np.abs(ax), np.maximum(ay, 0), np.maximum(-ay, 0))
    )
    age = np.arange(len(speed)) * STEP
    timing = np.column_stack((age / 120, -np.expm1(-age / 15), -np.expm1(-age / 60)))
    smooth = np.empty((len(speed), 2, public.shape[1]))
    smooth[0] = public[0]
    weights = -np.expm1(-STEP / np.array([10.0, 40.0]))[:, None]
    thermal = np.zeros((len(speed), 2))
    boundary = 298.15
    state = ThermalState(boundary, boundary)
    heat = 30 * speed * (np.abs(ax) + np.abs(ay))
    for i in range(1, len(speed)):
        smooth[i] = smooth[i - 1] + weights * (public[i] - smooth[i - 1])
        state = heat_step(
            state,
            STEP,
            tread_w=heat[i - 1],
            carcass_w=0,
            road_k=boundary,
            air_k=boundary,
        ).state
        thermal[i] = (state.tread_k - boundary, state.carcass_k - boundary)
    controls_history = np.column_stack((public, smooth.reshape(len(speed), -1)))
    return (
        speed,
        age,
        {
            "time_only": timing,
            "public_controls": np.column_stack((timing, controls_history)),
            "two_node_heat": np.column_stack((timing, thermal)),
            "hybrid": np.column_stack((timing, controls_history, thermal)),
        },
    )


def prepare_run(path):
    frame = pd.read_csv(path, comment="#", usecols=["t_s", "s_m", *CONTROL_COLUMNS, *TARGETS])
    clock = frame["t_s"].to_numpy(float)
    controls = frame.loc[:, list(CONTROL_COLUMNS)].to_numpy(float)
    temperatures = frame.loc[:, list(TARGETS)].to_numpy(float)
    segments = []
    for indexes in intervals(clock, controls):
        speed, age, predictors = view(controls[indexes])
        targets = temperatures[indexes]
        valid = ((targets >= -30) & (targets <= 140)).all(axis=1)
        keep = (age >= 15) & (speed >= 5) & valid
        if keep.any():
            segments.append(({k: v[keep] for k, v in predictors.items()}, targets[keep]))
    # Large forward wraps are a duration diagnostic and do not establish stint boundaries.
    progress = frame["s_m"].to_numpy(float)
    wraps = int(np.count_nonzero(np.diff(progress) < -1000))
    return segments, {
        "raw_rows": len(frame),
        "duration_s": float(clock[-1] - clock[0]),
        "track_progress_wraps": wraps,
        "scored_samples": sum(len(y) for _, y in segments),
        "scored_segments": len(segments),
    }


def transfer(train, test):
    scores = {
        name: {}
        for name in (*ARMS, "hybrid_with_measured_initial_temperature", "measured_initial_persistence")
    }
    for arm in ARMS:
        rows = [segment for segments in train.values() for segment in segments]
        x = np.concatenate([a[arm] for a, _ in rows])
        y = np.concatenate([b for _, b in rows])
        scaler = StandardScaler().fit(x)
        fit = Ridge(alpha=10).fit(scaler.transform(x), y)
        for run, segments in test.items():
            errors, initialized, initial_persistence = [], [], []
            for predictors, target in segments:
                predicted = fit.predict(scaler.transform(predictors[arm]))
                errors.append(np.abs(predicted - target))
                if arm == "hybrid" and len(target) > 1:
                    corrected = predicted[1:] - predicted[0] + target[0]
                    initialized.append(np.abs(corrected - target[1:]))
                    initial_persistence.append(np.abs(target[0] - target[1:]))
            scores[arm][run] = errors
            if initialized:
                scores["hybrid_with_measured_initial_temperature"][run] = initialized
                scores["measured_initial_persistence"][run] = initial_persistence
    result = {}
    for name, runs in scores.items():
        metrics = {}
        for run, segments in runs.items():
            values = np.concatenate(segments)
            metrics[run] = {
                "samples": len(values),
                "mae_c": float(values.mean()),
                "median_absolute_error_by_wheel_c": dict(
                    zip(WHEELS, np.median(values, axis=0).tolist(), strict=True)
                ),
            }
        result[name] = {
            "equal_run_mae_c": mean(run["mae_c"] for run in metrics.values()),
            "median_run_error_by_wheel_c": {
                w: median(run["median_absolute_error_by_wheel_c"][w] for run in metrics.values())
                for w in WHEELS
            },
            "runs": metrics,
        }
    result["hybrid_wins_against_time"] = sum(
        result["hybrid"]["runs"][r]["mae_c"] < result["time_only"]["runs"][r]["mae_c"] for r in test
    )
    return result


def run(root):
    inventory = read_json(root / "manifest.json")
    check_seal(inventory)
    if inventory["catalog_sha256"] != file_sha256(root / "catalog.json"):
        raise ValueError("Stanford metadata differs from the acquired inventory")
    plan = list(files(read_json(root / "catalog.json")))
    if len(plan) != 20 or set(inventory["runs"]) != {Path(filename).name for filename, _, _ in plan}:
        raise ValueError("Stanford archives are incomplete")
    telemetry, support = {"Oct2023": {}, "Nov2023": {}}, {}
    for filename, size, digest in plan:
        _, session, name = filename.split("/")
        path = root / name
        receipt = inventory["runs"][name]
        if (
            path.stat().st_size != size
            or receipt["publisher_sha1"] != digest
            or file_sha256(path) != receipt["sha256"]
        ):
            raise ValueError(f"Stanford archive changed: {name}")
        segments, support[name] = prepare_run(path)
        if segments:
            telemetry[session][name] = segments
    if not all(telemetry.values()):
        raise ValueError("No eligible evaluation runs in a Stanford session")
    scores = {
        "october_to_november": transfer(telemetry["Oct2023"], telemetry["Nov2023"]),
        "november_to_october": transfer(telemetry["Nov2023"], telemetry["Oct2023"]),
    }
    gates = {
        direction: {
            "lower_than_time": m["hybrid"]["equal_run_mae_c"] < m["time_only"]["equal_run_mae_c"],
            "majority_run_improvement": m["hybrid_wins_against_time"] * 2 > len(m["time_only"]["runs"]),
            "lower_than_controls": m["hybrid"]["equal_run_mae_c"] < m["public_controls"]["equal_run_mae_c"],
        }
        for direction, m in scores.items()
    }
    return seal(
        {
            "schema": "compound-external-thermal-v34",
            "archive_sha256": inventory["content_sha256"],
            "protocol_sha256_lf": canonical_file_sha(PROTOCOL),
            "source_sha256_lf": canonical_file_sha(Path(__file__)),
            "runs": support,
            "transfers": scores,
            "gates": gates,
            "masked_temperature_gate_passed": all(all(gate.values()) for gate in gates.values()),
            "r041_development_qualified": False,
            "three_lap_pace_oracle_scored": False,
            "production_promotion": False,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output, run(args.archive))
