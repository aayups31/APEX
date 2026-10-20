import copy
import json
import shutil

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from apexsim.cli import app
from apexsim.examples.track_reconstruction_demo import (
    _annotations,
    fit_case,
    run_track_reconstruction,
    verify_track_reconstruction,
)
from apexsim.provenance import file_sha256, payload_sha256
from apexsim.research.position_laps import boundary_position, extract_position_lap, position_arrays
from apexsim.research.reference_geometry import GeometryConfig, ReferenceCurve, fit_reference, register_lap
from apexsim.sim_core.track import TrackMap
from apexsim.track_geometry import GeometryProvider


def shape(a=100., b=100., count=1025):
    theta = np.linspace(0, 2*np.pi, count)
    return np.column_stack((a*np.cos(theta), b*np.sin(theta)))


def test_circle_independent_length_signed_curvature_station_and_projection():
    curve = fit_reference([shape()], GeometryConfig(32, 0), "circle")
    assert curve.length_m == pytest.approx(200*np.pi, rel=1e-8)
    station = np.linspace(0, curve.length_m, 200, endpoint=False)
    xy, tangent, curvature = curve.geometry(station)
    np.testing.assert_allclose(curvature, .01, rtol=1e-4)
    np.testing.assert_allclose(np.linalg.norm(tangent, axis=1), 1, atol=1e-12)
    points = xy*1.07
    result = curve.project(points)
    np.testing.assert_allclose(result["distance_m"], 7, atol=1e-6)
    # Positive left normal points inward for a counterclockwise circle.
    np.testing.assert_allclose(result["signed_lateral_m"], -7, atol=1e-6)
    wrapped = (result["station_m"]-station+curve.length_m/2)%curve.length_m-curve.length_m/2
    assert abs(wrapped).max() < 1e-4
    clockwise = fit_reference([shape()[::-1]], GeometryConfig(32, 0), "clockwise")
    np.testing.assert_allclose(clockwise.geometry(station)[2], -.01, rtol=1e-4)


def test_ellipse_analytic_curvature_and_rigid_frame_invariance():
    xy = shape(160, 80, 2049)
    curve = fit_reference([xy], GeometryConfig(64, 0), "ellipse")
    theta = np.linspace(.05, 6.2, 64)
    points = np.column_stack((160*np.cos(theta), 80*np.sin(theta)))
    expected = 160*80/((160*np.sin(theta))**2+(80*np.cos(theta))**2)**1.5
    actual = curve.project(points)["curvature_1pm"]
    assert np.max(abs(actual-expected)) < 1e-4
    rotation = np.array([[0., -1.], [1., 0.]])
    shifted = xy@rotation+np.array([1500., -3200.])
    registered, transform = register_lap(shifted, xy)
    np.testing.assert_allclose(registered, xy, atol=1e-9)
    assert transform["determinant"] == pytest.approx(1) and transform["scale"] == 1


def test_periodic_normals_unknowns_and_shared_synthetic_contract():
    curve = fit_reference([shape()], GeometryConfig(24, 0), "circle")
    sample = curve.sample_geometry(-3)
    assert isinstance(curve, GeometryProvider)
    assert np.dot(sample.tangent, sample.left_normal) == pytest.approx(0, abs=1e-12)
    assert np.linalg.norm(sample.left_normal) == pytest.approx(1)
    assert curve.sample_geometry(curve.length_m) == curve.sample_geometry(0)
    assert np.linalg.norm(curve.evaluate_u([0])-curve.evaluate_u([1])) < 1e-8
    assert np.linalg.norm(curve.evaluate_u([0], 1)-curve.evaluate_u([1], 1)) < 1e-8
    legacy = TrackMap.synthetic(points=128)
    before = legacy.sample(30)
    assert isinstance(legacy, GeometryProvider)
    assert np.isfinite(legacy.sample_geometry(30).curvature_1pm)
    assert legacy.sample(30) == before
    for name in ("width_m", "elevation_m", "official_drs_zones", "pit_lane_route"):
        with pytest.raises(ValueError, match="UNKNOWN"):
            curve.require_ancillary(name)


def test_invalid_degenerate_geometry_and_nonfinite_queries():
    with pytest.raises(ValueError):
        GeometryConfig(0)
    with pytest.raises(ValueError, match="degenerate"):
        fit_reference([np.ones((100, 2))], GeometryConfig(), "bad")
    with pytest.raises(ValueError, match="degenerate"):
        ReferenceCurve(np.zeros((97, 2)), GeometryConfig(), "bad")
    curve = fit_reference([shape()], GeometryConfig(24, 0), "circle")
    with pytest.raises(ValueError, match="finite"):
        curve.sample_geometry(float("nan"))


def native_fixture():
    t = np.arange(0, 101, .25)
    theta = t/100*2*np.pi
    positions = pd.DataFrame({"SessionTime": pd.to_timedelta(t, unit="s"), "X": 1000*np.cos(theta),
                              "Y": 1000*np.sin(theta), "Source": "pos", "Status": "OnTrack"})
    laps = pd.DataFrame({"DriverNumber": ["4"], "LapNumber": [2.], "IsAccurate": [True], "Deleted": [False],
                         "TrackStatus": ["1"], "Compound": ["MEDIUM"], "PitInTime": [pd.NaT], "PitOutTime": [pd.NaT],
                         "LapStartTime": pd.to_timedelta([.125], unit="s"), "Time": pd.to_timedelta([100.125], unit="s"),
                         "LapTime": pd.to_timedelta([100], unit="s"), "Sector1Time": pd.to_timedelta([30], unit="s"),
                         "Sector2Time": pd.to_timedelta([35], unit="s")})
    selection = {"native_row": 0, "event_id": "F1_2024_R01", "driver_id": "4", "lap_number": 2, "role": "train"}
    return laps, positions, selection


