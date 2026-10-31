"""Publish compact, source-bound R027/R028 evidence and a static research figure."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib
import numpy as np
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from matplotlib import pyplot as plt

matplotlib.use("Agg")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("study", "verification", "audit", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    evidence_path = args.output/"forecast-explanation-evidence.json"
    figure_path = args.output/"forecast-explanation-summary.png"
    manifest_path = args.output/"forecast-explanation-manifest.json"
    if any(p.exists() for p in (evidence_path, figure_path, manifest_path)):
        raise FileExistsError("Explanation publication outputs must be fresh")

    def read(name: str):
        return json.loads((args.study/name).read_text(encoding="utf-8"))

    summary, result, cohort, manifest = (read(name) for name in ("summary.json", "results.json", "cohort.json", "manifest.json"))
    verification = json.loads(args.verification.read_text(encoding="utf-8"))
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    if (not verification["verified"] or not audit["verified"]
            or verification["summary_sha256"] != summary["content_sha256"]
            or not summary["task_closure_eligible"]):
        raise ValueError("Explanation publication requires accepted, replayed, audited public evidence")
    methods = {}
    for name, method in result["models"].items():
        compact = []
        for case in method["cases"]:
            explanation, counterfactual = case["explanation"], case["counterfactual"]
            compact.append({"origin_key": case["origin_key"], "explanation_status": explanation["status"],
                            **{k: explanation[k] for k in ("ranking", "rank_audit_spearman", "heldout_top_mean_kj",
                               "heldout_random_expectation_kj", "joint_top_deletion_kj", "joint_random_deletion_kj",
                               "joint_top_insertion_gain_kj", "joint_random_insertion_gain_kj",
                               "nearby_top_three_overlap", "donor_top_three_overlap") if k in explanation},
                            "counterfactual": counterfactual})
        methods[name] = {"kind": method["kind"], "aggregates": method["aggregates"], "cases": compact,
                         "raw_output_projection": method["raw_output_projection"],
                         "maximum_baseline_difference_to_original_r026_kj": method["maximum_baseline_difference_to_original_r026_kj"],
                         "inference_accumulation": method["inference_accumulation"]}
    source_failures = dict(Counter(r for d in result["source_and_scenario_diagnostics"] for r in d["source_violations"]))
    splice_failures = Counter()
    for diagnostic in result["source_and_scenario_diagnostics"]:
        splice_failures.update(diagnostic["splice_constraint_violations"])
    evidence = {"schema_version": "apex-forecast-explanation-acceptance-evidence-v1", "study_summary": summary,
                "cohort_sha256": cohort["content_sha256"], "cohort_coverage": cohort["coverage"],
                "reference_inventory_sha256": cohort["reference_inventory_sha256"],
                "evaluation_inventory_sha256": cohort["evaluation_inventory_sha256"],
                "source_summary_sha256": {"reference": cohort["reference_summary_sha256"], "evaluation": cohort["evaluation_summary_sha256"]},
                "scientific_replay": verification, "independent_audit": audit,
                "verification_file_sha256": file_sha256(args.verification), "audit_file_sha256": file_sha256(args.audit),
                "gates": result["gates"], "useful_evidence_by_stratum": result["useful_evidence_by_stratum"],
                "same_family_seed_stability": result["same_family_seed_stability"], "methods": methods,
                "robust_primary_counterfactuals": result["robust_primary_counterfactuals"],
                "source_constraint_failures": source_failures,
                "diagnostic_splices": sum(d["diagnostic_splices"] for d in result["source_and_scenario_diagnostics"]),
                "diagnostic_splice_constraint_failures": dict(splice_failures),
                "history_span_s_quantiles": result["history_span_s_quantiles"],
                "elapsed_horizon_s_quantiles": result["elapsed_horizon_s_quantiles"],
                "limitations": result["limitations"]}
    evidence["content_sha256"] = payload_sha256(evidence)
    args.output.mkdir(parents=True, exist_ok=True)
    write_manifest(evidence_path, evidence)
    write_manifest(manifest_path, manifest)

    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), layout="constrained")
    primary = result["primary_frozen_seeds"]
    importance = {s: np.mean([result["models"][name]["aggregates"][s]["equal_event_importance_kj"] for name in primary], axis=0).reshape(3, 4)
                  for s in ("seen", "unseen")}
    maximum = max(float(v.max()) for v in importance.values())
    for ax, stratum in zip(axes[0], ("seen", "unseen"), strict=True):
        values = importance[stratum]
        image = ax.imshow(values, vmin=0, vmax=maximum, cmap="viridis", aspect="auto")
        for row in range(3):
            for column in range(4):
                ax.text(column, row, f"{values[row,column]:.2f}", ha="center", va="center",
                        color="white" if values[row, column] < values.max()*.55 else "black")
        ax.set_xticks(range(4), ["−7:−6", "−5:−4", "−3:−2", "−1:0"])
        ax.set_yticks(range(3), ["Kinematics", "Controls", "Past energy proxies"])
        ax.set_xlabel("Native history samples relative to origin")
        ax.set_title(f"XGBoost model dependence: {stratum} circuits")
        fig.colorbar(image, ax=ax, label="Mean absolute forecast change [kJ]")
    labels = list(methods)
    y = np.arange(len(labels))
    for ax, metric, title in (
        (axes[1, 0], "reliable_explanations", "Explanations passing independent-donor gates"),
        (axes[1, 1], "counterfactual_successes", "Constraint-feasible model counterfactuals"),
    ):
        for offset, stratum, color in ((-.18, "seen", "#246c88"), (.18, "unseen", "#ce7c28")):
            values = [100*methods[name]["aggregates"][stratum][metric]/methods[name]["aggregates"][stratum]["origins"] for name in labels]
            ax.barh(y+offset, values, height=.34, label=stratum, color=color)
        ax.set_yticks(y, labels)
        ax.invert_yaxis()
        ax.set_xlim(0, 100)
        ax.set_xlabel("Percent of all selected origins (including abstentions)")
        ax.set_title(title)
        ax.legend(loc="lower right", fontsize=8)
        ax.grid(axis="x", alpha=.18)
    fig.suptitle("APEX R027/R028 · 128 fixed development origins · frozen models\nPROXY targets; model diagnostics and bounded scenarios, no real-car causal claim", fontsize=12)
    fig.savefig(figure_path, dpi=170)
    plt.close(fig)
    print(json.dumps({"evidence_sha256": evidence["content_sha256"], "summary_sha256": summary["content_sha256"],
                      "figure": str(figure_path), "methods": len(methods)}, indent=2))


if __name__ == "__main__":
    main()
