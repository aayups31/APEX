from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import requests

from apexsim.data.manifest import SourceManifest

BASE_URL = "https://api.openf1.org/v1"


def _get(endpoint: str, params: dict[str, int | str], timeout: int = 60) -> list[dict]:
    response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list from OpenF1 {endpoint}, got {type(payload).__name__}")
    return payload


def ingest_openf1_session(
    session_key: int,
    driver_number: int,
    output_path: str | Path,
    sample_hz: int = 4,
    manifest_path: str | Path | None = None,
) -> pd.DataFrame:
    """Translate OpenF1 car/location/weather streams into the canonical frame.

    Historical OpenF1 data is rich but the endpoints are sampled independently. We therefore align
    streams on time instead of assuming row N in one endpoint matches row N in another.
    """
    output = Path(output_path)
    source_manifest_path = Path(manifest_path) if manifest_path else output.with_suffix(f"{output.suffix}.source.json")
    if output.exists() or source_manifest_path.exists():
        raise FileExistsError(f"OpenF1 output or source manifest already exists: {output}")

    car_query = {"session_key": session_key, "driver_number": driver_number}
    weather_query = {"session_key": session_key}
    car_payload = _get("car_data", car_query)
    location_payload = _get("location", car_query)
    weather_payload = _get("weather", weather_query)
    car = pd.DataFrame(car_payload)
    location = pd.DataFrame(location_payload)
    weather = pd.DataFrame(weather_payload)
    if car.empty or location.empty:
        raise RuntimeError("OpenF1 returned no car or location data for the request.")

    for frame in (car, location, weather):
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
    car = car.sort_values("date")
    location = location.sort_values("date")
    weather = weather.sort_values("date")
    merged = pd.merge_asof(car, location, on="date", direction="nearest", tolerance=pd.Timedelta("1s"))
    merged = pd.merge_asof(merged, weather, on="date", direction="nearest", tolerance=pd.Timedelta("20s"), suffixes=("", "_weather"))
    merged = merged.dropna(subset=["speed", "x", "y"])
    start = merged.date.min()
    merged["timestamp_s"] = (merged.date - start).dt.total_seconds()
    regular_time = np.arange(0, merged.timestamp_s.max(), 1.0 / sample_hz)
    numeric = merged.select_dtypes(include=[np.number]).drop(columns=["timestamp_s"], errors="ignore").copy()
    numeric.index = merged.timestamp_s
    numeric = numeric[~numeric.index.duplicated()].reindex(regular_time).interpolate().ffill().bfill()
    numeric.index.name = "timestamp_s"
    numeric = numeric.reset_index()

    speed_mps = numeric["speed"] / 3.6
    dt = numeric.timestamp_s.diff().replace(0, np.nan).fillna(1.0 / sample_hz)
    accel = speed_mps.diff().fillna(0.0) / dt
    x, y = numeric["x"], numeric["y"]
    heading = np.unwrap(np.arctan2(np.gradient(y), np.gradient(x)))
    curvature = np.clip(np.abs(np.gradient(heading)) * 5.0, 0, 1.5)
    distance = np.cumsum(speed_mps.to_numpy() / sample_hz)
    track_length = max(float(np.quantile(distance, 0.99)), 1.0)
    progress = (distance / track_length) % 1.0

    canonical = pd.DataFrame(
        {
            "session_id": f"OF1_{session_key}",
            "source": "openf1",
            "track_id": f"session_{session_key}",
            "driver_id": str(driver_number),
            "timestamp_s": numeric.timestamp_s,
            "lap_number": (distance // track_length + 1).astype(int),
            "speed_mps": speed_mps,
            "acceleration_mps2": accel,
            "track_progress_sin": np.sin(2 * np.pi * progress),
            "track_progress_cos": np.cos(2 * np.pi * progress),
            "tyre_age_laps": distance / track_length,
            "throttle": numeric.get("throttle", pd.Series(np.zeros(len(numeric)))) / 100.0,
            "brake": numeric.get("brake", pd.Series(np.zeros(len(numeric)))).clip(0, 1),
            "gear_norm": numeric.get("n_gear", pd.Series(np.ones(len(numeric)))) / 8.0,
            "drs": numeric.get("drs", pd.Series(np.zeros(len(numeric)))).clip(0, 1),
            "steering_proxy": np.clip(np.gradient(heading) * sample_hz / 1.8, -1, 1),
            "curvature": curvature,
            "air_temp_c": numeric.get("air_temperature", pd.Series(np.full(len(numeric), 25.0))),
            "track_temp_c": numeric.get("track_temperature", pd.Series(np.full(len(numeric), 35.0))),
            "rainfall": numeric.get("rainfall", pd.Series(np.zeros(len(numeric)))).clip(0, 1),
            "wind_speed_mps": numeric.get("wind_speed", pd.Series(np.full(len(numeric), 2.0))),
            "grip_level": 1.0,
            "lap_distance_m": distance % track_length,
            "x_m": x,
            "y_m": y,
            "rpm": numeric.get("rpm", pd.Series(np.full(len(numeric), 9000.0))),
            "gear": numeric.get("n_gear", pd.Series(np.ones(len(numeric)))).astype(int),
            "compound_id": 0,
            "is_pit": 0,
            "safety_car": 0,
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    canonical.to_csv(output, index=False)
    manifest = SourceManifest(
        source="openf1",
        query={"session_key": session_key, "driver_number": driver_number, "sample_hz": sample_hz},
        terms_url="https://creativecommons.org/licenses/by-nc-sa/4.0/",
        license_id="CC-BY-NC-SA-4.0",
    )
    manifest.add_request(f"{BASE_URL}/car_data", car_query, car_payload, len(car_payload))
    manifest.add_request(f"{BASE_URL}/location", car_query, location_payload, len(location_payload))
    manifest.add_request(f"{BASE_URL}/weather", weather_query, weather_payload, len(weather_payload))
    manifest.add_file(output, rows=len(canonical), role="derived_canonical")
    manifest.save(source_manifest_path)
    return canonical
