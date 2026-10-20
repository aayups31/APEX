"""R029 v2: native observations, explicit holes, multi-lap support and sensitivity."""
from __future__ import annotations

from dataclasses import asdict

import numpy as np
from scipy.spatial import cKDTree

from apexsim.research.reference_geometry import (
    GeometryConfig,
    ReferenceCurve,
    chord_parameter,
    fit_reference,
    reconstruction_gate,
    register_lap,
)

CANDIDATES_V2 = tuple(GeometryConfig(k, a) for k, a in ((48, .05), (96, .05), (96, .5), (160, .05), (160, .5), (96, .005)))


def supported_windows(chord_m: np.ndarray, intervals: np.ndarray, centers: np.ndarray, radius_m: float = 25.) -> np.ndarray:
    """A stencil is supported only if its whole open span avoids unsupported intervals."""
    chord_m, centers = np.asarray(chord_m, float), np.asarray(centers, float)
    intervals = np.asarray(intervals, bool)
    if chord_m.ndim != 1 or centers.ndim != 1 or intervals.shape != (len(chord_m)-1,) or np.any(np.diff(chord_m) <= 0) or not np.isfinite(chord_m).all() or not np.isfinite(centers).all() or radius_m <= 0:
        raise ValueError("Invalid supported-window coordinates")
    bad = np.flatnonzero(~intervals)
    crosses = (centers[:, None]+radius_m > chord_m[bad])&(centers[:, None]-radius_m < chord_m[bad+1])
    return (centers-radius_m >= chord_m[0])&(centers+radius_m <= chord_m[-1])&~crosses.any(axis=1)


def supported_polyline_distances(points: np.ndarray, line: np.ndarray, intervals: np.ndarray) -> np.ndarray:
    """Distance to observed vertices and supported segments; no invented closing/gap chord."""
    points, line = np.asarray(points, float), np.asarray(line, float)
    intervals = np.asarray(intervals, bool)
    if line.ndim != 2 or line.shape[1] != 2 or len(line) < 2 or intervals.shape != (len(line)-1,) or not np.isfinite(line).all() or not np.isfinite(points).all():
        raise ValueError("Invalid observed polyline support")
    result = cKDTree(line).query(points)[0]
    start, direction = line[:-1][intervals], np.diff(line, axis=0)[intervals]
    length2 = np.sum(direction**2, axis=1)
    keep = length2 > 1e-18
    start, direction, length2 = start[keep], direction[keep], length2[keep]
    if not len(start):
        return result
    for lo in range(0, len(points), 256):
        delta = points[lo:lo+256, None, :]-start[None, :, :]
        along = np.clip(np.sum(delta*direction[None, :, :], axis=2)/length2, 0., 1.)
        residual = delta-along[:, :, None]*direction[None, :, :]
        result[lo:lo+256] = np.minimum(result[lo:lo+256], np.sqrt(np.min(np.sum(residual**2, axis=2), axis=1)))
    return result


def evaluate_supported(curve: ReferenceCurve, lap: dict, aligned_xy: np.ndarray, baseline_xy: np.ndarray, baseline_intervals: np.ndarray) -> tuple[dict, dict]:
    """Score every observed vertex; curvature targets abstain on missing source stencils."""
    support = np.asarray(lap["interval_supported"], bool)
    projection = curve.project(aligned_xy)
    distances = projection["distance_m"]
    raw = supported_polyline_distances(aligned_xy, baseline_xy, baseline_intervals)
    phase, length = chord_parameter(aligned_xy)
    centers = np.arange(25., length-25., 25.)
    valid = supported_windows(phase*length, support, centers)
    proxy = np.full(len(centers), np.nan)
    model = np.full(len(centers), np.nan)
    coarse_xy = np.full((len(centers), 2), np.nan)
    points = [np.column_stack([np.interp(centers[valid]+offset, phase*length, aligned_xy[:, axis]) for axis in (0, 1)]) for offset in (-25., 0., 25.)]
    if valid.any():
        a, b = points[1]-points[0], points[2]-points[1]
        turning = np.arctan2(a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0], np.sum(a*b, axis=1))
        proxy[valid] = turning/((np.linalg.norm(a, axis=1)+np.linalg.norm(b, axis=1))/2)
        coarse_xy[valid] = points[1]
        model[valid] = curve.project(points[1])["curvature_1pm"]
    differences = abs(model[valid]-proxy[valid])
    unwrapped = np.unwrap(projection["station_m"]/curve.length_m*2*np.pi)*curve.length_m/(2*np.pi)
    metrics = {"xy_rmse_m": float(np.sqrt(np.mean(distances**2))), "xy_p95_m": float(np.quantile(distances, .95)),
               "xy_max_m": float(distances.max()), "raw_polyline_p95_m": float(np.quantile(raw, .95)),
               "p95_minus_raw_polyline_m": float(np.quantile(distances, .95)-np.quantile(raw, .95)),
               "backward_fraction": float(np.mean(np.diff(unwrapped) < -1e-6)),
               "coarse_curvature_mae_1pm": float(np.mean(differences)) if valid.any() else None,
               "coarse_curvature_p95_1pm": float(np.quantile(differences, .95)) if valid.any() else None,
               "coarse_supported_targets": int(valid.sum()), "coarse_total_targets": len(valid),
               "coarse_support_fraction": float(valid.mean()) if len(valid) else 0., "coarse_step_m": 25.,
               "curvature_target_quality": "SUPPORTED_COARSE_CHORD_PROXY_NOT_SURVEYED"}
    saved = {**projection, "raw_polyline_distance_m": raw, "interval_supported": support,
             "coarse_station_chord_m": centers, "coarse_supported": valid, "coarse_xy_m": coarse_xy,
             "coarse_curvature_proxy_1pm": proxy, "coarse_model_curvature_1pm": model}
    return metrics, saved


