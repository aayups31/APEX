"""Publish bound R032/R033 verification receipts and inspectable scientific figures."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from apexsim.examples.aero_study import load_aero_study
from apexsim.examples.recorded_replay import load_recorded_replay
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.aero_bicycle import AeroParameters, solve_axle_loads
from apexsim.research.bicycle import BicycleControl, BicycleParameters, BicycleState
from apexsim.research.evidence import read_json, seal


def publish(aero: Path, recorded: Path, receipts: list[Path], output: Path) -> dict:
    """Use exact run-bound receipts; scientific replay is performed before publication."""
    if output.exists():
        raise FileExistsError("Publication output must be fresh")
    a_summary, a_result = load_aero_study(aero)
    r_summary, r_result = load_recorded_replay(recorded)
    verified = [read_json(p) for p in receipts]
    for receipt, expected in zip(verified, [a_summary, a_summary, r_summary, r_summary], strict=True):
        if not receipt["verified"] or receipt["summary_sha256"] != expected["content_sha256"]:
            raise ValueError("Publication receipt does not bind the exact completed run")
    if not a_result["task_closure_eligible"] or not r_result["task_closure_eligible"]:
        raise ValueError("Cannot publish rejected or simulated-only studies as accepted")
    output.mkdir(parents=True, exist_ok=False)
    evidence = []
    for prefix, root, summary, result, replay, audit in (
            ("aero-load-transfer", aero, a_summary, a_result, verified[0], verified[1]),
            ("recorded-replay-alignment", recorded, r_summary, r_result, verified[2], verified[3])):
        payload = seal({"schema_version": "apex-"+prefix+"-publication-v1", "study_summary": summary,
                        "results": result, "verification": replay, "independent_audit": audit,
                        "run_manifest_sha256": file_sha256(root/"manifest.json"), "run_manifest": read_json(root/"manifest.json")})
        write_manifest(output/(prefix+"-evidence.json"), payload)
        evidence.append(payload["content_sha256"])
    fig, axes = plt.subplots(2, 2, figsize=(15, 9.5), constrained_layout=True)
    fig.suptitle("APEX R032/R033 | numerical physics and native-source alignment", fontsize=16)
    ax = axes[0, 0]
    loads = [solve_axle_loads(BicycleState(vx_mps=50), BicycleControl(rear_fx_request_n=float(f)),
                              BicycleParameters(), AeroParameters()) for f in np.linspace(-8000, 8000, 81)]
    ax.plot([v.tyre_body_fx_n for v in loads], [v.front.normal_n for v in loads], label="Front axle")
    ax.plot([v.tyre_body_fx_n for v in loads], [v.rear.normal_n for v in loads], label="Rear axle")
    ax.set(title="R032 synthetic load transfer at 50 m/s", xlabel="Applied tyre force along body x (N)", ylabel="Normal load (N)")
    ax.legend()
    ax = axes[0, 1]
    names = ("left", "combined", "pulse")
    x = np.arange(3)
    for i, label in enumerate((".02 s", ".01 s", ".005 s")):
        values = [next(c for c in a_result["cases"] if c["name"] == name)["maximum_dop853_error_by_step_and_state"][i][4] for name in names]
        ax.bar(x+(i-1)*.24, values, width=.23, label=label)
    ax.set_xticks(x, ["Left steer", "Brake + turn", "Steering pulse"])
    ax.set_yscale("log")
    ax.set(title="R032 synthetic integration difference", ylabel="Maximum lateral-speed difference (m/s)")
    ax.legend(title="RK4 maximum step", ncol=3, loc="upper left", fontsize=8, title_fontsize=8)
    ax = axes[1, 0]
    groups = r_result["event_driver_groups"]
    ax.bar(np.arange(len(groups)), [g["joint_row_coverage"]*100 for g in groups.values()], color="#3b7ca6")
    ax.axhline(90, linestyle="--", color="#aa3333", linewidth=1, label="Frozen group gate >90%")
    labels = [k[3:7]+" R"+k[9:11]+" / "+k.split("/")[1] for k in groups]
    ax.set_xticks(np.arange(len(groups)), labels, rotation=30, ha="right", fontsize=8)
    ax.set(ylim=(0, 105), title="R033 public joint-observation coverage", ylabel="All native car rows (%)")
    ax.legend(loc="lower right", fontsize=8)
    ax = axes[1, 1]
    f = r_result["coverage_fractions"]
    labels = ["Recorded controls", "RPM / gear", "Causal position", "Joint observations", "Native intervals", "Full bicycle inputs"]
    values = [f["controls_observed"]*100, f["engine_observed"]*100, f["position_observed"]*100,
              f["joint_observed"]*100, f["joint_interval_duration"]*100, 0.]
    ax.barh(np.arange(6), values, color=["#3b7ca6"]*5+["#aa3333"])
    ax.set_yticks(np.arange(6), labels)
    for i, value in enumerate(values):
        ax.text(min(value+1, 101), i, f"{value:.2f}%", va="center", fontsize=8)
    ax.invert_yaxis()
    ax.set(xlim=(0, 113), title="R033 observed coverage and missing chassis inputs", xlabel="Coverage (%); intervals use complete lap time")
    ax.text(.01, -.24, "Full bicycle input coverage is 0%: missing states remain UNKNOWN.", transform=ax.transAxes, fontsize=8)
    for ax in axes.flat:
        ax.grid(alpha=.15)
        ax.set_axisbelow(True)
    fig.savefig(output/"vehicle-replay-summary.png", dpi=160)
    plt.close(fig)
    manifest = seal({"schema_version": "apex-vehicle-replay-publication-manifest-v1", "evidence_sha256": evidence,
                     "publisher_sha256": file_sha256(__file__),
                     "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}})
    write_manifest(output/"vehicle-replay-manifest.json", manifest)
    return {"evidence_sha256": evidence, "manifest_sha256": manifest["content_sha256"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aero", type=Path, required=True)
    parser.add_argument("--recorded", type=Path, required=True)
    parser.add_argument("--receipt", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    print(publish(options.aero, options.recorded, options.receipt, options.output))
