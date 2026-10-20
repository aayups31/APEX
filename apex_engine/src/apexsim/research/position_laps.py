"""R029 source-bound complete position laps; bounded timing anchors only."""
from __future__ import annotations

import numpy as np
import pandas as pd

from apexsim.research.reference_geometry import chord_parameter

EVENT_TRACKS = {"F1_2024_R01": "bahrain", "F1_2024_R16": "monza", "F1_2023_R01": "bahrain", "F1_2023_R14": "monza"}
MASK_SEALS = {
    2024: "d79966d3b13c06cb8a0bd6f6bcff1690a10965d6414e0e71840ecf6d7811d6a2",
    2023: "28f947c68e71c1d97b61b52d3cfcdfed0b30fce801bad3f0ee49136fa61a966d",
}


def position_arrays(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not {"SessionTime", "X", "Y", "Status", "Source"}.issubset(frame):
        raise ValueError("Missing native position fields")
    time = frame.SessionTime.dt.total_seconds().to_numpy(float)
    if not np.isfinite(time).all() or np.any(np.diff(time) <= 0):
        raise ValueError("Native position timestamps must be finite and strictly increasing")
    return time, frame[["X", "Y"]].to_numpy(float)*.1, frame.Source.to_numpy(), frame.Status.to_numpy()


def boundary_position(arrays: tuple, time: float, *, allow_pit_status: bool = False) -> tuple[np.ndarray, tuple[int, int], float]:
    timestamps, xy, source, status = arrays
    right = int(np.searchsorted(timestamps, time))
    left = right if right < len(timestamps) and abs(timestamps[right]-time) < 1e-8 else right-1
    if left < 0 or right >= len(timestamps) or timestamps[right]-timestamps[left] > .75:
        raise ValueError("Unsupported timing boundary bracket; no extrapolation/gap filling")
    indices = [left, right]
    allowed = ("OnTrack", "OffTrack") if allow_pit_status else ("OnTrack",)
    if (not np.isfinite(xy[indices]).all() or any(source[i] != "pos" or status[i] not in allowed for i in indices)):
        raise ValueError("Timing boundary lacks supported native position samples")
    weight = 0. if left == right else (time-timestamps[left])/(timestamps[right]-timestamps[left])
    return xy[left]*(1-weight)+xy[right]*weight, (left, right), float(weight)


def extract_position_lap(laps: pd.DataFrame, positions: pd.DataFrame, selection: dict, *, allow_interior_gaps: bool = False) -> dict:
    """Extract native vertices; v2 optionally retains explicit unsupported interior intervals.

    Timing-anchor support, native quality, identity and closure rules never change.
    The default remains the frozen v1 complete-lap policy.
    """
    row = laps.iloc[selection["native_row"]]
    if str(row.DriverNumber) != selection["driver_id"] or int(row.LapNumber) != selection["lap_number"]:
        raise ValueError("Selected lap/native row identity mismatch")
    if (pd.isna(row.IsAccurate) or not bool(row.IsAccurate) or pd.isna(row.Deleted) or bool(row.Deleted)
            or row.TrackStatus != "1" or row.Compound not in ("SOFT", "MEDIUM", "HARD")
            or pd.notna(row.PitInTime) or pd.notna(row.PitOutTime)):
        raise ValueError("Selected lap no longer meets frozen clean-dry eligibility")
    start, end, duration = (row[name].total_seconds() if pd.notna(row[name]) else np.nan
                            for name in ("LapStartTime", "Time", "LapTime"))
    if not np.isfinite([start, end, duration]).all() or duration <= 0 or abs(end-start-duration) > .1:
        raise ValueError("Unsupported native lap timing consistency")
    arrays = position_arrays(positions)
    timestamps, xy, source, status = arrays
    first, first_parents, first_weight = boundary_position(arrays, start)
    last, last_parents, last_weight = boundary_position(arrays, end)
    indices = np.flatnonzero((timestamps > start+1e-8)&(timestamps < end-1e-8))
    if len(indices) < 100 or any(source[i] != "pos" or status[i] != "OnTrack" for i in indices):
        raise ValueError("Selected lap needs >=100 supported native OnTrack position rows")
    times = np.r_[start, timestamps[indices], end]
    points = np.vstack((first, xy[indices], last))
    interval_supported = np.diff(times) <= .75
    if not np.isfinite(points).all() or (not allow_interior_gaps and not interval_supported.all()):
        raise ValueError("Selected position lap has unsupported samples/gaps")
    raw_gap = float(np.linalg.norm(points[-1]-points[0]))
    if raw_gap > 30:
        raise ValueError("Selected raw position lap fails30m endpoint closure")
    _, raw_length = chord_parameter(points)
    sectors = []
    for name in ("Sector1Time", "Sector2Time"):
        value = row.get(name)
        sectors.append(float(value.total_seconds()) if pd.notna(value) else None)
    result = {"xy_m": points, "time_s": times,
            "native_parents": np.vstack((first_parents, np.column_stack((indices, indices)), last_parents)).astype(np.int64),
            "metadata": {**selection, "lap_id": f"{selection['event_id']}_{selection['driver_id']}_{selection['lap_number']}",
                         "lap_start_s": start, "lap_end_s": end, "native_samples": len(indices), "boundary_samples": 2,
                         "boundary_weights": [first_weight, last_weight], "raw_closure_gap_m": raw_gap,
                         "raw_chord_length_m": raw_length, "max_gap_s": float(np.diff(times).max()),
                         "sector_durations_s": sectors, "position_scale_m_per_unit": .1,
                         "boundary_truth": "BOUNDED_LINEAR_RECONSTRUCTION_FROM_NATIVE_POS",
                         "native_truth": "FASTF1_PARSED_SOURCE; upstream reconstruction possible"}}
    if allow_interior_gaps:
        result["interval_supported"] = interval_supported
        result["metadata"].update(
            interval_policy="V2_NATIVE_VERTICES_WITH_EXPLICIT_UNSUPPORTED_INTERVALS",
            chord_phase_truth="RECONSTRUCTED_CHORD_PARAMETER; lower-bound distance across missing intervals",
            unsupported_intervals=[{"left_vertex": int(i), "right_vertex": int(i+1),
                                    "start_s": float(times[i]), "end_s": float(times[i+1]),
                                    "gap_s": float(times[i+1]-times[i]),
                                    "endpoint_chord_m": float(np.linalg.norm(points[i+1]-points[i]))}
                                   for i in np.flatnonzero(~interval_supported)])
    return result
