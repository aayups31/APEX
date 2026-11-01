"""Independent catalog/action inspection and actual-copy artifact boundaries."""
from __future__ import annotations

import argparse
import copy
import shutil
from pathlib import Path

import numpy as np
from apexsim.examples.recovery_study import VERSION as RECOVERY_VERSION
from apexsim.examples.recovery_study import load_recovery, load_recovery_inputs
from apexsim.examples.support_study import VERSION as SUPPORT_VERSION
from apexsim.examples.support_study import load_support, load_support_detector
from apexsim.provenance import payload_sha256, write_manifest
from apexsim.research.evidence import finish_run, read_json, seal
from apexsim.research.support_fallback import support_score


def check_catalog(root: Path, kind: str, result: dict) -> None:
    inputs = root/"inputs" if kind == "recovery" else root/"detector/recovery/inputs"
    _, _, header, _, _ = load_recovery_inputs(inputs)
    catalog = [r for r in header["cases"] if r["role"] == "test"]
    expected = set()
    for row in catalog:
        if kind == "recovery":
            recipes = [(a, s, .02) for a in ("transparent", "learned") for s in ("nominal", "pulse_left", "pulse_right")]
            recipes += [("learned", "nominal", .01)]
        else:
            recipes = [(a, "nominal", .02) for a in ("unguarded", "guarded", "transparent")]
            recipes += [(a, s, .02) for a in ("unguarded", "guarded") for s in ("feature_shift", "residual_bias", "nonfinite")]
            recipes += [("guarded", "residual_bias", .01)]
            recipes += [("guarded", s, .02) for s in ("missing_map", "untrusted_state", "vehicle_mismatch")]
        expected.update(a+"__"+row["lap_id"]+"__"+s+"__"+str(step) for a, s, step in recipes)
    if kind == "recovery":
        expected.add("learned__"+catalog[0]["lap_id"]+"__challenge__0.02")
    actual = [r["case_id"] for r in result["cases"]]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("Independent complete physical/failure/abstention catalog mismatch")


def inspect_actions(root: Path, result: dict) -> dict:
    maximum_angle, maximum_rate, maximum_brake, maximum_drive, count = 0., 0., 0., 0., 0
    with np.load(root/"trajectories.npz", allow_pickle=False) as archive:
        for case in result["cases"]:
            key = case["case_id"]
            states, controls = archive[key+"__states"], archive[key+"__controls"]
            assert np.isfinite(states).all() and np.isfinite(controls).all()
            assert np.min(states[:, 3]) >= 5 and np.max(states[:, 3]) <= 110
            assert np.max(abs(np.arctan2(states[:, 4], states[:, 3]))) <= .35 and np.max(abs(states[:, 5])) <= 2
            if not len(controls):
                assert case["abstained"] and len(states) == 1
                continue
            assert len(states) == len(controls)+1
            angle = float(np.max(abs(controls[:, 0])))
            rate = float(np.max(abs(controls[:, 0]-np.r_[0., controls[:-1, 0]]))/.1)
            brake = float(np.max(np.maximum(0, -controls[:, 1]-controls[:, 2])))
            drive = float(np.max(np.maximum(0, controls[:, 2])*states[:-1, 3]))
            assert angle <= .6+1e-12 and rate <= 1.5+1e-10 and brake <= 40000+1e-8 and drive <= 680800+1e-6
            maximum_angle, maximum_rate = max(maximum_angle, angle), max(maximum_rate, rate)
            maximum_brake, maximum_drive = max(maximum_brake, brake), max(maximum_drive, drive)
            count += len(controls)
    return {"verified": True, "held_actions": count, "maximum_steering_rad": maximum_angle,
            "maximum_steering_rate_radps": maximum_rate, "maximum_brake_force_n": maximum_brake,
            "maximum_rear_drive_power_w": maximum_drive, "scope": "SAVED_ACTION_AND_STATE_PRIOR_BOUND_INSPECTION; DYNAMICS_HAVE_SEPARATE_REPLAY"}


def expected_rejection(operation, pattern):
    try:
        operation()
    except ValueError as exc:
        if pattern not in str(exc):
            raise
        return str(exc)
    raise AssertionError("Corrupted evidence was accepted")


