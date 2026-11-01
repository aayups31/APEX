"""Real R036 artifact copies: portability, reserved events, payload and choice integrity."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from apexsim.examples.imitation_study import (
    VERSION,
    load_development,
    load_imitation_evaluation,
    verify_imitation_development,
)
from apexsim.provenance import payload_sha256, write_manifest
from apexsim.research.evidence import finish_run, read_json, seal


def rejected(operation):
    try:
        operation()
    except ValueError as exc:
        return str(exc)
    raise AssertionError("Corrupted R036 artifact was accepted")


def check(study: Path, output: Path) -> dict:
    if output.exists() or output.resolve().is_relative_to(study.resolve()):
        raise ValueError("R036 artifact-check output must be fresh and outside study")
    original, _ = load_imitation_evaluation(study)
    output.mkdir(parents=True)
    portable = output/"portable"
    shutil.copytree(study, portable)
    moved, _ = load_imitation_evaluation(portable)
    if moved != original:
        raise ValueError("Portable R036 identity changed")
    audit = verify_imitation_development(portable/"development", replay_dynamics=False)
    corrupt = output/"corrupt"
    shutil.copytree(study, corrupt)
    (corrupt/"trajectories.npz").write_bytes(b"intentional adversarial payload")
    payload_failure = rejected(lambda: load_imitation_evaluation(corrupt))
    choice = output/"changed-choice"
    shutil.copytree(study/"development", choice)
    summary, result, _, _, _ = load_development(choice)
    alternative = next(name for name in result["models"] if name != result["selected"] and name.startswith("bc_d1"))
    summary.pop("content_sha256")
    summary["selected"] = result["selected"] = alternative
    summary["selected_model_sha256"] = payload_sha256(result["models"][alternative])
    summary["development_sha256"] = payload_sha256(result)
    for name in ("summary.json", "manifest.json", "development.json"):
        (choice/name).unlink()
    write_manifest(choice/"development.json", result)
    finish_run(choice, VERSION+"-development", summary)
    choice_failure = rejected(lambda: verify_imitation_development(choice, replay_dynamics=False))
    protected = output/"protected"
    shutil.copytree(study/"development", protected)
    header = read_json(protected/"dataset/inputs.json")
    header["cases"][0]["event_id"] = "F1_2024_R04"
    (protected/"dataset/inputs.json").unlink()
    write_manifest(protected/"dataset/inputs.json", header)
    guard_failure = rejected(lambda: load_development(protected))
    if "Permanent benchmark event" not in guard_failure:
        raise AssertionError("Actual reserved-event guard was not reached before binary reads")
    receipt = seal({"schema_version": VERSION+"-boundary-check-v1", "verified": True,
                    "summary_sha256": original["content_sha256"], "portable_source_model_binding": True,
                    "portable_development_equation_audit": audit, "corrupted_payload_rejection": payload_failure,
                    "resealed_changed_model_choice_rejection": choice_failure, "reserved_header_rejection": guard_failure,
                    "scope": "REAL_PUBLIC_ARTIFACT_COPIES; FULL_TRAJECTORY_REPLAY_HAS_SEPARATE_BOUND_RECEIPT"})
    write_manifest(output/"receipt.json", receipt)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(check(args.study, args.output))