def station_support(length_m: float, stations: list[np.ndarray], intervals: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Count distinct donor laps, using only positive <=100m supported projected spans."""
    if length_m <= 0 or not np.isfinite(length_m) or len(stations) != len(intervals):
        raise ValueError("Invalid station support inputs")
    query = np.arange(0., length_m, 10.)
    donors = []
    for station, supported in zip(stations, intervals, strict=True):
        station = np.asarray(station, float)
        supported = np.asarray(supported, bool)
        if station.ndim != 1 or supported.shape != (len(station)-1,) or not np.isfinite(station).all():
            raise ValueError("Invalid projected native interval support")
        unwrapped = np.unwrap(station/length_m*2*np.pi)*length_m/(2*np.pi)
        steps = np.diff(unwrapped)
        good = supported&(steps > 0)&(steps <= 100.)
        delta = np.mod(query[:, None]-unwrapped[:-1][good], length_m)
        # One micrometre handles arithmetic at periodic endpoints, not source holes.
        donors.append(np.any((delta <= steps[good]+1e-6)|(length_m-delta <= 1e-6), axis=1))
    return query, np.asarray(donors, bool)


def test_lap_passed(m: dict) -> bool:
    return bool(m["xy_rmse_m"] <= 6 and m["xy_p95_m"] <= 12 and m["xy_max_m"] <= 30
                and m["p95_minus_raw_polyline_m"] <= 2 and m["backward_fraction"] <= .02
                and m["coarse_support_fraction"] >= .75 and m["coarse_supported_targets"] >= 100
                and m["coarse_curvature_mae_1pm"] is not None and m["coarse_curvature_mae_1pm"] <= .003
                and m["coarse_curvature_p95_1pm"] <= .015)


def refine_rigid_pose(xy: np.ndarray, aligned: np.ndarray, registration: dict, curve: ReferenceCurve) -> tuple[np.ndarray, dict]:
    """Eight proper rigid ICP steps against a fixed curve; never change shape coefficients."""
    rotation = np.asarray(registration["rotation"], float)
    translation = np.asarray(registration["translation_m"], float)
    rms = [float(np.sqrt(np.mean(curve.project(aligned)["distance_m"]**2)))]
    initial = {"rotation": rotation.tolist(), "translation_m": translation.tolist(), "phase_rms_after_m": registration["rms_after_m"]}
    for _ in range(8):
        targets = curve.project(aligned)["xy_m"]
        xc, yc = aligned.mean(axis=0), targets.mean(axis=0)
        u, _, vt = np.linalg.svd((aligned-xc).T@(targets-yc))
        step_r = u@np.diag([1., np.linalg.det(u@vt)])@vt
        step_t = yc-xc@step_r
        rotation, translation = rotation@step_r, translation@step_r+step_t
        aligned = xy@rotation+translation
        rms.append(float(np.sqrt(np.mean(curve.project(aligned)["distance_m"]**2))))
        if rms[-1] > rms[-2]+1e-6:
            raise ValueError("Rigid closest-curve registration increased native RMS")
    result = {**registration, "rotation": rotation.tolist(), "translation_m": translation.tolist(),
              "determinant": float(np.linalg.det(rotation)), "initial_phase_registration": initial,
              "rms_after_m": rms[-1], "rms_after_definition": "Native nearest-curve RMS after rigid pose refinement",
              "method": "KABSCH_512_THEN_8_FIXED_CURVE_RIGID_ICP_STEPS", "nearest_curve_rms_steps_m": rms,
              "shape_coefficients_changed": False}
    return aligned, result


def fit_supported_case(laps: list[dict], track: str, *, expected_counts: tuple[int, int, int] = (10, 10, 12), refine_test_pose: bool = False) -> tuple[dict, dict]:
    """Fit/choose on train/validation only, then evaluate native support and frozen test gates."""
    groups = [[lap for lap in laps if lap["metadata"]["role"] == role] for role in ("train", "validation", "test")]
    if tuple(map(len, groups)) != expected_counts:
        raise ValueError("Observed-support study lap counts differ from its frozen profile")
    train, validation, _tests = groups
    aligned, registrations = {}, {}
    for lap in laps:
        key = lap["metadata"]["lap_id"]
        aligned[key], registrations[key] = register_lap(lap["xy_m"], train[0]["xy_m"])
    training_xy = [aligned[lap["metadata"]["lap_id"]] for lap in train]
    candidates, eligible = [], []
    for index, config in enumerate(CANDIDATES_V2):
        curve = fit_reference(training_xy, config, track)
        geometric = reconstruction_gate(curve, training_xy, [])["geometry_passed"]
        losses = [float(np.mean(curve.project(aligned[lap["metadata"]["lap_id"]], refine=False)["distance_m"]**2)) for lap in validation]
        candidates.append({"config": asdict(config), "training_geometry_passed": geometric,
                           "validation_lap_mse_m2": losses, "mean_validation_mse_m2": float(np.mean(losses))})
        if geometric:
            eligible.append(index)
    if not eligible:
        raise ValueError("No frozen candidate passes training-only geometry sanity")
    selected = min(eligible, key=lambda i: candidates[i]["mean_validation_mse_m2"])
    curve = fit_reference(training_xy, CANDIDATES_V2[selected], track)
    saved, metrics, station_arrays, support_arrays = {}, [], [], []
    for lap in laps:
        key = lap["metadata"]["lap_id"]
        if refine_test_pose and lap["metadata"]["role"] == "test":
            aligned[key], registrations[key] = refine_rigid_pose(lap["xy_m"], aligned[key], registrations[key], curve)
        result, arrays = evaluate_supported(curve, lap, aligned[key], training_xy[0], train[0]["interval_supported"])
        metrics.append({**lap["metadata"], "registration": registrations[key], **result})
        saved[key+"_aligned_xy"] = aligned[key]
        saved.update({key+"_"+name: values for name, values in arrays.items()})
        if lap["metadata"]["role"] == "train":
            station_arrays.append(arrays["station_m"])
            support_arrays.append(lap["interval_supported"])
    support_query, donor_matrix = station_support(curve.length_m, station_arrays, support_arrays)
    counts = donor_matrix.sum(axis=0)
    query = np.linspace(0., curve.length_m, 2048, endpoint=False)
    full_xy, tangent, _ = curve.geometry(query)
    normal = np.column_stack((-tangent[:, 1], tangent[:, 0]))
    offsets, lengths = [], []
    for omit in range(len(train)):
        alternate = fit_reference([xy for i, xy in enumerate(training_xy) if i != omit], curve.config, track)
        other_xy, _, _ = alternate.geometry(query/curve.length_m*alternate.length_m)
        offsets.append(np.sum((other_xy-full_xy)*normal, axis=1))
        lengths.append(alternate.length_m)
    offsets = np.asarray(offsets)
    sensitivity = {"method": "leave-one-training-lap normal offsets; descriptive, not calibrated confidence",
                   "p95_absolute_normal_offset_m": float(np.quantile(abs(offsets), .95)),
                   "max_absolute_normal_offset_m": float(np.max(abs(offsets))), "leave_one_lap_lengths_m": lengths}
    geometry = reconstruction_gate(curve, training_xy, [])
    each = [test_lap_passed(m) for m in metrics if m["role"] == "test"]
    coverage = {"station_step_m": 10., "minimum_donor_laps": int(counts.min()),
                "supported_station_fraction": float(np.mean(counts >= 3)), "station_count": len(support_query),
                "supported_projected_step_limit_m": 100.}
    passed = bool(geometry["geometry_passed"] and bool(each) and all(each) and np.all(counts >= 3)
                  and sensitivity["p95_absolute_normal_offset_m"] <= 3 and sensitivity["max_absolute_normal_offset_m"] <= 8)
    gate = {**geometry, "passed": passed, "each_test_passed": each,
            "coverage_passed": bool(np.all(counts >= 3)), "sensitivity_passed": bool(sensitivity["p95_absolute_normal_offset_m"] <= 3 and sensitivity["max_absolute_normal_offset_m"] <= 8)}
    saved.update(coefficients=curve.coefficients, arc_u=curve.arc_u, arc_s=curve.arc_s,
                 support_station_m=support_query, support_donor_matrix=donor_matrix,
                 support_donor_counts=counts, sensitivity_station_m=query, sensitivity_normal_offsets_m=offsets)
    return {"track_id": track, "selected_config": asdict(curve.config), "selected_candidate_index": selected,
            "candidate_selection": candidates, "length_m": curve.length_m, "gate": gate, "lap_metrics": metrics,
            "coverage": coverage, "sensitivity": sensitivity, "frame_anchor_lap_id": train[0]["metadata"]["lap_id"],
            "geometry_truth": "RECONSTRUCTED_REFERENCE_RACING_TRACE_NOT_SURVEYED_CENTERLINE",
            "frame_truth": "CONDITIONAL_REGISTERED_SHAPE_AFTER_RIGID_POSE_OPTIMIZATION" if refine_test_pose else "LOCAL_SOURCE_XY; WHOLE_LAP_RIGID_REGISTRATION_FOR_SHAPE_EVALUATION"}, saved
