"""R033 independent scalar causal join and native-control/state conversion audit."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from apexsim.research.recorded_alignment import UNKNOWN_FIELDS


def audit_aligned_lap(car: pd.DataFrame, position: pd.DataFrame, lap: dict, stored: pd.DataFrame) -> dict:
    """Use a scalar backward pointer, not the primary searchsorted alignment helper."""
    ct = [float(v.value/1e9) for v in car.SessionTime]
    pt = [float(v.value/1e9) for v in position.SessionTime]
    start, end = lap["lap_start_s"], lap["lap_end_s"]
    car_ids = [i for i, t in enumerate(ct) if start <= t < end]
    pos_ids = [i for i, t in enumerate(pt) if start <= t < end]
    if stored.source_car_row.tolist() != car_ids or not stored.lap_id.eq(lap["lap_id"]).all():
        raise ValueError("R033 independent native row/lap identity mismatch")
    k, ready, speed_ok, maximum_error = -1, [], [], 0.
    known_drs = {0: 0, 1: 0, 8: 0, 10: 1, 12: 1, 14: 1}

    def number(row, key):
        try:
            return float(row.get(key, math.nan))
        except (TypeError, ValueError):
            return math.nan

    for output_id, i in enumerate(car_ids):
        while k+1 < len(pos_ids) and pt[pos_ids[k+1]] <= ct[i]:
            k += 1
        row = car.iloc[i]
        out = stored.iloc[output_id]
        source = row.Source == "car"
        speed = number(row, "Speed")/3.6
        throttle = number(row, "Throttle")/100
        rpm = number(row, "RPM")
        gear = number(row, "nGear")
        drs = number(row, "DRS")
        brake = row.Brake if "Brake" in car else None
        speed_valid = source and math.isfinite(speed) and 0 <= speed <= 120
        engine = (source and math.isfinite(rpm) and rpm.is_integer() and 0 <= rpm <= 30000
                  and math.isfinite(gear) and gear.is_integer() and 0 <= gear <= 8)
        control = source and math.isfinite(throttle) and 0 <= throttle <= 1 and isinstance(brake, (bool, np.bool_)) and drs in known_drs
        pos_valid, j = False, pos_ids[k] if k >= 0 else None
        if k >= 1:
            p = position.iloc[j]
            pos_valid = (ct[i]-pt[j] <= .35+1e-9 and pt[j]-pt[pos_ids[k-1]] <= .75+1e-9
                         and p.Source == "pos" and p.Status == "OnTrack" and math.isfinite(p.X) and math.isfinite(p.Y))
        if (bool(out.controls_observed) != control or bool(out.engine_observed) != engine
                or bool(out.speed_observed) != speed_valid or bool(out.position_observed) != pos_valid
                or bool(out.joint_observed_ready) != (control and engine and speed_valid and pos_valid)):
            raise ValueError("R033 independent observed-readiness mismatch")
        if pos_valid:
            if pd.isna(out.position_source_row) or int(out.position_source_row) != j or ct[i] < pt[j]:
                raise ValueError("R033 independent backward source row mismatch")
            for actual, expected in ((out.x_m, float(position.X.iloc[j])*.1), (out.y_m, float(position.Y.iloc[j])*.1),
                                     (out.position_age_s, ct[i]-pt[j]), (out.position_previous_gap_s, pt[j]-pt[pos_ids[k-1]])):
                maximum_error = max(maximum_error, abs(float(actual)-expected))
        elif not pd.isna(out.position_source_row) or not pd.isna(out.x_m) or not pd.isna(out.y_m):
            raise ValueError("R033 independent unsupported position was filled")
        for actual, expected in ((out.speed_mps, speed), (out.throttle, throttle), (out.rpm, rpm), (out.gear, gear)):
            if math.isnan(expected):
                if not pd.isna(actual):
                    raise ValueError("R033 independent unknown source channel was filled")
            else:
                maximum_error = max(maximum_error, abs(float(actual)-expected))
        if isinstance(brake, (bool, np.bool_)):
            if pd.isna(out.brake_on) or bool(out.brake_on) != bool(brake):
                raise ValueError("R033 independent brake observation mismatch")
        elif not pd.isna(out.brake_on):
            raise ValueError("R033 independent unknown brake pressure was filled")
        if drs in known_drs:
            if pd.isna(out.drs_open) or int(out.drs_open) != known_drs[drs]:
                raise ValueError("R033 independent recorded DRS mismatch")
        elif not pd.isna(out.drs_open):
            raise ValueError("R033 independent unknown DRS was filled")
        ready.append(control and engine and speed_valid and pos_valid)
        speed_ok.append(speed_valid)
    duration = 0.
    for n in range(len(car_ids)-1):
        dt = ct[car_ids[n+1]]-ct[car_ids[n]]
        expected = dt if ready[n] and speed_ok[n+1] and dt <= .5+1e-9 else 0.
        if abs(float(stored.covered_interval_s.iloc[n])-expected) > 1e-9:
            raise ValueError("R033 independent interval coverage mismatch")
        duration += expected
    if (maximum_error > 1e-9 or stored.full_bicycle_ready.any()
            or not stored[list(UNKNOWN_FIELDS)].isna().all().all()):
        raise ValueError("R033 independent units/unknown-state audit failed")
    return {"lap_id": lap["lap_id"], "rows": len(car_ids), "joint_observed_rows": sum(ready),
            "covered_interval_s": duration, "maximum_native_conversion_error": maximum_error}
