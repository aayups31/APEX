from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from apexsim.research.recorded_alignment import (
    UNKNOWN_FIELDS,
    align_lap,
    longitudinal_inputs,
    require_full_bicycle_observations,
)


def synthetic_sources():
    ct = 100+np.arange(30)*.24
    pt = 100.08+np.arange(33)*.22
    base = pd.Timestamp("2023-03-05T12:00:00Z")
    car = pd.DataFrame({"SessionTime": pd.to_timedelta(ct, unit="s"), "Date": base+pd.to_timedelta(ct, unit="s"),
                        "Time": pd.to_timedelta(np.zeros(len(ct)), unit="s"), "Source": "car", "Speed": 180.,
                        "Throttle": 100., "Brake": False, "DRS": 8., "RPM": 11000., "nGear": 6.})
    pos = pd.DataFrame({"SessionTime": pd.to_timedelta(pt, unit="s"), "Date": base+pd.to_timedelta(pt, unit="s"),
                        "Source": "pos", "Status": "OnTrack", "X": np.arange(len(pt))*110., "Y": 40.})
    lap = {"event_id": "F1_2023_R01", "driver_id": "4", "track_id": "bahrain", "lap_id": "fixture_lap",
           "lap_number": 3, "lap_start_s": 100., "lap_end_s": 107.2, "native_row": 0}
    return car, pos, lap


def test_native_units_causal_parent_rows_and_full_denominator_are_preserved():
    car, pos, lap = synthetic_sources()
    frame, metrics = align_lap(car, pos, lap)
    assert len(frame) == 30 and metrics["native_car_rows"] == 30
    assert frame.speed_mps.eq(50).all() and frame.throttle.eq(1).all() and frame.drs_open.eq(0).all()
    assert str(frame.brake_on.dtype) == "boolean"
    for row in frame.loc[frame.position_observed].itertuples():
        j = int(row.position_source_row)
        assert pos.SessionTime.iloc[j].total_seconds() <= row.session_time_s
        assert row.x_m == pytest.approx(pos.X.iloc[j]*.1)
    assert metrics["future_position_matches"] == 0
    assert metrics["lap_duration_s"] == pytest.approx(7.2)
    assert metrics["covered_interval_s"] < metrics["lap_duration_s"]


def test_future_positions_cannot_change_past_associations_or_observations():
    car, pos, lap = synthetic_sources()
    baseline, _ = align_lap(car, pos, lap)
    changed = pos.copy()
    future = changed.SessionTime.dt.total_seconds() > 103
    changed.loc[future, ["X", "Y"]] += 10000
    actual, _ = align_lap(car, changed, lap)
    pd.testing.assert_frame_equal(actual.loc[actual.session_time_s <= 103], baseline.loc[baseline.session_time_s <= 103])


def test_missing_steering_body_states_fuel_and_battery_are_unknown_and_abstain():
    frame, _ = align_lap(*synthetic_sources())
    assert frame[list(UNKNOWN_FIELDS)].isna().all().all()
    assert not frame.full_bicycle_ready.any()
    with pytest.raises(ValueError, match="UNKNOWN steering_rad"):
        require_full_bicycle_observations(frame)


def test_unknown_drs_missing_engine_and_nonboolean_brake_are_not_filled():
    car, pos, lap = synthetic_sources()
    car.loc[8, "DRS"] = 3
    car.loc[9, "RPM"] = np.nan
    car["Brake"] = car.Brake.astype(object)
    car.loc[10, "Brake"] = .3
    frame, metrics = align_lap(car, pos, lap)
    assert pd.isna(frame.drs_open.iloc[8]) and not frame.controls_observed.iloc[8]
    assert not frame.engine_observed.iloc[9] and pd.isna(frame.brake_on.iloc[10])
    assert not frame.loc[[8, 9, 10], "joint_observed_ready"].any()
    assert metrics["native_car_rows"] == 30


def test_gaps_and_half_open_lap_membership_cannot_bridge_other_laps():
    car, pos, lap = synthetic_sources()
    # The same source car row exactly on the new lap boundary belongs only to it.
    boundary = float(car.SessionTime.iloc[15].total_seconds())
    first, _ = align_lap(car, pos, dict(lap, lap_end_s=boundary))
    second, _ = align_lap(car, pos, dict(lap, lap_id="second", lap_start_s=boundary))
    assert not set(first.source_car_row)&set(second.source_car_row)
    assert second.source_car_row.iloc[0] == 15
    assert not second.position_observed.iloc[0]
    t = pos.SessionTime.dt.total_seconds()
    gap_pos = pos.loc[~t.between(102, 103)].reset_index(drop=True)
    frame, _ = align_lap(car, gap_pos, lap)
    assert (frame.position_status == "position_previous_gap_exceeds_limit").any()
    assert (frame.position_status == "position_age_exceeds_limit").any()


def test_bad_clock_or_duplicate_source_timestamps_are_rejected():
    car, pos, lap = synthetic_sources()
    broken = car.copy()
    broken["Date"] = broken.Date+pd.to_timedelta(np.where(np.arange(len(broken)) == 5, .001, 0), unit="s")
    with pytest.raises(ValueError, match="clocks"):
        align_lap(broken, pos, lap)
    duplicate = pos.copy()
    duplicate.loc[5, ["SessionTime", "Date"]] = duplicate.loc[4, ["SessionTime", "Date"]].values
    with pytest.raises(ValueError, match="clocks"):
        align_lap(car, duplicate, lap)


def test_longitudinal_adapter_is_independent_of_future_observed_speed_targets():
    frame, _ = align_lap(*synthetic_sources())
    rows = np.arange(5, 18, dtype=np.int64)
    baseline = longitudinal_inputs(frame, rows, "section")
    changed = frame.copy()
    changed.loc[changed.source_car_row > 5, "speed_mps"] += 10
    actual = longitudinal_inputs(changed, rows, "section")
    assert actual.initial_speed_mps == baseline.initial_speed_mps == 50
    for key in ("time_s", "throttle", "drs_open", "source_car_rows"):
        np.testing.assert_array_equal(getattr(actual, key), getattr(baseline, key))
    assert not hasattr(actual, "speed_targets")
    assert replace(actual, section_id="other").initial_speed_mps == 50
    with pytest.raises(ValueError, match="contiguous"):
        longitudinal_inputs(frame, np.array([5, 7, 8, 9, 10]), "gap")


def test_reserved_event_guard_runs_before_any_source_access():
    _, _, lap = synthetic_sources()
    with pytest.raises(ValueError, match="Permanent benchmark"):
        align_lap(None, None, dict(lap, event_id="F1_2023_R04"))


def test_independent_pointer_audit_matches_and_rejects_fabricated_state(monkeypatch):
    from apexsim.research import recorded_alignment
    from apexsim.research.recorded_alignment_audit import audit_aligned_lap

    car, pos, lap = synthetic_sources()
    frame, metrics = align_lap(car, pos, lap)
    monkeypatch.setattr(recorded_alignment, "align_lap", lambda *a, **k: pytest.fail("Audit reused primary join"))
    audit = audit_aligned_lap(car, pos, lap, frame)
    assert audit["joint_observed_rows"] == metrics["joint_observed_rows"]
    assert audit["maximum_native_conversion_error"] <= 1e-9
    frame.loc[5, "body_vy_mps"] = 0
    with pytest.raises(ValueError, match="unknown-state"):
        audit_aligned_lap(car, pos, lap, frame)