def check(study: Path, output: Path, kind: str) -> dict:
    if output.exists() or output.resolve().is_relative_to(study.resolve()):
        raise ValueError("Boundary output must be fresh and outside study")
    load = load_recovery if kind == "recovery" else load_support
    summary, result = load(study)
    check_catalog(study, kind, result)
    bounds = inspect_actions(study, result)
    output.mkdir(parents=True)
    moved = output/"portable"
    shutil.copytree(study, moved)
    assert load(moved)[0]["content_sha256"] == summary["content_sha256"]
    bad = copy.deepcopy(result)
    bad["cases"].pop()
    catalog_rejection = expected_rejection(lambda: check_catalog(moved, kind, bad), "catalog mismatch")
    payload = moved/"trajectories.npz"
    original = payload.read_bytes()
    payload.write_bytes(b"corrupt")
    byte_rejection = expected_rejection(lambda: load(moved), "inventory")
    payload.write_bytes(original)
    header_path = moved/("inputs/reference/development/dataset/inputs.json" if kind == "recovery" else "detector/recovery/inputs/reference/development/dataset/inputs.json")
    original_header = header_path.read_bytes()
    header = read_json(header_path)
    header["cases"][0]["event_id"] = "F1_2024_R04"
    header_path.unlink()
    write_manifest(header_path, header)
    reserved_rejection = expected_rejection(lambda: load(moved), "Permanent benchmark event")
    header_path.write_bytes(original_header)
    # The complete catalog was rebuilt independently from frozen source identities.
    # Reseal a removed case and demonstrate that hash integrity alone is insufficient.
    old_summary = read_json(moved/"summary.json")
    original_summary, original_manifest, original_results = [(moved/n).read_bytes() for n in ("summary.json", "manifest.json", "results.json")]
    for name in ("summary.json", "manifest.json", "results.json"):
        (moved/name).unlink()
    old_summary.pop("content_sha256")
    old_summary["results_sha256"] = payload_sha256(bad)
    write_manifest(moved/"results.json", bad)
    finish_run(moved, RECOVERY_VERSION if kind == "recovery" else SUPPORT_VERSION, old_summary)
    _, resealed = load(moved)
    resealed_rejection = expected_rejection(lambda: check_catalog(moved, kind, resealed), "catalog mismatch")
    for name, value in zip(("summary.json", "manifest.json", "results.json"), (original_summary, original_manifest, original_results), strict=True):
        (moved/name).write_bytes(value)
    detector_rejection, probes = None, None
    if kind == "support":
        _, model = load_support_detector(study/"detector")
        center, width, cutoff = np.array(model["center"]), np.array(model["half_range"]), model["cutoff"]
        outside, inside = [], []
        for coordinate in range(8):
            for sign in (-1, 1):
                a, b = center.copy(), center.copy()
                a[coordinate] += sign*1.01*cutoff*width[coordinate]
                b[coordinate] += sign*.99*cutoff*width[coordinate]
                outside.append(support_score(model, a) > cutoff)
                inside.append(support_score(model, b) <= cutoff)
        blind_spot = support_score(model, center+.99*cutoff*width) <= cutoff
        assert all(outside) and all(inside) and blind_spot
        probes = {"outside_axis_points_rejected": sum(outside), "inside_axis_points_supported": sum(inside),
                  "joint_in_box_corner_not_rejected": bool(blind_spot),
                  "scope": "CONSTRUCTED_API_BOUNDARY_AND_STRUCTURAL_BLIND_SPOT_CHECKS; NOT_REAL_WORLD_OOD_ACCURACY"}
        detector = output/"changed-detector"
        shutil.copytree(study/"detector", detector)
        old = read_json(detector/"summary.json")
        data = read_json(detector/"detector.json")
        data["model"]["cutoff"] *= 2
        for name in ("summary.json", "manifest.json", "detector.json"):
            (detector/name).unlink()
        old.pop("content_sha256")
        old["model_sha256"] = payload_sha256(data["model"])
        write_manifest(detector/"detector.json", data)
        finish_run(detector, SUPPORT_VERSION+"-detector", old)
        detector_rejection = expected_rejection(lambda: load_support_detector(detector), "numeric mismatch")
    receipt = seal({"schema_version": "apex-"+kind+"-boundary-v1", "summary_sha256": summary["content_sha256"], "verified": True,
                    "portable_source_binding": True, "independent_catalog": True, "action_bounds": bounds,
                    "corrupted_payload_rejection": byte_rejection, "missing_case_rejection": catalog_rejection,
                    "resealed_missing_case_independent_catalog_rejection": resealed_rejection,
                    "reserved_header_rejection": reserved_rejection, "resealed_changed_cutoff_rejection": detector_rejection,
                    "actual_detector_boundary_probes": probes,
                    "scope": "ACTUAL_ARTIFACT_COPIES; FULL_SCIENTIFIC_REGENERATION_HAS_SEPARATE_BOUND_RECEIPT"})
    write_manifest(output/"receipt.json", receipt)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kind", choices=("recovery", "support"), required=True)
    args = parser.parse_args()
    print(check(args.study, args.output, args.kind))
