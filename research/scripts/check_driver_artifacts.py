"""Exercise R035 portability and adversarial source/choice/payload integrity on real copies."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from apexsim.examples.driver_study import (
    VERSION,
    load_calibration,
    load_driver_study,
    verify_driver_calibration,
)
from apexsim.provenance import payload_sha256, write_manifest
from apexsim.research.evidence import finish_run, read_json, seal


def expect_rejection(operation):
    try:
        operation()
    except ValueError as exc:
        return str(exc)
    raise AssertionError("Adversarial R035 artifact was accepted")


def check(study: Path, output: Path):
    if output.exists() or output.resolve().is_relative_to(study.resolve()):
        raise ValueError("Artifact check output must be fresh and outside study")
    source, _ = load_driver_study(study)
    output.mkdir(parents=True)
    portable = output/"portable"
    shutil.copytree(study, portable)
    copied, _ = load_driver_study(portable)
    if copied != source:
        raise ValueError("Portable source identity changed")
    replay = verify_driver_calibration(portable/"calibration")
    corrupt = output/"corrupt"
    shutil.copytree(study, corrupt)
    (corrupt/"trajectories.npz").write_bytes(b"intentional adversarial payload")
    payload_failure = expect_rejection(lambda: load_driver_study(corrupt))
    choice = output/"changed-choice"
    shutil.copytree(study/"calibration", choice)
    summary, calibration, _ = load_calibration(choice)
    calibration["selected"] = {"fraction": .35, "maximum_mps": 60.}
    summary.pop("content_sha256")
    summary["selected"] = calibration["selected"]
    summary["calibration_sha256"] = payload_sha256(calibration)
    for name in ("summary.json", "manifest.json", "calibration.json"):
        (choice/name).unlink()
    write_manifest(choice/"calibration.json", calibration)
    finish_run(choice, VERSION+"-calibration", summary)
    choice_failure = expect_rejection(lambda: verify_driver_calibration(choice))
    protected = output/"protected"
    shutil.copytree(study/"calibration", protected)
    header = read_json(protected/"recorded/inputs.json")
    header["laps"][0]["event_id"] = "F1_2024_R04"
    (protected/"recorded/inputs.json").unlink()
    write_manifest(protected/"recorded/inputs.json", header)
    guard_failure = expect_rejection(lambda: load_calibration(protected))
    if "Permanent benchmark event" not in guard_failure:
        raise AssertionError("Expected actual protected benchmark rejection before payload reads")
    receipt = seal({"schema_version": VERSION+"-real-artifact-boundary-check-v1", "verified": True,
                    "summary_sha256": source["content_sha256"], "portable_inventory_binding": True,
                    "portable_calibration_scientific_replay": replay, "tampered_payload_rejection": payload_failure,
                    "resealed_changed_choice_rejection": choice_failure, "protected_header_rejection": guard_failure,
                    "scope": "REAL_PUBLIC_ARTIFACT_COPIES; FULL_SCIENTIFIC_TRAJECTORY_REPLAY_HAS_SEPARATE_RECEIPT"})
    write_manifest(output/"receipt.json", receipt)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(check(args.study, args.output))
