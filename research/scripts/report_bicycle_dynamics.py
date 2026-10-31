"""Publish verified R031 synthetic evidence and an inspectable static figure."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from apexsim.examples.bicycle_study import (
    audit_bicycle_study,
    load_bicycle_study,
    verify_bicycle_study,
)
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research.bicycle import axle_force


def publish(study: Path, output: Path) -> dict:
    """Verify before publication; keep source trajectories in the ignored run folder."""
    if output.exists():
        raise FileExistsError("R031 publication output must be fresh")
    summary, results = load_bicycle_study(study)
    verified, audit = verify_bicycle_study(study), audit_bicycle_study(study)
    if not results["task_closure_eligible"]:
        raise ValueError("Cannot publish a rejected R031 run as accepted")
    evidence = {"schema_version": "apex-bicycle-publication-v1", "study_summary": summary,
                "results": results, "verification": verified, "independent_audit": audit,
                "study_manifest_sha256": file_sha256(study/"manifest.json"),
                "study_manifest": json.loads((study/"manifest.json").read_text(encoding="utf-8"))}
    evidence["content_sha256"] = payload_sha256(evidence)
    output.mkdir(parents=True, exist_ok=False)
    write_manifest(output/"bicycle-dynamics-evidence.json", evidence)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, panels = plt.subplots(2, 2, figsize=(13, 8.5), constrained_layout=True)
    fig.suptitle("APEX R031 | synthetic bicycle force and numerical validation", fontsize=16)
    with np.load(study/"trajectories.npz", allow_pickle=False) as saved:
        ax = panels[0, 0]
        for case, label in (("left", "Left steering"), ("right", "Right steering"), ("pulse", "Steering pulse")):
            ax.plot(saved[case+"__time_s"], saved[case+"__rk4_01"][:, 5], label=label)
        ax.set(title="Supported yaw response", xlabel="Time (s)", ylabel="Yaw rate (rad/s)")
        ax.legend(loc="best")
        ax = panels[0, 1]
        prefix = saved["near_limit_drive__rk4_01"]
        ax.plot(saved["near_limit_drive__time_s"], prefix[:, 5], "o-", label="Supported output prefix")
        rejection = next(c for c in results["cases"] if c["name"] == "near_limit_drive")
        ax.scatter([rejection["independent_exit_time_s"]], [saved["near_limit_drive__boundary_state"][5]],
                   color="#bb3333", marker="x", s=70, label="Independent boundary root", zorder=3)
        ax.axhline(2, color="#bb3333", linestyle="--", linewidth=1, label="Declared yaw support limit")
        ax.set(title="Full rear drive: explicit abstention", xlabel="Time (s)", ylabel="Yaw rate (rad/s)")
        ax.legend(loc="upper left", fontsize=8)
        ax = panels[1, 0]
        cases = ("left", "combined_brake", "pulse", "near_limit_drive")
        x = np.arange(len(cases))
        for i, (suffix, label) in enumerate((("rk4_02", ".02 s"), ("rk4_01", ".01 s"), ("rk4_005", ".005 s"))):
            values = [max(abs(saved[c+"__"+suffix][:, 4]-saved[c+"__dop853"][:, 4])) for c in cases]
            ax.bar(x+(i-1)*.24, values, width=.23, label=label)
        ax.set_xticks(x, ["Left", "Brake + turn", "Pulse", "Drive limit*"], fontsize=9)
        ax.set_yscale("log")
        ax.set(title="Independent lateral-speed integration error", ylabel="Maximum |vy − reference| (m/s)")
        ax.legend(title="RK4 maximum step", fontsize=8, title_fontsize=8, loc="upper left", ncol=3)
        ax.set_xlabel("* Drive limit: supported prefix only; full case abstains", fontsize=8)
    ax = panels[1, 1]
    alpha = np.linspace(-.2, .2, 201)
    for fraction in (0., .6, .9, 1.):
        force = [axle_force(float(a), fraction*1000, 1000, 20000, 1, 1).fy_n/1000 for a in alpha]
        ax.plot(alpha, force, label=f"|Fx| / capacity = {fraction:g}")
    ax.set(title="Declared combined-grip prior", xlabel="Axle slip (rad)", ylabel="Fy / lateral capacity")
    ax.legend(fontsize=8)
    for ax in panels.flat:
        ax.grid(alpha=.18)
    fig.savefig(output/"bicycle-dynamics-summary.png", dpi=170)
    plt.close(fig)
    manifest = {"schema_version": "apex-bicycle-publication-manifest-v1", "evidence_sha256": evidence["content_sha256"],
                "publisher_sha256": file_sha256(__file__),
                "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}}
    manifest["content_sha256"] = payload_sha256(manifest)
    write_manifest(output/"bicycle-dynamics-manifest.json", manifest)
    return {"evidence_sha256": evidence["content_sha256"], "study_sha256": summary["content_sha256"],
            "supported_cases": results["supported_cases"], "abstention_challenges": results["abstention_challenges"],
            "maximum_independent_error_by_state": audit["maximum_error_by_state"], "state_units": audit["state_units"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(publish(args.study, args.output), indent=2))
