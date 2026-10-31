from dataclasses import replace

import numpy as np
import pytest

from apexsim.research.longitudinal_calibration import SpecificPowerDrag
from apexsim.research.longitudinal_data import LongitudinalSection
from apexsim.research.open_loop_errors import error_record, hierarchical_scores, horizon_grid, predict_horizon


def section():
    t = 10+np.arange(13)*.24
    return LongitudinalSection({"event_id": "F1_2023_R01", "track_id": "bahrain", "driver_id": "4", "role": "train",
                                "lap_id": "one", "section_id": "one_section"}, t, 50+.2*(t-10),
                               np.ones(13), np.zeros(13, dtype=np.int64), np.arange(13, dtype=np.int64),
                               np.arange(13, dtype=np.int64), 10+np.arange(-4, 1)*.24, 50+np.arange(-4, 1)*.048)


def models():
    return {"candidates": {"shared_drag": {"cells": {"bahrain/4": {"parameters": SpecificPowerDrag(600, .001).as_dict()}}}},
            "legacy": {"bahrain/4": {"rolling_accel": .1, "throttle_accel_gain": 8., "drag_accel_coeff": .001}}}


def test_short_exact_horizon_inserts_endpoint_and_never_future_controls():
    s = section()
    changed = replace(s, throttle=np.r_[np.ones(3), np.full(10, .98)])
    t, u, _, targets = horizon_grid(changed, .5)
    assert t[-1] == .5 and u[-1] == 1
    assert targets[-1] == pytest.approx(50.1)
    np.testing.assert_allclose(t, [0, .24, .48, .5], atol=1e-12)
    with pytest.raises(ValueError, match="HORIZON_OUTSIDE"):
        horizon_grid(s, 3)


def test_predictions_ignore_future_speed_targets_in_every_method():
    s = section()
    changed = replace(s, speed_mps=np.r_[s.speed_mps[0], s.speed_mps[1:]+2])
    for method in ("shared_drag", "legacy_huber", "physical_prior", "constant_speed", "constant_acceleration"):
        np.testing.assert_array_equal(predict_horizon(s, 1, method, models()), predict_horizon(changed, 1, method, models()))


def test_hand_error_metrics_exclude_initial_node_and_keep_signed_integral():
    result = error_record(np.array([0, 1, 2.]), np.array([10, 10, 10.]), np.array([10, 11, 13.]))
    assert result["mse_m2ps2"] == 5 and result["mae_mps"] == 2
    assert result["endpoint_error_mps"] == 3 and result["speed_integral_error_m"] == 2.5
    with pytest.raises(ValueError, match="matched"):
        error_record(np.array([0, 0.]), np.ones(2), np.ones(2))


def test_event_driver_lap_weighting_does_not_weight_dense_driver_more():
    rows = []
    for event, driver, lap, error, count in [("A", "4", "one", 3, 5), ("A", "44", "two", 1, 1), ("B", "4", "three", 2, 1)]:
        for _ in range(count):
            rows.append({"event_id": event, "driver_id": driver, "lap_id": lap, "horizon_s": 1.,
                         **error_record(np.array([0, 1.]), np.array([10, 10.]), np.array([10, 10+error]))})
    assert hierarchical_scores(rows)["mse_m2ps2"] == pytest.approx(4.5)
    assert hierarchical_scores([]) is None
    with pytest.raises(ValueError, match="different forecast horizons"):
        hierarchical_scores([rows[0], dict(rows[1], horizon_s=2.)])