def test_native_units_lineage_and_only_bounded_boundary_interpolation():
    laps, positions, selection = native_fixture()
    result = extract_position_lap(laps, positions, selection)
    assert result["metadata"]["native_samples"] == 400
    assert result["metadata"]["boundary_weights"] == [.5, .5]
    np.testing.assert_allclose(np.linalg.norm(result["xy_m"][1:-1], axis=1), 100, atol=1e-10)
    assert result["native_parents"][0].tolist() == [0, 1]
    assert result["native_parents"][-1].tolist() == [400, 401]
    assert result["metadata"]["raw_closure_gap_m"] < 1e-8
    with pytest.raises(ValueError, match="extrapolation"):
        boundary_position(position_arrays(positions), -1)


def test_missing_native_support_and_identity_refused_without_filling():
    laps, positions, selection = native_fixture()
    broken = positions.drop(index=range(40, 48)).reset_index(drop=True)
    with pytest.raises(ValueError, match="gaps"):
        extract_position_lap(laps, broken, selection)
    bad = positions.copy()
    bad.loc[20, "Status"] = "OffTrack"
    with pytest.raises(ValueError, match="supported native"):
        extract_position_lap(laps, bad, selection)
    with pytest.raises(ValueError, match="identity"):
        extract_position_lap(laps, positions, {**selection, "driver_id": "44"})


def test_benchmark_guard_before_native_payload(tmp_path):
    path = tmp_path/"protected"
    path.mkdir()
    (path/"manifest.json").write_text(json.dumps({"query": {"year": 2023, "round_number": 4, "session": "R"}}))
    with pytest.raises(ValueError, match="Permanent benchmark"):
        run_track_reconstruction([path], tmp_path/"no-mask", tmp_path/"no-mask2", tmp_path/"output")


def test_sector_timing_projection_and_unobserved_fields_remain_unknown():
    laps, positions, selection = native_fixture()
    lap = extract_position_lap(laps, positions, selection)
    curve = fit_reference([lap["xy_m"]], GeometryConfig(24, .05), "fixture")
    annotations = _annotations(curve, [lap], laps, positions, {"rotation": [[1., 0.], [0., 1.]], "translation_m": [0., 0.]})
    assert annotations["sector1_end"]["status"] == "RECONSTRUCTED_TIMING_PROJECTIONS"
    assert annotations["sector1_end"]["spread"]["circular_mean_station_m"] == pytest.approx(.3*curve.length_m, abs=.05)
    for field in ("width_m", "elevation_m", "official_drs_zones", "pit_lane_route", "surveyed_centerline"):
        assert annotations[field]["status"] == "UNKNOWN" and annotations[field]["value"] is None
    assert annotations["pit_entry"]["status"] == "UNKNOWN"
    json.dumps(annotations)


@pytest.fixture(scope="module")
def study(tmp_path_factory):
    output = tmp_path_factory.mktemp("reference-geometry")/"smoke"
    result = CliRunner().invoke(app, ["track-reconstruction-smoke", "--output", str(output)])
    assert result.exit_code == 0, result.output+repr(result.exception)
    return output


def test_complete_smoke_reloads_and_cannot_close_public_research(study):
    result = verify_track_reconstruction(study)
    assert result["verified"] and not result["task_closure_eligible"]
    assert json.loads((study/"summary.json").read_text())["input_truth"] == "SIMULATED"


def test_portable_refit_immutability_and_tamper(study, tmp_path):
    before = {p.name: file_sha256(p) for p in study.iterdir()}
    with pytest.raises(FileExistsError):
        run_track_reconstruction([], study, study, study)
    assert before == {p.name: file_sha256(p) for p in study.iterdir()}
    moved = tmp_path/"relocated"
    shutil.copytree(study, moved)
    assert verify_track_reconstruction(moved)["verified"]
    with (moved/"sim_circle_geometry_predictions.npz").open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_track_reconstruction(moved)


def test_held_out_shapes_never_change_fitted_coefficients_or_selection(study):
    metadata = json.loads((study/"sim_circle_lap_metadata.json").read_text())
    with np.load(study/"sim_circle_lap_inputs.npz") as raw:
        laps = [{"metadata": m, "xy_m": raw[m["lap_id"]+"_xy"].copy()} for m in metadata]
    first, arrays = fit_case(laps, "sim_circle")
    changed = copy.deepcopy(laps)
    for lap in changed:
        if lap["metadata"]["role"] == "test":
            lap["xy_m"][:, 0] *= 1.1
    second, new_arrays = fit_case(changed, "sim_circle")
    assert first["selected_config"] == second["selected_config"]
    np.testing.assert_array_equal(arrays["coefficients"], new_arrays["coefficients"])


def test_resealed_simulation_cannot_be_promoted_to_research(study, tmp_path):
    moved = tmp_path/"fake-public"
    shutil.copytree(study, moved)
    summary = json.loads((moved/"summary.json").read_text())
    summary.update(profile="research", task_closure_eligible=True)
    summary["content_sha256"] = payload_sha256({k:v for k,v in summary.items() if k != "content_sha256"})
    (moved/"summary.json").write_text(json.dumps(summary))
    manifest = json.loads((moved/"manifest.json").read_text())
    manifest["summary_sha256"] = summary["content_sha256"]
    manifest["files"]["summary.json"] = {"sha256": file_sha256(moved/"summary.json"), "bytes": (moved/"summary.json").stat().st_size}
    manifest["content_sha256"] = payload_sha256({k:v for k,v in manifest.items() if k != "content_sha256"})
    (moved/"manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="research source/cohort"):
        verify_track_reconstruction(moved)
