"""Publish source-bound R037/R038 comparisons; no policy fitting or gate changes."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from apexsim.examples.recovery_study import load_recovery
from apexsim.examples.support_study import load_support
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import read_json, seal


def publish(study: Path, receipt: Path, output: Path, kind: str) -> dict:
    if output.exists():
        raise ValueError("Publication output must be fresh")
    summary, result = (load_recovery if kind == "recovery" else load_support)(study)
    verification = read_json(receipt)
    if (not verification.get("verified") or verification.get("summary_sha256") != summary["content_sha256"]
            or verification.get("task_closure_eligible") != summary["task_closure_eligible"]):
        raise ValueError("Publication needs a run-bound full scientific replay receipt")
    compact = []
    for row in result["cases"]:
        decisions = row["decisions"]
        seam_drift = None
        if row["seam_states"]:
            states = np.array([r["state"] for r in row["seam_states"]])
            heading = states[:, 2]-states[0, 2]
            seam_drift = {"maximum_position_change_from_first_seam_m": float(max(np.linalg.norm(states[:, :2]-states[0, :2], axis=1))),
                          "maximum_body_velocity_change_mps": float(max(np.linalg.norm(states[:, 3:5]-states[0, 3:5], axis=1))),
                          "maximum_wrapped_heading_change_rad": float(max(abs(np.arctan2(np.sin(heading), np.cos(heading))))),
                          "maximum_yaw_rate_change_radps": float(max(abs(states[:, 5]-states[0, 5]))),
                          "scope": "POSTHOC_SAME_REFERENCE_PHASE_DIAGNOSTIC; NOT_A_NEW_ACCEPTANCE_GATE"}
        compact.append({**{k: v for k, v in row.items() if k != "decisions"},
                        "same_phase_drift": seam_drift,
                        "mode_counts": dict(Counter(d["mode"] for d in decisions)),
                        "reason_counts": dict(Counter(d["reason"] or "SUPPORTED" for d in decisions))})
    output.mkdir(parents=True)
    evidence = seal({"schema_version": "apex-"+kind+"-publication-v1", "summary": summary, "gate": result["gate"],
                     "cases": compact, "refinements": result["refinements"], "verification": verification,
                     "conditional_simulated_generic_prior_vehicle": True, "production_promotion": False,
                     "scope": "FINITE_REUSED_DEVELOPMENT_CONDITIONS; NO_REAL_CAR_PACE_OR_UNIVERSAL_SAFETY_CLAIM"})
    write_manifest(output/(kind+"-evidence.json"), evidence)
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    title = "APEX R037 continuous recovery" if kind == "recovery" else "APEX R038 empirical support and fallback"
    fig.suptitle(title+"\nConditional simulation | generic vehicle | supplied map | "+summary["profile"], fontsize=15)
    with np.load(study/"trajectories.npz", allow_pickle=False) as arrays:
        if kind == "recovery":
            ax = axes[0, 0]
            for actor in ("transparent", "learned"):
                for scenario, style in (("nominal", "-"), ("pulse_left", "--"), ("pulse_right", ":")):
                    rows = [r for r in result["cases"] if r["actor"] == actor and r["scenario"] == scenario and r["max_step_s"] == .02]
                    means = np.sqrt(np.mean([[v["rmse_m"]**2 for v in r["laps"]] for r in rows], axis=0))
                    ax.plot(np.arange(1, len(means)+1), means, style, marker="o", label=actor+" "+scenario.replace("pulse_", ""))
            ax.set(xlabel="Continuous lap", ylabel="Macro station RMSE (m)", title="Complete matched horizon; no seam resets")
            ax.legend(fontsize=8)
            ax = axes[0, 1]
            nominal = next(r for r in result["cases"] if r["actor"] == "learned" and r["scenario"] == "nominal" and r["max_step_s"] == .02)
            base = nominal["case_id"]
            for scenario in ("pulse_left", "pulse_right"):
                row = next(r for r in result["cases"] if r["actor"] == "learned" and r["lap_id"] == nominal["lap_id"] and r["scenario"] == scenario)
                key = row["case_id"]
                station = arrays[key+"__station_m"]
                error = arrays[key+"__lateral_m"]-np.interp(station, arrays[base+"__station_m"], arrays[base+"__lateral_m"])
                ax.plot(station/row["track_length_m"], error, label=scenario)
            ax.axhline(.15, color="grey", linestyle=":")
            ax.axhline(-.15, color="grey", linestyle=":")
            ax.set(xlabel="Unwrapped progress (laps)", ylabel="Lateral difference from nominal (m)", title="Signed command pulses; first learned condition")
            ax.legend(fontsize=8)
            ax = axes[1, 1]
            rows = [v for r in result["cases"] for v in r.get("recovery", [])]
            ax.scatter(np.arange(len(rows))+1, [r["recovery_s"] if r["recovery_s"] is not None else 10.5 for r in rows], s=24)
            ax.axhline(10, color="darkred", linestyle="--", label="10s gate")
            ax.set(xlabel="Every required pulse (both controllers/signs)", ylabel="Sustained recovery time (s)", title="Two-second sustained matched-path recovery", ylim=(-.3, 11))
            ax.legend(fontsize=8)
        else:
            ax = axes[0, 0]
            for actor in ("unguarded", "guarded", "transparent"):
                rows = [r for r in result["cases"] if r["actor"] == actor and r["scenario"] == "nominal"]
                means = np.sqrt(np.mean([[v["rmse_m"]**2 for v in r["laps"]] for r in rows], axis=0))
                ax.plot((1, 2, 3), means, marker="o", label=actor)
            ax.set(xlabel="Continuous lap", ylabel="Macro station RMSE (m)", title="Nominal matched pace and physics")
            ax.legend(fontsize=8)
            ax = axes[0, 1]
            row = next(r for r in result["cases"] if r["actor"] == "guarded" and r["scenario"] == "feature_shift")
            key = row["case_id"]
            x = arrays[key+"__station_m"][:-1]/row["track_length_m"]
            decisions = row["decisions"][:len(x)]
            ax.step(x, [int(d["mode"] == "fallback") for d in decisions], where="post", label="fallback")
            ax.set(xlabel="Unwrapped progress (laps)", ylabel="Controller mode", yticks=[0, 1], yticklabels=["learned", "fallback"],
                   title="Injected preview-feature fault; first condition", ylim=(-.15, 1.2))
            right = ax.twinx()
            right.plot(x, [d["score"] for d in decisions], color="darkorange", alpha=.45)
            cutoff = read_json(study/"detector/detector.json")["model"]["cutoff"]
            right.axhline(cutoff, color="grey", linestyle="--", label="Frozen cutoff")
            right.legend(fontsize=7, loc="upper right")
            right.set_ylabel("Empirical box score", color="darkorange")
            ax = axes[1, 1]
            faults = ("nominal", "feature_shift", "residual_bias", "nonfinite")
            table = []
            for actor in ("unguarded", "guarded"):
                table.append([sum(r["passed"] for r in result["cases"] if r["actor"] == actor and r["scenario"] == fault and r["max_step_s"] == .02) for fault in faults])
            ax.imshow(table, vmin=0, vmax=max(max(r) for r in table), cmap="Blues", aspect="auto")
            for i, row in enumerate(table):
                for j, value in enumerate(row):
                    ax.text(j, i, str(value), ha="center", va="center", color="darkred", fontsize=13)
            ax.set(xticks=range(4), xticklabels=["nominal", "feature shift", "action bias", "nonfinite"], yticks=[0, 1],
                   yticklabels=["unguarded", "guarded"], title="Runs within declared stability and error limits")
        ax = axes[1, 0]
        refinements = result["refinements"]
        ax.bar(np.arange(len(refinements))+1, [r["maximum_position_difference_m"] for r in refinements], color="#39799b")
        ax.set(xlabel="Every frozen source condition", ylabel="Maximum common-station XY difference (m)", title=".02s vs .01s refinement over full horizon")
        ax.ticklabel_format(axis="y", style="sci", scilimits=(-3, 3))
    for ax in axes.flat:
        ax.grid(alpha=.15)
        ax.set_axisbelow(True)
    fig.savefig(output/(kind+"-summary.png"), dpi=160)
    plt.close(fig)
    manifest = seal({"schema_version": "apex-"+kind+"-publication-manifest-v1", "evidence_sha256": evidence["content_sha256"],
                     "publisher_sha256": file_sha256(Path(__file__)), "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}})
    write_manifest(output/(kind+"-manifest.json"), manifest)
    return {"evidence_sha256": evidence["content_sha256"], "publication_sha256": manifest["content_sha256"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kind", choices=("recovery", "support"), required=True)
    args = parser.parse_args()
    print(publish(args.study, args.receipt, args.output, args.kind))
