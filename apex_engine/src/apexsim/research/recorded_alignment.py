"""R033 native observed-state/control alignment; missing model states stay UNKNOWN."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from apexsim.data.benchmark_guard import assert_development_event
from apexsim.research.longitudinal_data import DRS_STATES, EVENT_ROLES, EVENT_TRACKS

UNKNOWN_FIELDS = ("steering_rad", "body_vx_mps", "body_vy_mps", "yaw_rate_radps", "fuel_kg", "battery_mj")


def native_times(frame: pd.DataFrame) -> np.ndarray:
    """Check parsed SessionTime against Date increments; do not fit clock offsets."""
    t = frame.SessionTime.dt.total_seconds().to_numpy(float)
    dates = pd.DatetimeIndex(frame.Date)
    if (not np.isfinite(t).all() or dates.isna().any() or len(t) < 2 or np.any(np.diff(t) <= 0)
            or not np.allclose(np.diff(t), np.diff(dates.as_unit("ns").asi8)/1e9, rtol=0, atol=1e-6)):
        raise ValueError("R033 native SessionTime/Date clocks invalid or inconsistent")
    return t


def _numeric(frame: pd.DataFrame, field: str) -> np.ndarray:
    values = frame[field] if field in frame else pd.Series(np.nan, index=frame.index)
    return pd.to_numeric(values, errors="coerce").to_numpy(dtype=float, na_value=np.nan)


def align_lap(car: pd.DataFrame, position: pd.DataFrame, lap: dict,
               geometry: dict[str, np.ndarray] | None = None) -> tuple[pd.DataFrame, dict]:
    """Align all lap car rows to backward same-lap native positions without filling.

    Source row IDs address original table order. Native clocks must be ordered;
    arbitrary sorting/deduplication or nearest/future position matches are forbidden.
    """
    event, driver = lap["event_id"], lap["driver_id"]
    assert_development_event(int(event[3:7]), int(event[-2:]), event_id=event)
    if event not in EVENT_ROLES or driver not in ("4", "44") or lap["track_id"] != EVENT_TRACKS[event]:
        raise ValueError("R033 frozen event/track/driver identity mismatch")
    start, end = float(lap["lap_start_s"]), float(lap["lap_end_s"])
    if not np.isfinite([start, end]).all() or start >= end:
        raise ValueError("R033 invalid frozen lap interval")
    ct, pt = native_times(car), native_times(position)
    ci = np.flatnonzero((ct >= start) & (ct < end))
    pi = np.flatnonzero((pt >= start) & (pt < end))
    if not len(ci):
        raise ValueError("R033 frozen lap has no native car rows")
    c = car.iloc[ci]
    speed, throttle = _numeric(c, "Speed")/3.6, _numeric(c, "Throttle")/100
    rpm, gear, drs = (_numeric(c, k) for k in ("RPM", "nGear", "DRS"))
    source = c.Source.to_numpy() == "car"
    raw_brake = c.Brake.to_numpy() if "Brake" in c else np.full(len(c), None)
    brake_valid = np.array([isinstance(v, (bool, np.bool_)) for v in raw_brake])
    brake = pd.array([bool(v) if valid else pd.NA for v, valid in zip(raw_brake, brake_valid, strict=True)], dtype="boolean")
    speed_valid = source & np.isfinite(speed) & (speed >= 0) & (speed <= 120)
    throttle_valid = np.isfinite(throttle) & (throttle >= 0) & (throttle <= 1)
    drs_valid = np.isin(drs, list(DRS_STATES))
    controls = source & throttle_valid & brake_valid & drs_valid
    engine = (source & np.isfinite(rpm) & (rpm >= 0) & (rpm <= 30000) & (rpm == np.floor(rpm))
              & np.isfinite(gear) & (gear >= 0) & (gear <= 8) & (gear == np.floor(gear)))
    n = len(ci)
    selected = np.full(n, -1, dtype=np.int64)
    age, gap, x, y = [np.full(n, np.nan) for _ in range(4)]
    pos_ready = np.zeros(n, dtype=bool)
    reason = np.full(n, "no_same_lap_position", dtype=object)
    if len(pi):
        local = np.searchsorted(pt[pi], ct[ci], side="right")-1
        has = local >= 0
        selected[has] = pi[local[has]]
        age[has] = ct[ci[has]]-pt[selected[has]]
        previous = local >= 1
        gap[previous] = pt[pi[local[previous]]]-pt[pi[local[previous]-1]]
        px, py = _numeric(position, "X"), _numeric(position, "Y")
        pos_source = position.Source.to_numpy() == "pos"
        status = position.Status.to_numpy() if "Status" in position else np.full(len(position), None)
        for i in np.flatnonzero(has):
            j = selected[i]
            if local[i] < 1:
                reason[i] = "no_same_lap_position_predecessor"
            elif age[i] > .35+1e-9:
                reason[i] = "position_age_exceeds_limit"
            elif gap[i] > .75+1e-9:
                reason[i] = "position_previous_gap_exceeds_limit"
            elif not pos_source[j] or status[j] != "OnTrack" or not np.isfinite([px[j], py[j]]).all():
                reason[i] = "unsupported_native_position"
            else:
                reason[i] = "supported"
                pos_ready[i] = True
                x[i], y[i] = px[j]*.1, py[j]*.1
    joint = controls & engine & speed_valid & pos_ready
    covered = np.zeros(n)
    dt = np.diff(ct[ci])
    valid_interval = joint[:-1] & speed_valid[1:] & (dt <= .5+1e-9)
    covered[:-1] = np.where(valid_interval, dt, 0.)
    frame = pd.DataFrame({"event_id": event, "driver_id": driver, "track_id": lap["track_id"],
                          "lap_id": lap["lap_id"], "lap_number": int(lap["lap_number"]), "role": EVENT_ROLES[event],
                          "source_car_row": ci, "session_time_s": ct[ci], "lap_elapsed_s": ct[ci]-start,
                          "sample_utc": pd.to_datetime(c.Date.to_numpy(), utc=True), "speed_mps": speed,
                          "throttle": throttle, "brake_on": brake, "raw_drs": drs, "rpm": rpm, "gear": gear,
                          "drs_open": pd.array([DRS_STATES[v] if valid else pd.NA for v, valid in zip(drs, drs_valid, strict=True)], dtype="Int64"),
                          "position_candidate_row": pd.array([int(j) if j >= 0 else pd.NA for j in selected], dtype="Int64"),
                          "position_source_row": pd.array([int(j) if valid else pd.NA for j, valid in zip(selected, pos_ready, strict=True)], dtype="Int64"),
                          "position_age_s": age, "position_previous_gap_s": gap, "x_m": x, "y_m": y,
                          "controls_observed": controls, "engine_observed": engine, "speed_observed": speed_valid,
                          "position_observed": pos_ready, "position_status": reason, "joint_observed_ready": joint,
                          "covered_interval_s": covered, "full_bicycle_ready": np.zeros(n, dtype=bool)})
    frame["reference_curvature_1pm"] = np.nan
    frame["reference_projection_error_m"] = np.nan
    if geometry is not None:
        parents = geometry["native_parents"]
        lookup = {int(pair[0]): i for i, pair in enumerate(parents) if pair[0] == pair[1]}
        for i in np.flatnonzero(pos_ready):
            key = lookup.get(int(selected[i]))
            if key is not None:
                frame.loc[i, "reference_curvature_1pm"] = float(geometry["curvature_1pm"][key])
                frame.loc[i, "reference_projection_error_m"] = float(geometry["distance_m"][key])
    for field in UNKNOWN_FIELDS:
        frame[field] = pd.array([pd.NA]*n, dtype="Float64")
    frame["rejection_reasons"] = [";".join(label for label, valid in (
        ("unsupported_controls", controls[i]), ("unsupported_engine_observations", engine[i]),
        ("unsupported_speed", speed_valid[i]), (str(reason[i]), pos_ready[i])) if not valid) for i in range(n)]
    metrics = {"lap_id": lap["lap_id"], "event_id": event, "driver_id": driver, "role": EVENT_ROLES[event],
               "native_car_rows": n, "controls_observed_rows": int(controls.sum()), "engine_observed_rows": int(engine.sum()),
               "position_observed_rows": int(pos_ready.sum()), "joint_observed_rows": int(joint.sum()),
               "joint_row_coverage": float(joint.mean()), "lap_duration_s": end-start,
               "covered_interval_s": float(covered.sum()), "joint_interval_coverage": float(covered.sum()/(end-start)),
               "future_position_matches": int((age[pos_ready] < -1e-9).sum()), "full_bicycle_ready_rows": 0,
               "maximum_accepted_position_age_s": float(max(age[pos_ready])) if pos_ready.any() else None,
               "maximum_accepted_position_gap_s": float(max(gap[pos_ready])) if pos_ready.any() else None,
               "position_rejection_counts": {str(k): int(v) for k, v in pd.Series(reason[~pos_ready]).value_counts().items()}}
    return frame, metrics


@dataclass(frozen=True)
class RecordedLongitudinalInputs:
    """Recorded controls/times plus observed initial speed; no future target speeds."""

    section_id: str
    initial_speed_mps: float
    time_s: np.ndarray
    throttle: np.ndarray
    drs_open: np.ndarray
    source_car_rows: np.ndarray


def longitudinal_inputs(frame: pd.DataFrame, source_rows: np.ndarray, section_id: str) -> RecordedLongitudinalInputs:
    """Build causal R030-domain inputs from aligned rows; future speed is not consumed."""
    rows = np.asarray(source_rows)
    if rows.ndim != 1 or rows.dtype.kind not in "iu" or len(rows) < 5 or np.any(np.diff(rows) != 1):
        raise ValueError("R033 section must reference contiguous native car row IDs")
    selected = frame.set_index("source_car_row").reindex(rows)
    if (selected.lap_id.nunique() != 1 or not selected.joint_observed_ready.fillna(False).all()
            or selected.brake_on.fillna(True).any() or not selected.throttle.between(.98, 1).all()
            or selected.drs_open.isna().any() or selected.drs_open.nunique() != 1):
        raise ValueError("R033 section lacks supported source controls/observations; no invented input")
    times = selected.session_time_s.to_numpy(float)
    first_speed = float(selected.speed_mps.iloc[0])
    if (not 40 <= first_speed <= 105 or np.any(np.diff(times) <= 0) or max(np.diff(times)) > .5+1e-9
            or not 2-1e-9 <= times[-1]-times[0] <= 3.5+1e-9):
        raise ValueError("R033 section outside R030 initial speed/time support")
    return RecordedLongitudinalInputs(section_id, first_speed, times.copy(), selected.throttle.to_numpy(float),
                                      selected.drs_open.to_numpy(dtype=np.int64), rows.copy())


def require_full_bicycle_observations(frame: pd.DataFrame) -> None:
    """Abstain instead of initializing missing steering/body states from proxies."""
    missing = [name for name in UNKNOWN_FIELDS if name not in frame or frame[name].isna().any()]
    if missing or "full_bicycle_ready" not in frame or not frame.full_bicycle_ready.all():
        raise ValueError("R033 complete measured bicycle replay unavailable: UNKNOWN "+", ".join(missing))
