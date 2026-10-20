"""Independent NumPy/native-table audit; does not import the geometry implementation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from apexsim.provenance import file_sha256, payload_sha256, write_manifest


def close(a, b):
    np.testing.assert_allclose(a, b, rtol=1e-9, atol=1e-8, equal_nan=True)


def raw_control(points, baseline, supported):
    # Independent point/finite-segment minimum, including every observed vertex.
    best = np.min(np.linalg.norm(points[:, None]-baseline[None, :], axis=2), axis=1)
    for i in np.flatnonzero(supported):
        v = baseline[i+1]-baseline[i]
        q = np.maximum(0., np.minimum(1., ((points-baseline[i])@v)/(v@v)))
        best = np.minimum(best, np.linalg.norm(points-baseline[i]-q[:, None]*v, axis=1))
    return best


def audit(input_path: Path, development: Path, retrospective: Path, archives: list[Path], output: Path) -> dict:
    if output.exists() or output.resolve().is_relative_to(input_path.resolve()):
        raise ValueError("Audit requires fresh output outside the immutable study")
    read = lambda p: json.loads(p.read_text())
    summary, manifest = read(input_path/"summary.json"), read(input_path/"manifest.json")
    assert summary["profile"] == "research_v3" and summary["task_closure_eligible"]
    for item in (summary, manifest):
        assert item["content_sha256"] == payload_sha256({k:v for k,v in item.items() if k != "content_sha256"})
    assert summary["content_sha256"] == manifest["summary_sha256"]
    for name, item in manifest["files"].items():
        assert Path(name).name == name and file_sha256(input_path/name) == item["sha256"]
    sources = {}
    for path in archives:
        m = read(path/"manifest.json")
        e = f"F1_{m['query']['year']}_R{m['query']['round_number']:02d}"
        saved = next(s for s in summary["sources"] if s["event_id"] == e)
        assert m["content_sha256"] == saved["archive_sha256"]
        for name in ("tables/laps.parquet", "tables/pos_data/4.parquet", "tables/pos_data/44.parquet"):
            assert file_sha256(path/name) == m["files"][name]["sha256"]
        sources[e] = {"laps": pd.read_parquet(path/"tables/laps.parquet"),
                      **{d: pd.read_parquet(path/f"tables/pos_data/{d}.parquet") for d in ("4", "44")}}
    assert len(sources) == 4
    old = read(retrospective/"summary.json")
    old_ids = {m["lap_id"] for c in old["cases"].values() for m in c["lap_metrics"] if m["role"] == "test"}
    development_summary = read(development/"summary.json")
    all_records, case_audits = [], {}
    for track, case in summary["cases"].items():
        metadata = read(input_path/f"{track}_lap_metadata.json")
        with np.load(input_path/f"{track}_lap_inputs.npz", allow_pickle=False) as raw, np.load(input_path/f"{track}_geometry_predictions.npz", allow_pickle=False) as pred, np.load(development/f"{track}_geometry_predictions.npz", allow_pickle=False) as dev, np.load(retrospective/f"{track}_geometry_predictions.npz", allow_pickle=False) as old_pred:
            np.testing.assert_array_equal(pred["coefficients"], dev["coefficients"])
            np.testing.assert_array_equal(pred["arc_u"], dev["arc_u"])
            np.testing.assert_array_equal(pred["arc_s"], dev["arc_s"])
            assert case["selected_config"] == development_summary["cases"][track]["selected_config"]
            assert case["candidate_selection"] == development_summary["cases"][track]["candidate_selection"]
            anchor = case["frame_anchor_lap_id"]
            baseline = pred[anchor+"_aligned_xy"]
            baseline_support = np.diff(raw[anchor+"_time"]) <= .75
            station_grid = pred["support_station_m"]
            donor_rows = []
            for m in metadata:
                key = m["lap_id"]
                fitted = next(x for x in case["lap_metrics"] if x["lap_id"] == key)
                if key in old_ids:
                    close(pred[key+"_xy_m"], old_pred[key+"_xy_m"])
                    close(pred[key+"_distance_m"], old_pred[key+"_distance_m"])
                    close(pred[key+"_coarse_unfiltered_proxy_diagnostic_1pm"], old_pred[key+"_coarse_curvature_proxy_1pm"])
                xy, time, parents = raw[key+"_xy"], raw[key+"_time"], raw[key+"_native_parents"]
                frame = sources[m["event_id"]][m["driver_id"]]
                native_time = frame.SessionTime.dt.total_seconds().to_numpy(float)
                native_xy = frame[["X", "Y"]].to_numpy(float)*.1
                lo, hi = parents.T
                assert np.all(lo >= 0) and np.all(hi < len(frame))
                weight = np.zeros(len(time))
                pair = lo != hi
                weight[pair] = (time[pair]-native_time[lo[pair]])/(native_time[hi[pair]]-native_time[lo[pair]])
                assert np.all((weight >= 0)&(weight <= 1))
                assert np.all(native_time[hi[pair]]-native_time[lo[pair]] <= .75)
                close(xy, native_xy[lo]*(1-weight[:, None])+native_xy[hi]*weight[:, None])
                close(time[~pair], native_time[lo[~pair]])
                for indices in (lo, hi):
                    assert (frame.Source.iloc[indices].to_numpy() == "pos").all()
                    assert (frame.Status.iloc[indices].to_numpy() == "OnTrack").all()
                native_ids = np.flatnonzero((native_time > m["lap_start_s"]+1e-8)&(native_time < m["lap_end_s"]-1e-8))
                interior = (time > m["lap_start_s"]+1e-8)&(time < m["lap_end_s"]-1e-8)
                np.testing.assert_array_equal(lo[interior], native_ids)
                np.testing.assert_array_equal(hi[interior], native_ids)
                lap_row = sources[m["event_id"]]["laps"].iloc[m["native_row"]]
                assert str(lap_row.DriverNumber) == m["driver_id"] and int(lap_row.LapNumber) == m["lap_number"]
                r = np.array(fitted["registration"]["rotation"])
                t = np.array(fitted["registration"]["translation_m"])
                aligned = xy@r+t
                close(aligned, pred[key+"_aligned_xy"])
                close(r.T@r, np.eye(2))
                close(np.linalg.det(r), 1.)
                support = np.diff(time) <= .75
                np.testing.assert_array_equal(support, pred[key+"_interval_supported"])
                displacement = np.diff(xy, axis=0)
                magnitude = np.linalg.norm(displacement, axis=1)
                cosine = np.sum(displacement[:-1]*displacement[1:], axis=1)/(magnitude[:-1]*magnitude[1:])
                derivative = support.copy()
                for index in np.flatnonzero(cosine <= 0):
                    derivative[index:index+2] = False
                close(cosine, pred[key+"_native_turn_cosine"])
                np.testing.assert_array_equal(derivative, pred[key+"_curvature_interval_supported"])
                chord = np.r_[0., np.cumsum(np.linalg.norm(np.diff(aligned, axis=0), axis=1))]
                centers = np.arange(25., chord[-1]-25., 25.)
                time_valid, valid = [], []
                for c in centers:
                    crosses = (chord[:-1] < c+25)&(chord[1:] > c-25)
                    time_valid.append(bool(support[crosses].all()))
                    valid.append(bool(derivative[crosses].all()))
                time_valid, valid = np.array(time_valid), np.array(valid)
                np.testing.assert_array_equal(time_valid, pred[key+"_coarse_time_supported"])
                np.testing.assert_array_equal(valid, pred[key+"_coarse_supported"])
                unfiltered = np.full(len(centers), np.nan)
                p = [np.column_stack([np.interp(centers[time_valid]+offset, chord, aligned[:, axis]) for axis in (0, 1)]) for offset in (-25., 0., 25.)]
                a, b = p[1]-p[0], p[2]-p[1]
                unfiltered[time_valid] = np.arctan2(a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0], np.sum(a*b, axis=1))/((np.linalg.norm(a, axis=1)+np.linalg.norm(b, axis=1))/2)
                close(unfiltered, pred[key+"_coarse_unfiltered_proxy_diagnostic_1pm"])
                close(unfiltered[valid], pred[key+"_coarse_curvature_proxy_1pm"][valid])
                assert np.isnan(pred[key+"_coarse_curvature_proxy_1pm"][~valid]).all()
                assert np.isnan(pred[key+"_coarse_model_curvature_1pm"][~valid]).all()
                distance = np.linalg.norm(aligned-pred[key+"_xy_m"], axis=1)
                close(distance, pred[key+"_distance_m"])
                control = raw_control(aligned, baseline, baseline_support)
                close(control, pred[key+"_raw_polyline_distance_m"])
                error = abs(pred[key+"_coarse_model_curvature_1pm"][valid]-unfiltered[valid])
                computed = {"xy_rmse_m": float(np.sqrt(np.mean(distance**2))), "xy_p95_m": float(np.quantile(distance, .95)),
                            "xy_max_m": float(distance.max()), "raw_polyline_p95_m": float(np.quantile(control, .95)),
                            "p95_minus_raw_polyline_m": float(np.quantile(distance, .95)-np.quantile(control, .95)),
                            "coarse_curvature_mae_1pm": float(error.mean()), "coarse_curvature_p95_1pm": float(np.quantile(error, .95)),
                            "coarse_support_fraction": float(valid.mean()), "coarse_supported_targets": int(valid.sum())}
                station = np.unwrap(pred[key+"_station_m"]/case["length_m"]*2*np.pi)*case["length_m"]/(2*np.pi)
                computed["backward_fraction"] = float(np.mean(np.diff(station) < -1e-6))
                for name, value in computed.items():
                    close(value, fitted[name])
                if m["role"] == "train":
                    donor = np.zeros(len(station_grid), bool)
                    for i, ds in enumerate(np.diff(station)):
                        if support[i] and 0 < ds <= 100:
                            delta = np.mod(station_grid-station[i], case["length_m"])
                            donor |= (delta <= ds+1e-6)|(case["length_m"]-delta <= 1e-6)
                    donor_rows.append(donor)
                if m["role"] == "test":
                    stratum = "retrospective" if key in old_ids else "additional_confirmation"
                    assert m["evaluation_stratum"] == stratum
                    assert computed["xy_rmse_m"] <= 6 and computed["xy_p95_m"] <= 12 and computed["xy_max_m"] <= 30
                    assert computed["p95_minus_raw_polyline_m"] <= 2 and computed["backward_fraction"] <= .02
                    assert computed["coarse_curvature_mae_1pm"] <= .003 and computed["coarse_curvature_p95_1pm"] <= .015
                    assert computed["coarse_support_fraction"] >= .75 and valid.sum() >= 100
                all_records.append({"lap_id": key, "track_id": track, "role": m["role"], "stratum": m.get("evaluation_stratum"),
                                    "native_vertices": len(xy), "reversal_vertices": int(np.count_nonzero(cosine <= 0)), **computed})
            donor_rows = np.array(donor_rows)
            np.testing.assert_array_equal(donor_rows, pred["support_donor_matrix"])
            assert np.all(donor_rows.sum(axis=0) >= 3)
            offsets = pred["sensitivity_normal_offsets_m"]
            close(np.quantile(abs(offsets), .95), case["sensitivity"]["p95_absolute_normal_offset_m"])
            close(abs(offsets).max(), case["sensitivity"]["max_absolute_normal_offset_m"])
            case_audits[track] = {"coefficients_and_arc_equal_development": True, "minimum_donor_laps": int(donor_rows.sum(axis=0).min()),
                                  "retrospective_position_predictions_reproduce_v2_1": True, "unfiltered_proxy_diagnostics_reproduce_v2_1": True,
                                  "all_native_vertices_and_parents_match_sources": True}
    tests = [m for m in all_records if m["role"] == "test"]
    assert len(tests) == 48 and sum(m["stratum"] == "additional_confirmation" for m in tests) == 24
    result = {"schema_version": "apex-reference-geometry-independent-audit-v3", "verified": True,
              "summary_sha256": summary["content_sha256"], "method": "Independent NumPy recomputation and original native-table comparison; no geometry implementation import",
              "cases": case_audits, "lap_records": all_records, "native_laps_checked": len(all_records), "test_laps_checked": len(tests),
              "script_sha256": file_sha256(__file__)}
    result["content_sha256"] = payload_sha256(result)
    write_manifest(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, dest="input_path")
    parser.add_argument("--development", required=True, type=Path)
    parser.add_argument("--retrospective", required=True, type=Path)
    parser.add_argument("--archives", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.input_path, args.development, args.retrospective, args.archives, args.output)
    print(json.dumps({k: result[k] for k in ("verified", "native_laps_checked", "test_laps_checked", "content_sha256")}, indent=2))
