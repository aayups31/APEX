"""Publish source-bound R030 evidence and an inspected static diagnostic figure."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
from apexsim.examples.longitudinal_dataset import load_sections
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from matplotlib import pyplot as plt

matplotlib.use("Agg")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("study", "verification", "audit", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()

    def read(name: str):
        return json.loads((args.study/name).read_text(encoding="utf-8"))

    targets = [args.output/("longitudinal-calibration-"+n) for n in ("evidence.json", "manifest.json", "summary.png")]
    if any(p.exists() for p in targets):
        raise FileExistsError("R030 publication outputs must be fresh")
    summary, results = read("summary.json"), read("results.json")
    development, models = read("development/summary.json"), read("development/models.json")
    source = read("development/dataset/summary.json")
    verification = json.loads(args.verification.read_text(encoding="utf-8"))
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    if (not verification["verified"] or not audit["verified"] or summary["profile"] != "research"
            or verification["summary_sha256"] != summary["content_sha256"]
            or verification["decision"] != results["decision"] or audit["decision"] != results["decision"]):
        raise ValueError("R030 publication requires replayed and independently audited research")
    evidence = {"schema_version": "apex-longitudinal-calibration-evidence-v1", "study_summary": summary,
                "development_summary": development, "source_preflight": source, "results": results,
                "fitted_candidate_classes": {k: {"eligible": v["eligible"], "failures": v["failures"]} for k, v in models["candidates"].items()},
                "selected_parameters": models["candidates"][models["selected"]]["cells"],
                "rolling_prior_sensitivity": models["rolling_prior_sensitivity"],
                "scientific_replay": verification, "independent_audit": audit,
                "verification_file_sha256": file_sha256(args.verification), "audit_file_sha256": file_sha256(args.audit)}
    evidence["content_sha256"] = payload_sha256(evidence)
    args.output.mkdir(parents=True, exist_ok=True)
    write_manifest(targets[0], evidence)
    write_manifest(targets[1], read("manifest.json"))
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout="constrained")
    methods = list(results["metrics"])
    positions = np.arange(len(methods))
    for offset, label, color in ((-.18, "Validation: Bahrain2024", "#277187"), (.18, "Test: Monza2024", "#cb7b29")):
        values = [models["validation_metrics"][m]["rmse_mps"] if offset < 0 else results["metrics"][m]["rmse_mps"] for m in methods]
        axes[0, 0].barh(positions+offset, values, height=.34, color=color, label=label)
    axes[0, 0].set_yticks(positions, methods)
    axes[0, 0].invert_yaxis()
    axes[0, 0].set_xlabel("Equal-driver/lap speed RMSE [m/s]")
    axes[0, 0].set_title("Frozen model versus matched baselines", pad=30)
    axes[0, 0].legend(loc="lower center", bbox_to_anchor=(.5, 1), ncol=2, frameon=False, fontsize=8)
    axes[0, 0].grid(axis="x", alpha=.2)
    sections = [s for s in load_sections(args.study/"development/dataset") if s.metadata["role"] == "test"]
    selected = results["selected"]
    with np.load(args.study/"predictions.npz", allow_pickle=False) as raw:
        for driver, color in (("4", "#277187"), ("44", "#cb7b29")):
            ids = [i for i, s in enumerate(sections) if s.metadata["driver_id"] == driver]
            axes[0, 1].scatter([sections[i].speed_mps[-1] for i in ids], [raw[selected+f"__s{i}"][-1] for i in ids],
                               label="Driver "+driver, color=color, s=25, alpha=.8)
        lo = min(s.speed_mps[-1] for s in sections)-3
        hi = max(max(s.speed_mps[-1] for s in sections), max(raw[selected+f"__s{i}"][-1] for i in range(len(sections))))+3
        axes[0, 1].plot([lo, hi], [lo, hi], color="black", linewidth=1)
        axes[0, 1].set(xlabel="Recorded endpoint speed [m/s]", ylabel="Model endpoint speed [m/s]", title=f"All {len(sections)} held-out section endpoints")
        axes[0, 1].legend(fontsize=8)
        axes[0, 1].grid(alpha=.2)
        for ax, driver in zip(axes[1], ("4", "44"), strict=True):
            # Deterministic first source key, not best/worst error selection.
            i = next(i for i, s in enumerate(sections) if s.metadata["driver_id"] == driver)
            section = sections[i]
            elapsed = section.time_s-section.time_s[0]
            ax.plot(elapsed, section.speed_mps, "o", label="Recorded source", color="black", markersize=4)
            ax.plot(elapsed, raw[selected+f"__s{i}"], label="Calibrated model", color="#277187")
            ax.plot(elapsed, raw["physical_prior"+f"__s{i}"], "--", label="Uncalibrated prior", color="#cb7b29")
            q = raw[f"bootstrap_quantiles__s{i}"]
            ax.fill_between(elapsed, q[0], q[2], color="#277187", alpha=.15, label="Parameter band only")
            ax.set(xlabel="Elapsed recorded-control replay [s]", ylabel="Speed [m/s]",
                   title=f"Driver {driver}: first source-ordered test section")
            ax.legend(fontsize=8)
            ax.grid(alpha=.2)
    fig.suptitle("APEX R030 · native public speed replay · fixed training/validation/test events\nHigh-speed full-throttle straights only; effective coefficients, not identified engine power/CdA", fontsize=12)
    fig.savefig(targets[2], dpi=170)
    plt.close(fig)
    print(json.dumps({"evidence_sha256": evidence["content_sha256"], "study_sha256": summary["content_sha256"],
                      "decision": summary["decision"], "figure": str(targets[2])}, indent=2))


if __name__ == "__main__":
    main()
