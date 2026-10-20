"""R029 v2 source support and mathematical controls, independent of public outcomes."""
import numpy as np
import pytest
from test_reference_geometry import native_fixture

from apexsim.research.position_laps import extract_position_lap
from apexsim.research.reference_geometry import GeometryConfig, fit_reference
from apexsim.research.supported_geometry import (
    evaluate_supported,
    station_support,
    supported_polyline_distances,
    supported_windows,
)


def test_native_gaps_are_explicit_without_adding_or_replacing_vertices():
    laps, positions, selection = native_fixture()
    broken = positions.drop(index=range(40, 48)).reset_index(drop=True)
    with pytest.raises(ValueError, match="gaps"):
        extract_position_lap(laps, broken, selection)
    trace = extract_position_lap(laps, broken, selection, allow_interior_gaps=True)
    assert len(trace["xy_m"]) == 394  # 400 original native rows -8, plus two anchors.
    assert (~trace["interval_supported"]).sum() == 1
    gap = trace["metadata"]["unsupported_intervals"][0]
    assert (gap["start_s"], gap["end_s"], gap["gap_s"]) == (9.75, 12., 2.25)
    np.testing.assert_array_equal(trace["time_s"][1:-1], broken.SessionTime.dt.total_seconds().to_numpy()[1:393])
    assert "lower-bound" in trace["metadata"]["chord_phase_truth"]


def test_gap_mode_never_relaxes_boundary_or_native_status_rules():
    laps, positions, selection = native_fixture()
    with pytest.raises(ValueError, match="boundary bracket"):
        extract_position_lap(laps, positions.iloc[1:].reset_index(drop=True), selection, allow_interior_gaps=True)
    positions.loc[20, "Status"] = "OffTrack"
    with pytest.raises(ValueError, match="supported native"):
        extract_position_lap(laps, positions, selection, allow_interior_gaps=True)


def test_curvature_stencils_exclude_the_entire_missing_interval():
    chord = np.arange(0., 201., 10.)
    intervals = np.ones(20, bool)
    intervals[8:10] = False  # Missing span80..100m.
    centers = np.array([25., 50., 75., 100., 125., 150., 175.])
    np.testing.assert_array_equal(supported_windows(chord, intervals, centers), [True, True, False, False, True, True, True])
    with pytest.raises(ValueError):
        supported_windows(chord, intervals[:-1], centers)


def test_observed_baseline_never_invents_a_segment_across_a_hole():
    line = np.array([[0., 0.], [1., 0.], [9., 0.], [10., 0.]])
    points = np.array([[5., 0.], [.5, 2.], [9.5, 2.]])
    result = supported_polyline_distances(points, line, [True, False, True])
    np.testing.assert_allclose(result, [4., 2., 2.])


def test_multiple_laps_cover_staggered_holes_and_common_holes_are_rejected():
    stations = np.arange(0., 1001., 10.) % 1000
    intervals = []
    for lo in (10, 30, 50, 70):
        flags = np.ones(100, bool)
        flags[lo:lo+3] = False
        intervals.append(flags)
    _, donors = station_support(1000., [stations]*4, intervals)
    assert donors.sum(axis=0).min() == 3
    for flags in intervals:
        flags[85:90] = False
    _, donors = station_support(1000., [stations]*4, intervals)
    assert donors.sum(axis=0).min() == 0


def test_unsupported_curvature_stencils_remain_unknown_in_saved_predictions():
    theta = np.linspace(0., 2*np.pi, 401)
    xy = np.column_stack((500*np.cos(theta), 500*np.sin(theta)))
    curve = fit_reference([xy], GeometryConfig(32, .05), "circle")
    flags = np.ones(400, bool)
    flags[20:30] = False
    m, arrays = evaluate_supported(curve, {"interval_supported": flags}, xy, xy, flags)
    valid = arrays["coarse_supported"]
    assert 0 < m["coarse_supported_targets"] < m["coarse_total_targets"]
    assert np.isnan(arrays["coarse_curvature_proxy_1pm"][~valid]).all()
    assert np.isnan(arrays["coarse_model_curvature_1pm"][~valid]).all()
    assert np.isnan(arrays["coarse_xy_m"][~valid]).all()
    assert m["coarse_curvature_mae_1pm"] < 1e-5


def test_coverage_endpoint_roundoff_does_not_expand_real_missing_regions():
    _, tiny = station_support(1000., [np.array([1e-7, 50.])]*3, [np.array([True])]*3)
    assert tiny[:, 0].all()
    _, real = station_support(1000., [np.array([.01, 50.])]*3, [np.array([True])]*3)
    assert not real[:, 0].any()
