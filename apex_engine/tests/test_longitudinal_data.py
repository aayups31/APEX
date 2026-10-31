import copy

import numpy as np
import pandas as pd
import pytest

from apexsim.research.longitudinal_data import extract_sections


def native_fixture(n=81):
    t = np.arange(n)*.25
    car = pd.DataFrame({"SessionTime": pd.to_timedelta(t, unit="s"),
                        "Date": pd.Timestamp("2023-01-01")+pd.to_timedelta(t, unit="s"),
                        "Speed": (50+t*.4)*3.6, "Throttle": np.full(n, 100), "Brake": np.zeros(n, dtype=bool),
                        "DRS": np.full(n, 12), "Source": ["car"]*n})
    lap = {"event_id": "F1_2023_R01", "track_id": "bahrain", "driver_id": "4", "lap_number": 7,
           "lap_id": "F1_2023_R01_4_7", "role": "test", "native_row": 0, "lap_start_s": 0., "lap_end_s": float(t[-1])}
    geometry = {"time_s": t, "curvature_1pm": np.zeros(n), "distance_m": np.zeros(n),
                "native_parents": np.repeat(np.arange(n)[:, None], 2, axis=1)}
    return car, lap, geometry


def test_native_units_causal_warmup_event_roles_and_nonoverlapping_intervals():
    car, lap, geometry = native_fixture()
    sections, quality, rejected = extract_sections(car, lap, geometry)
    assert len(sections) >= 5
    assert quality["native_lap_rows"] == quality["eligible_rows"]+quality["rejected_rows"]
    assert quality["rejected_rows"] == len(rejected)
    intervals = []
    for section in sections:
        assert section.metadata["role"] == "train"
        assert section.metadata["geometry_original_role"] == "test"
        assert section.speed_mps[0] == pytest.approx(float(car.Speed.iloc[section.car_rows[0]])/3.6)
        assert section.initial_acceleration_mps2 == pytest.approx(.4)
        assert section.warmup_time_s[-1] == section.time_s[0]
        intervals.extend(zip(section.car_rows[:-1], section.car_rows[1:], strict=True))
    assert len(intervals) == len(set(intervals))


def test_gap_brake_unknown_drs_and_curvature_are_explicit_exclusions():
    car, lap, geometry = native_fixture()
    car.loc[20, "Brake"] = True
    car.loc[35, "DRS"] = 2
    geometry["curvature_1pm"][50] = .01
    sections, quality, rejected = extract_sections(car, lap, geometry)
    assert quality["rejection_counts"]["unknown_drs_code"] == 1
    assert quality["rejection_counts"]["outside_reference_straight_support"] == 1
    assert 20 in [r["native_car_row"] for r in rejected]
    for section in sections:
        assert not set(section.car_rows) & {20, 35, 50}


def test_drs_transitions_do_not_cross_sections():
    car, lap, geometry = native_fixture()
    car.loc[40:, "DRS"] = 0
    sections, _, _ = extract_sections(car, lap, geometry)
    assert {int(s.drs_open[0]) for s in sections} == {0, 1}
    assert all(np.ptp(s.drs_open) == 0 for s in sections)


def test_future_endpoint_changes_do_not_change_initial_acceleration_or_source_keys():
    car, lap, geometry = native_fixture()
    first, _, _ = extract_sections(car, lap, geometry)
    changed = car.copy()
    row = first[0].car_rows[-1]
    changed.loc[row, "Speed"] += .5
    second, _, _ = extract_sections(changed, lap, geometry)
    assert first[0].metadata == second[0].metadata
    assert first[0].initial_acceleration_mps2 == second[0].initial_acceleration_mps2
    assert first[0].speed_mps[-1] != second[0].speed_mps[-1]


def test_future_position_is_not_used_and_timing_anchors_are_not_native_observations():
    car, lap, geometry = native_fixture()
    geometry["time_s"] = geometry["time_s"]+.1
    geometry["native_parents"][25] = [25, 26]
    sections, _, rejected = extract_sections(car, lap, geometry)
    assert any(r["native_car_row"] == 26 and r["reason"] == "unsupported_causal_position" for r in rejected)
    for section in sections:
        assert np.all(section.geometry_rows < section.car_rows)


def test_clock_disagreement_and_missing_channels_fail_closed():
    car, lap, geometry = native_fixture()
    bad = car.copy()
    offsets = np.zeros(len(car), dtype=int)
    offsets[30] = 2
    bad["Date"] = car.Date+pd.to_timedelta(offsets, unit="ms")
    with pytest.raises(ValueError, match="clocks"):
        extract_sections(bad, lap, geometry)
    with pytest.raises(ValueError, match="channels"):
        extract_sections(car.drop(columns="DRS"), lap, geometry)


def test_protected_event_guard_runs_before_reading_native_channels():
    _, lap, geometry = native_fixture()
    lap = copy.deepcopy(lap)
    lap["event_id"] = "F1_2023_R04"
    with pytest.raises(ValueError, match="Permanent benchmark"):
        extract_sections(pd.DataFrame(), lap, geometry)
