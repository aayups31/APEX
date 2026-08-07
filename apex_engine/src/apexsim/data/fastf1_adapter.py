from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def ingest_fastf1_session(
    year: int,
    event: str,
    session_code: str,
    driver: str,
    output_path: str | Path,
    sample_hz: int = 5,
) -> pd.DataFrame:
    """Fetch a historical FastF1 session and translate it into APEX's canonical contract.

    FastF1 is an optional dependency because the complete project must remain runnable offline.
    """
    try:
        import fastf1
    except ImportError as exc:
        raise RuntimeError(
            "FastF1 is not installed. Install the project with the 'real-data' extra."
        ) from exc

    cache_dir = Path(".cache/fastf1")
    cache_dir.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir))
    session = fastf1.get_session(year, event, session_code)
    session.load(telemetry=True, laps=True, weather=True, messages=False)

    driver_laps = session.laps.pick_drivers(driver)
    rows: list[pd.DataFrame] = []
    weather = session.weather_data.copy()
    if "Time" in weather:
        weather["timestamp_s"] = weather["Time"].dt.total_seconds()

    for _, lap in driver_laps.iterlaps():
        telemetry = lap.get_telemetry().copy()
        if telemetry.empty:
            continue
        telemetry["timestamp_s"] = telemetry["SessionTime"].dt.total_seconds()
        start, end = telemetry.timestamp_s.min(), telemetry.timestamp_s.max()
        regular_time = np.arange(start, end, 1.0 / sample_hz)
        telemetry = telemetry.set_index("timestamp_s").reindex(regular_time).interpolate().ffill().bfill()
        telemetry.index.name = "timestamp_s"
        telemetry = telemetry.reset_index()
        telemetry["lap_number"] = int(lap.LapNumber)
        telemetry["tyre_age_laps"] = float(lap.TyreLife or 0) + (
            telemetry["Distance"] / max(float(telemetry["Distance"].max()), 1.0)
        )
        rows.append(telemetry)

    if not rows:
        raise RuntimeError("FastF1 returned no telemetry for the requested driver/session.")
    tele = pd.concat(rows, ignore_index=True).sort_values("timestamp_s")
    distance = tele["Distance"].fillna(method="ffill").fillna(0.0)
    progress = (distance / max(float(distance.max()), 1.0)) % 1.0
    speed_mps = tele["Speed"].astype(float) / 3.6
    dt = tele.timestamp_s.diff().replace(0, np.nan).fillna(1.0 / sample_hz)
    acceleration = speed_mps.diff().fillna(0.0) / dt
    x = tele.get("X", pd.Series(np.zeros(len(tele)))).astype(float)
    y = tele.get("Y", pd.Series(np.zeros(len(tele)))).astype(float)
    heading = np.unwrap(np.arctan2(np.gradient(y), np.gradient(x)))
    steering = np.clip(np.gradient(heading) * sample_hz / 1.8, -1, 1)
    curvature = np.clip(np.abs(np.gradient(heading)) * 5.0, 0, 1.5)

    canonical = pd.DataFrame(
        {
            "session_id": f"FF1_{year}_{event}_{session_code}",
            "source": "fastf1",
            "track_id": str(event),
            "driver_id": str(driver),
            "timestamp_s": tele.timestamp_s,
            "lap_number": tele.lap_number,
            "speed_mps": speed_mps,
            "acceleration_mps2": acceleration,
            "track_progress_sin": np.sin(2 * np.pi * progress),
            "track_progress_cos": np.cos(2 * np.pi * progress),
            "tyre_age_laps": tele.tyre_age_laps,
            "throttle": tele["Throttle"].astype(float) / 100.0,
            "brake": tele["Brake"].astype(float),
            "gear_norm": tele["nGear"].astype(float).clip(0, 8) / 8.0,
            "drs": (tele["DRS"].astype(float) > 9).astype(float),
            "steering_proxy": steering,
            "curvature": curvature,
            "air_temp_c": 25.0,
            "track_temp_c": 35.0,
            "rainfall": 0.0,
            "wind_speed_mps": 2.0,
            "grip_level": 1.0,
            "lap_distance_m": distance,
            "x_m": x,
            "y_m": y,
            "rpm": tele["RPM"].astype(float),
            "gear": tele["nGear"].astype(int),
            "compound_id": 0,
            "is_pit": 0,
            "safety_car": 0,
        }
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    canonical.to_csv(output, index=False)
    return canonical
