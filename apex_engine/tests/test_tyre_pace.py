import copy

import numpy as np
import pandas as pd
import pytest

from apexsim.data.tyre_dataset import FuelPrior, segment_native_laps
from apexsim.research.hierarchical_tyre import (
    HierarchicalTyreModel,
    HierarchySettings,
    apply_calibration,
    calibration_scales,
    split_rhat,
)
from apexsim.research.tyre_pace import (
    PaceParameters,
    drift_likelihood,
    filter_prefix,
    fit_pace,
    forecast_rows,
)


def segments(seed=77):
    rng = np.random.default_rng(seed)
    result = []
    for i in range(18):
        drift = .08 + (i % 3) * .015
        values = 90 + drift * np.arange(20) + rng.normal(0, .05, 20)
        result.append({"segment_id": f"s{i}", "event_id": "F1_2024_R01", "season": 2024, "round_number": 1,
                       "race_date": "2024-03-02", "track_id": f"track{i % 2}", "driver": str(i % 3),
                       "compound": ("SOFT", "MEDIUM", "HARD")[i % 3],
                       "rows": [{"lap": j + 1, "corrected_s": float(v)} for j, v in enumerate(values)]})
    return result


def test_hand_filter_and_independent_covariance_drift_likelihood():
    mean, variance = filter_prefix(np.array([90., 90.2]), .1, .01, .04)
    assert mean == pytest.approx(90.15555555555555)
    assert variance == pytest.approx(.022222222222222223)
    values = np.array([90., 90.2, 90.25, 90.5])
    center, var, _ = drift_likelihood(values, .01, .04)
    t = np.arange(1, len(values))
    covariance = .01 * np.minimum.outer(t, t) + .04 * np.eye(len(t)) + .04
    inverse = np.linalg.inv(covariance)
    expected_var = 1 / (t @ inverse @ t)
    expected_mean = expected_var * t @ inverse @ (values[1:] - values[0])
    assert var == pytest.approx(expected_var, abs=1e-12)
    assert center == pytest.approx(expected_mean, abs=1e-12)


def test_likelihood_fit_recovers_synthetic_drift_and_keeps_events():
    data = segments()
    params, report = fit_pace(data)
    assert report["training_events"] == ["F1_2024_R01"]
    assert params.drift == pytest.approx((.08, .095, .11), abs=.015)
    assert params.process_variance > 0 and params.observation_variance > 0


def test_future_observations_do_not_change_earlier_predictions():
    data = segments()[:1]
    params = PaceParameters((.08, .08, .08), .01, .04)
    original = forecast_rows(data, params)
    data[0]["rows"][-1]["corrected_s"] += 100
    changed = forecast_rows(data, params)
    for before, after in zip(original, changed, strict=True):
        if before["origin_lap"] < 19:
            assert before["predicted_corrected_s"] == after["predicted_corrected_s"]
    assert any(a["observed_corrected_s"] != b["observed_corrected_s"] for a, b in zip(original, changed, strict=True))


@pytest.mark.parametrize("variance", [0., -1., float("nan")])
def test_invalid_variances_rejected(variance):
    with pytest.raises(ValueError):
        PaceParameters((.1, .1, .1), variance, .1)


def test_benchmark_refused_at_model_boundary():
    data = segments()
    data[0].update(season=2023, round_number=4, event_id="F1_2023_R04")
    with pytest.raises(ValueError, match="Permanent benchmark"):
        fit_pace(data)


def test_fuel_prior_truth_boundary_and_no_negative_clipping():
    assert FuelPrior().effect(1) == pytest.approx(3.15)
    assert FuelPrior().effect(2) == pytest.approx(3.108)
    with pytest.raises(ValueError, match="no clipping"):
        FuelPrior().effect(100)
    with pytest.raises(ValueError):
        FuelPrior(time_s_per_kg=float("nan")).effect(1)


def test_source_mask_gap_and_stint_resets_preserve_rejection_rows():
    n = 20
    frame = pd.DataFrame({"DriverNumber": ["4"] * n, "LapNumber": np.arange(1, n + 1), "Stint": [1] * 10 + [2] * 10,
                          "Compound": ["MEDIUM"] * n, "TyreLife": np.arange(n),
                          "LapTime": pd.to_timedelta(np.full(n, 90.), unit="s"), "IsAccurate": [True] * n,
                          "Deleted": [False] * n, "TrackStatus": ["1"] * n,
                          "PitInTime": [pd.NaT] * n, "PitOutTime": [pd.NaT] * n})
    frame.loc[9, "TrackStatus"] = "2"
    event = {"season": 2024, "round_number": 1, "event_id": "F1_2024_R01", "track_id": "fixture", "race_date": "2024-03-02"}
    result, excluded = segment_native_laps(frame, event, FuelPrior())
    assert [len(s["rows"]) for s in result] == [9, 10]
    assert [s["rows"][0]["lap"] for s in result] == [1, 11]
    assert excluded == [{"native_row": 9, "reasons": ["not_exact_green_status"]}]


def test_hierarchy_local_rng_draws_and_unknown_group_uncertainty():
    data = segments()
    noise = PaceParameters((.1, .1, .1), .001, .01)
    settings = HierarchySettings(warmup=100, draws=200)
    np.random.seed(123)
    before = np.random.get_state()
    a, b = HierarchicalTyreModel(noise, settings), HierarchicalTyreModel(noise, settings)
    report = a.fit(data)
    b.fit(data)
    np.testing.assert_array_equal(a.chains, b.chains)
    after = np.random.get_state()
    assert before[0] == after[0] and np.array_equal(before[1], after[1]) and before[2:] == after[2:]
    assert np.isfinite(report["max_supported_split_rhat"])
    unknown = {**data[0], "track_id": "unseen"}
    assert np.var(a.drift_draws(unknown)) > np.var(a.drift_draws(data[0]))
    initial = a.chains.copy()
    one = a.forecast([unknown])
    changed = copy.deepcopy(unknown)
    changed["rows"][-1]["corrected_s"] += 100
    two = a.forecast([changed])
    np.testing.assert_array_equal(a.chains, initial)
    assert [r["predicted_corrected_s"] for r in one] == [r["predicted_corrected_s"] for r in two]


def test_validation_only_calibration_is_immutable_when_test_changes():
    model = HierarchicalTyreModel(PaceParameters((.1, .1, .1), .001, .01), HierarchySettings(warmup=50, draws=100))
    model.fit(segments())
    validation = model.forecast(segments()[:1])
    scales = calibration_scales(validation)
    original = dict(scales)
    test = model.forecast(segments(seed=81)[:1])
    test[0]["observed_corrected_s"] += 1000
    result = apply_calibration(test, scales)
    assert scales == original
    assert result[0]["calibrated_upper_90_s"] < result[0]["observed_corrected_s"]
    with pytest.raises(ValueError):
        split_rhat(np.zeros((1, 10, 2)))
