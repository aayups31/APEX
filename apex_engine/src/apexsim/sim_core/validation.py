from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SimulationQualityReport:
    telemetry_rows: int
    cars: int
    duplicate_car_times: int
    negative_speed_rows: int
    negative_fuel_rows: int
    invalid_battery_rows: int
    invalid_tyre_health_rows: int
    backward_distance_steps: int
    backward_time_steps: int
    backward_lap_steps: int
    invalid_position_rows: int
    invalid_control_rows: int
    conflicting_terminal_rows: int
    finite_numeric: bool
    passed: bool

    def to_dict(self) -> dict:
        return asdict(self)


def validate_simulation_telemetry(
    frame: pd.DataFrame,
    expected_cars: int | None = None,
    battery_capacity_mj: float | None = None,
) -> SimulationQualityReport:
    required = {
        "time_s",
        "car_id",
        "position",
        "total_distance_m",
        "speed_mps",
        "fuel_kg",
        "battery_mj",
        "tyre_health",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Simulation telemetry missing columns: {sorted(missing)}")
    cars = int(frame.car_id.nunique())
    duplicate = int(frame.duplicated(["car_id", "time_s"]).sum())
    negative_speed = int((frame.speed_mps < -1e-9).sum())
    negative_fuel = int((frame.fuel_kg < -1e-9).sum())
    invalid_battery_mask = frame.battery_mj < -1e-9
    if battery_capacity_mj is not None:
        invalid_battery_mask |= frame.battery_mj > battery_capacity_mj + 1e-9
    invalid_battery = int(invalid_battery_mask.sum())
    invalid_health = int(((frame.tyre_health < 0.0) | (frame.tyre_health > 1.0)).sum())
    sorted_frame = frame.sort_values(["car_id", "time_s"])
    deltas = sorted_frame.groupby("car_id").total_distance_m.diff()
    backward = int((deltas < -1e-6).sum())
    time_deltas = frame.groupby("car_id", sort=False).time_s.diff()
    backward_time = int((time_deltas <= 0.0).sum())
    backward_lap = 0
    if "lap" in sorted_frame:
        lap_deltas = sorted_frame.groupby("car_id").lap.diff()
        backward_lap = int((lap_deltas < 0).sum())
    invalid_position = int(((frame.position < 1) | (frame.position > max(cars, 1))).sum())
    invalid_controls = 0
    if {"throttle", "brake"}.issubset(frame.columns):
        invalid_controls = int(((frame.throttle > 0.2) & (frame.brake > 0.2)).sum())
    terminal_conflicts = 0
    if {"finished", "retired"}.issubset(frame.columns):
        terminal_conflicts = int(((frame.finished > 0) & (frame.retired > 0)).sum())
    core_numeric_columns = [
        "time_s", "position", "total_distance_m", "speed_mps",
        "fuel_kg", "battery_mj", "tyre_health"
    ]
    finite = bool(np.isfinite(frame[core_numeric_columns].to_numpy()).all())
    passed = all(
        [
            duplicate == 0,
            negative_speed == 0,
            negative_fuel == 0,
            invalid_battery == 0,
            invalid_health == 0,
            backward == 0,
            backward_time == 0,
            backward_lap == 0,
            invalid_position == 0,
            invalid_controls == 0,
            terminal_conflicts == 0,
            finite,
            expected_cars is None or cars == expected_cars,
        ]
    )
    return SimulationQualityReport(
        telemetry_rows=len(frame),
        cars=cars,
        duplicate_car_times=duplicate,
        negative_speed_rows=negative_speed,
        negative_fuel_rows=negative_fuel,
        invalid_battery_rows=invalid_battery,
        invalid_tyre_health_rows=invalid_health,
        backward_distance_steps=backward,
        backward_time_steps=backward_time,
        backward_lap_steps=backward_lap,
        invalid_position_rows=invalid_position,
        invalid_control_rows=invalid_controls,
        conflicting_terminal_rows=terminal_conflicts,
        finite_numeric=finite,
        passed=passed,
    )


def assert_simulation_quality(report: SimulationQualityReport) -> None:
    """Fail at the simulation boundary with the complete invariant report."""
    if report.passed:
        return
    failures = {
        key: value
        for key, value in report.to_dict().items()
        if key not in {"telemetry_rows", "cars", "finite_numeric", "passed"} and value
    }
    if not report.finite_numeric:
        failures["finite_numeric"] = False
    raise RuntimeError(f"Simulation invariants failed: {failures}")


def derive_lap_table(frame: pd.DataFrame, total_laps: int) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["car_id", "driver_id", "lap", "lap_time_s", "max_speed_mps", "compound"])
    records: list[dict] = []
    for car_id, car in frame.sort_values("time_s").groupby("car_id"):
        car = car.copy()
        # Detect lap transitions from the simulator's current-lap counter.
        lap_start_time = float(car.time_s.iloc[0])
        previous_lap = int(car.lap.iloc[0])
        for _, row in car.iloc[1:].iterrows():
            current_lap = int(row.lap)
            if current_lap > previous_lap:
                lap_rows = car[(car.time_s >= lap_start_time) & (car.time_s <= row.time_s)]
                completed = min(previous_lap, total_laps)
                if completed >= 1:
                    records.append(
                        {
                            "car_id": car_id,
                            "driver_id": str(row.driver_id),
                            "lap": completed,
                            "lap_time_s": float(row.time_s - lap_start_time),
                            "max_speed_mps": float(lap_rows.speed_mps.max()),
                            "mean_speed_mps": float(lap_rows.speed_mps.mean()),
                            "compound": str(lap_rows.tyre_compound.mode().iloc[0]),
                            "rain_mean": float(lap_rows.rain_intensity.mean()),
                            "flagged_fraction": float((lap_rows.flag != "GREEN").mean()),
                        }
                    )
                lap_start_time = float(row.time_s)
                previous_lap = current_lap
    return pd.DataFrame(records)


def derive_stint_table(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["car_id", "stint", "compound", "start_lap", "end_lap"])
    records: list[dict] = []
    for car_id, car in frame.sort_values("time_s").groupby("car_id"):
        car = car.copy()
        compound_change = car.tyre_compound.ne(car.tyre_compound.shift()).cumsum()
        for stint, group in car.groupby(compound_change):
            records.append(
                {
                    "car_id": car_id,
                    "driver_id": str(group.driver_id.iloc[0]),
                    "stint": int(stint),
                    "compound": str(group.tyre_compound.iloc[0]),
                    "start_lap": int(group.lap.min()),
                    "end_lap": int(group.lap.max()),
                    "start_time_s": float(group.time_s.min()),
                    "end_time_s": float(group.time_s.max()),
                    "distance_m": float(group.total_distance_m.max() - group.total_distance_m.min()),
                    "tyre_health_end": float(group.tyre_health.iloc[-1]),
                }
            )
    return pd.DataFrame(records)
