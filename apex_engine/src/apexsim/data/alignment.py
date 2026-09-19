"""Auditable temporal associations, preserving missingness and source row order."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AlignmentPolicy:
    """Declared diagnostic tolerances in milliseconds; no offsets are fitted."""

    car_location_ms: int = 1000
    car_weather_ms: int = 90000
    cross_telemetry_ms: int = 10
    cross_weather_ms: int = 1000
    telemetry_gap_ms: int = 1000
    weather_gap_ms: int = 90000

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if type(value) is not int or not 0 <= value <= 86400000:
                raise ValueError(f"{name} must be integer milliseconds in [0, 86400000]")


def utc_times(values, *, naive_is_utc: bool = False) -> pd.DatetimeIndex:
    """Normalize explicitly zoned timestamps; FastF1's documented naive UTC is opt-in."""
    series = pd.Series(values)
    if not naive_is_utc:
        present = series.dropna().astype(str)
        if not present.str.contains(r"(?:Z|[+-]\d{2}:\d{2})$", regex=True).all():
            raise ValueError("Source timestamps require an explicit UTC offset")
    result = pd.DatetimeIndex(pd.to_datetime(series, utc=True, format="ISO8601")).as_unit("ns")
    valid = result.dropna()
    if len(valid) and (valid.min() < pd.Timestamp("1950-01-01", tz="UTC") or valid.max() >= pd.Timestamp("2101-01-01", tz="UTC")):
        raise ValueError("Source timestamps outside supported 1950-2100 interval")
    return result


def stream_quality(times: pd.DatetimeIndex, gap_ms: int) -> dict:
    """Report missing/duplicate timestamps, source-order reversals and every long gap."""
    valid = times[~times.isna()].asi8
    unique = np.unique(valid)
    deltas = np.diff(unique)
    gaps = [{"start_utc": pd.Timestamp(int(unique[i]), tz="UTC").isoformat(),
             "end_utc": pd.Timestamp(int(unique[i + 1]), tz="UTC").isoformat(),
             "duration_ms": float(deltas[i] / 1e6)} for i in np.flatnonzero(deltas > gap_ms * 1000000)]
    return {"rows": len(times), "missing_timestamps": int(times.isna().sum()),
            "duplicate_timestamp_rows": int(len(valid) - len(unique)),
            "source_order_reversals": int((np.diff(valid) < 0).sum()),
            "gap_threshold_ms": gap_ms, "gap_count": len(gaps), "gaps": gaps,
            "maximum_gap_ms": float(deltas.max() / 1e6) if len(deltas) else None,
            "first_utc": pd.Timestamp(int(unique[0]), tz="UTC").isoformat() if len(unique) else None,
            "last_utc": pd.Timestamp(int(unique[-1]), tz="UTC").isoformat() if len(unique) else None}


def temporal_join(left: pd.DatetimeIndex, right: pd.DatetimeIndex, *, tolerance_ms: int,
                  direction: str = "backward") -> tuple[pd.DataFrame, dict]:
    """Associate one pair of already-partitioned streams without dropping left rows.

    Nearest is diagnostic only; equal-distance ties prefer the earlier timestamp.
    A duplicate selected right timestamp is ambiguous and is rejected, never silently
    deduplicated. Row indices address original input order, including missing rows.
    """
    if direction not in {"backward", "nearest"}:
        raise ValueError("Alignment direction must be backward or nearest")
    if type(tolerance_ms) is not int or not 0 <= tolerance_ms <= 86400000:
        raise ValueError("tolerance_ms must be integer milliseconds in [0, 86400000]")
    if left.tz is None or right.tz is None:
        raise ValueError("Alignment requires timezone-aware timestamps")
    left, right = utc_times(left), utc_times(right)
    n = len(left)
    chosen = np.full(n, -1, dtype=np.int64)
    delta = np.full(n, np.nan)
    reason = np.full(n, "missing_left_timestamp", dtype=object)
    valid_left, valid_right = np.flatnonzero(~left.isna()), np.flatnonzero(~right.isna())
    reason[valid_left] = "no_target_in_direction"
    if len(valid_left) and len(valid_right):
        target, first, counts = np.unique(right.asi8[valid_right], return_index=True, return_counts=True)
        source = left.asi8[valid_left]
        pos = np.searchsorted(target, source, side="right") - 1
        if direction == "nearest":
            following = np.clip(pos + 1, 0, len(target) - 1)
            preceding = np.clip(pos, 0, len(target) - 1)
            choose_next = (pos < 0) | (np.abs(target[following] - source) < np.abs(target[preceding] - source))
            pos = np.where(choose_next, following, preceding)
        has_candidate = pos >= 0
        safe = np.clip(pos, 0, len(target) - 1)
        signed_ns = target[safe] - source
        within = has_candidate & (np.abs(signed_ns) <= tolerance_ms * 1000000)
        ambiguous = within & (counts[safe] > 1)
        accepted = within & ~ambiguous
        reason[valid_left[has_candidate & ~within]] = "outside_tolerance"
        reason[valid_left[ambiguous]] = "ambiguous_target_timestamp"
        reason[valid_left[accepted]] = "matched"
        chosen[valid_left[accepted]] = valid_right[first[safe[accepted]]]
        delta[valid_left[accepted]] = signed_ns[accepted] / 1e6
    matched = chosen >= 0
    right_rows = pd.array(chosen, dtype="Int64")
    right_rows[~matched] = pd.NA
    right_times = pd.Series(pd.NaT, index=range(n), dtype="datetime64[ns, UTC]")
    right_times.loc[matched] = right.take(chosen[matched])
    pairs = pd.DataFrame({"left_row": np.arange(n), "left_utc": left, "right_row": right_rows,
                          "right_utc": right_times, "right_minus_left_ms": delta,
                          "matched": matched, "reason": reason})
    accepted_delta = delta[matched]
    stats = {"direction": direction, "tolerance_ms": tolerance_ms, "left_rows": n, "right_rows": len(right),
             "matched_rows": int(matched.sum()), "unmatched_rows": int((~matched).sum()),
             "join_rate_all_rows": float(matched.mean()) if n else None,
             "future_matches": int((accepted_delta > 0).sum()),
             "reused_right_rows": int(matched.sum() - len(set(chosen[matched]))),
             "unmatched_reasons": {str(key): int(value) for key, value in pd.Series(reason[~matched]).value_counts().items()},
             "signed_delta_ms_median": float(np.median(accepted_delta)) if len(accepted_delta) else None,
             "absolute_delta_ms_p95": float(np.quantile(np.abs(accepted_delta), 0.95)) if len(accepted_delta) else None,
             "absolute_delta_ms_max": float(np.max(np.abs(accepted_delta))) if len(accepted_delta) else None}
    return pairs, stats
