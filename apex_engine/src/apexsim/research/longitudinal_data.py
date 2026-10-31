"""R030 native high-speed full-throttle sections; no interpolation of controls/speed."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np
import pandas as pd

from apexsim.data.benchmark_guard import assert_development_event

EVENT_ROLES = {"F1_2023_R01": "train", "F1_2023_R14": "train",
               "F1_2024_R01": "validation", "F1_2024_R16": "test"}
EVENT_TRACKS = {"F1_2023_R01": "bahrain", "F1_2023_R14": "monza",
                "F1_2024_R01": "bahrain", "F1_2024_R16": "monza"}
DRS_STATES = {0: 0, 1: 0, 8: 0, 10: 1, 12: 1, 14: 1}


@dataclass(frozen=True)
class LongitudinalSection:
    """Recorded-control replay section. Speed after index0 is an observed target."""

    metadata: dict
    time_s: np.ndarray
    speed_mps: np.ndarray
    throttle: np.ndarray
    drs_open: np.ndarray
    car_rows: np.ndarray
    geometry_rows: np.ndarray
    warmup_time_s: np.ndarray
    warmup_speed_mps: np.ndarray

    def __post_init__(self) -> None:
        m = self.metadata
        event = m["event_id"]
        if event not in EVENT_ROLES or m["role"] != EVENT_ROLES[event] or m["track_id"] != EVENT_TRACKS[event]:
            raise ValueError("R030 section event/split/track identity mismatch")
        assert_development_event(int(event[3:7]), int(event[-2:]), event_id=event)
        n = len(self.time_s)
        arrays = [self.time_s, self.speed_mps, self.throttle, self.drs_open, self.car_rows, self.geometry_rows]
        if (n < 5 or any(a.shape != (n,) for a in arrays) or not all(np.isfinite(a).all() for a in arrays)
                or np.any(np.diff(self.time_s) <= 0) or np.any(np.diff(self.time_s) > .5+1e-9)
                or not 2.-1e-9 <= self.time_s[-1]-self.time_s[0] <= 3.5+1e-9
                or np.any((self.speed_mps < 40) | (self.speed_mps > 105))
                or np.any((self.throttle < .98) | (self.throttle > 1))
                or not np.all(np.isin(self.drs_open, [0, 1])) or np.ptp(self.drs_open) != 0
                or self.car_rows.dtype.kind not in "iu" or np.any(np.diff(self.car_rows) != 1)
                or self.geometry_rows.dtype.kind not in "iu" or np.any(self.geometry_rows < 0)
                or self.warmup_time_s.shape != (5,) or self.warmup_speed_mps.shape != (5,)
                or not np.isfinite([self.warmup_time_s, self.warmup_speed_mps]).all()
                or np.any(np.diff(self.warmup_time_s) <= 0) or np.any(np.diff(self.warmup_time_s) > .5+1e-9)
                or not .4-1e-9 <= np.ptp(self.warmup_time_s) <= 2.+1e-9
                or self.warmup_time_s[-1] != self.time_s[0] or self.warmup_speed_mps[-1] != self.speed_mps[0]):
            raise ValueError("Invalid R030 native section/time/control/causal warmup contract")

    @property
    def cell(self) -> str:
        return self.metadata["track_id"]+"/"+self.metadata["driver_id"]

    @property
    def initial_acceleration_mps2(self) -> float:
        t = self.warmup_time_s-self.warmup_time_s.mean()
        return float(t@self.warmup_speed_mps/(t@t))


def extract_sections(car: pd.DataFrame, lap: dict, geometry: dict[str, np.ndarray]) -> tuple[list[LongitudinalSection], dict, list[dict]]:
    """Source-only extraction on the previously frozen offline R029 geometry.

    ``geometry`` has time_s/curvature_1pm/distance_m/native_parents. At car time
    only its latest native (not interpolated timing-anchor) observation is used.
    """
    event = lap["event_id"]
    assert_development_event(int(event[3:7]), int(event[-2:]), event_id=event)
    if event not in EVENT_ROLES or lap["track_id"] != EVENT_TRACKS[event]:
        raise ValueError("Unexpected R030 source event/circuit")
    required = {"Date", "SessionTime", "Speed", "Throttle", "Brake", "DRS", "Source"}
    if not required.issubset(car):
        raise ValueError("Missing R030 native car channels")
    t = car.SessionTime.dt.total_seconds().to_numpy(float)
    date_dt = car.Date.diff().dt.total_seconds().to_numpy(float)[1:]
    if (not np.isfinite(t).all() or not np.isfinite(date_dt).all() or np.any(np.diff(t) <= 0)
            or not np.allclose(np.diff(t), date_dt, rtol=0, atol=1e-6)):
        raise ValueError("R030 native SessionTime/Date clocks are invalid or disagree")
    gt, curvature, distance, parents = (geometry[k] for k in ("time_s", "curvature_1pm", "distance_m", "native_parents"))
    if (len(gt) < 2 or curvature.shape != gt.shape or distance.shape != gt.shape or parents.shape != (len(gt), 2)
            or not np.isfinite([gt, curvature, distance]).all() or np.any(np.diff(gt) <= 0)):
        raise ValueError("Invalid R030 frozen geometry observation arrays")
    indices = np.flatnonzero((t >= lap["lap_start_s"]) & (t <= lap["lap_end_s"]))
    speed, throttle = car.Speed.to_numpy(float)/3.6, car.Throttle.to_numpy(float)/100
    brake, source, drs = car.Brake.to_numpy(), car.Source.to_numpy(), car.DRS.to_numpy()
    gidx = np.searchsorted(gt, t, side="right")-1
    accepted, rejections, runs = [], [], []
    current: list[int] = []
    for i in indices:
        reason = None
        j = gidx[i]
        if (source[i] != "car" or not np.isfinite([speed[i], throttle[i], drs[i]]).all()
                or not isinstance(brake[i], (bool, np.bool_))):
            reason = "unsupported_native_channels"
        elif not 40 <= speed[i] <= 105 or not .98 <= throttle[i] <= 1 or bool(brake[i]):
            reason = "outside_full_throttle_high_speed_domain"
        elif drs[i] not in DRS_STATES:
            reason = "unknown_drs_code"
        elif (j < 1 or parents[j, 0] != parents[j, 1] or t[i]-gt[j] > .35+1e-9
              or gt[j]-gt[j-1] > .75+1e-9):
            reason = "unsupported_causal_position"
        elif distance[j] > 15 or abs(curvature[j]) > .001:
            reason = "outside_reference_straight_support"
        elif (i < 4 or t[i-4] < lap["lap_start_s"] or not np.all(source[i-4:i+1] == "car")
              or not np.isfinite(speed[i-4:i+1]).all() or max(np.diff(t[i-4:i+1])) > .5+1e-9
              or not .4-1e-9 <= t[i]-t[i-4] <= 2.+1e-9):
            reason = "unsupported_causal_speed_warmup"
        if reason is not None:
            rejections.append({"lap_id": lap["lap_id"], "native_car_row": int(i), "reason": reason})
        else:
            accepted.append(int(i))
        continuous = (reason is None and current and i == current[-1]+1 and t[i]-t[current[-1]] <= .5+1e-9
                      and DRS_STATES[drs[i]] == DRS_STATES[drs[current[-1]]])
        if not continuous and current:
            runs.append(current)
            current = []
        if reason is None:
            current.append(int(i))
    if current:
        runs.append(current)
    sections, used = [], set()
    for run in runs:
        start = 0
        while start < len(run)-1:
            end = min(int(np.searchsorted(t[run], t[run[start]]+3., side="left")), len(run)-1)
            rows = np.array(run[start:end+1], dtype=np.int64)
            if t[rows[-1]]-t[rows[0]] < 2.-1e-9:
                break
            g = gidx[rows]
            section_id = f"{lap['lap_id']}_car{rows[0]}"
            metadata = {"section_id": section_id, "event_id": event, "track_id": lap["track_id"],
                        "driver_id": lap["driver_id"], "lap_number": lap["lap_number"], "lap_id": lap["lap_id"],
                        "role": EVENT_ROLES[event], "geometry_original_role": lap["role"],
                        "native_lap_row": lap["native_row"], "origin_native_car_row": int(rows[0]),
                        "source_truth": "FASTF1_PARSED_SOURCE; upstream reconstruction possible",
                        "geometry_conditioning": "FROZEN_OFFLINE_REGISTERED_REFERENCE; NOT_ONLINE_LOCALIZATION"}
            sections.append(LongitudinalSection(metadata, t[rows], speed[rows], throttle[rows],
                                                np.array([DRS_STATES[v] for v in drs[rows]], dtype=np.int64),
                                                rows, parents[g, 0].astype(np.int64), t[rows[0]-4:rows[0]+1], speed[rows[0]-4:rows[0]+1]))
            used.update(rows.tolist())
            start = end
    quality = {"lap_id": lap["lap_id"], "native_lap_rows": len(indices), "eligible_rows": len(accepted),
               "rejected_rows": len(rejections), "sectioned_unique_rows": len(used),
               "eligible_unsectioned_rows": len(accepted)-len(used), "sections": len(sections),
               "rejection_counts": dict(Counter(r["reason"] for r in rejections))}
    return sections, quality, rejections
