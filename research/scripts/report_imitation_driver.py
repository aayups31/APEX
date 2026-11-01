"""Publish R036 run-bound comparison evidence; preserve expert/student distinctions."""
from __future__ import annotations

import argparse
import platform
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from apexsim.examples.imitation_study import load_development, load_imitation_evaluation
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import read_json, seal
from apexsim.research.imitation_driver import predict_residual


def source_discrepancies(root: Path, result: dict) -> list[dict]:
    """Descriptive source-speed comparison after fitting/test, never a training input."""
    recorded = root/"development/dataset/parent/calibration/recorded"
    records = []
    with np.load(root/"trajectories.npz", allow_pickle=False) as arrays:
        for case in result["cases"]:
            if case["actor"] != "final" or case["scenario"] != "nominal" or case["max_step_s"] != .02:
                continue
            key, track = case["lap_id"], case["track_id"]
            if not case["completed"]:
                records.append({"case_id": case["case_id"], "matched_native_rows": 0, "speed_rmse_mps": None,
                                "scope": "UNAVAILABLE_INCOMPLETE_MODEL_LAP"})
                continue
            base = recorded/"longitudinal/geometry"
            with (np.load(base/(track+"_lap_inputs.npz"), allow_pickle=False) as native,
                  np.load(base/(track+"_geometry_predictions.npz"), allow_pickle=False) as geometry):
                lookup = {int(a): float(s) for (a, b), s, d in zip(native[key+"_native_parents"], geometry[key+"_station_m"],
                                                                  geometry[key+"_distance_m"], strict=True) if a == b and d <= 15}
            frame = pd.read_parquet(recorded/"frames"/(key+".parquet"))
            frame = frame.loc[frame.joint_observed_ready & frame.position_source_row.isin(lookup)]
            station = np.array([lookup[int(v)] for v in frame.position_source_row])
            progress = arrays[case["case_id"]+"__station_m"]
            states = arrays[case["case_id"]+"__states"]
            if np.any(np.diff(progress) <= 0):
                raise ValueError("R036 descriptive source comparison requires monotone progress")
            supported = (station >= progress[0]) & (station <= progress[-1])
            simulated = np.interp(station[supported], progress, np.hypot(states[:, 3], states[:, 4]))
            delta = simulated-frame.speed_mps.to_numpy(float)[supported]
            records.append({"case_id": case["case_id"], "matched_native_rows": int(sum(supported)),
                            "speed_rmse_mps": float(np.sqrt(np.mean(delta**2))), "speed_mae_mps": float(np.mean(abs(delta))),
                            "speed_bias_mps": float(np.mean(delta)), "truth": "SIMULATED_SPEED_VS_PARSED_SOURCE_AT_RECONSTRUCTED_BACKWARD_STATION",
                            "scope": "POSTHOC_DESCRIPTION_ONLY; NOT_TRAINING_OR_REAL_CAR_ACCEPTANCE"})
    return records


def inference_benchmark(root: Path, fitted: dict) -> dict:
    with np.load(root/"development/training.npz", allow_pickle=False) as arrays:
        rows = arrays["aggregate_x"][:256]
    model = fitted["models"][fitted["selected"]]
    for row in rows:
        predict_residual(model, row)
    measurements = []
    for _ in range(5):
        start = time.perf_counter()
        for row in rows:
            predict_residual(model, row)
        elapsed = time.perf_counter()-start
        if elapsed <= 0:
            raise ValueError("Unstable timing clock; inference benchmark unavailable")
        measurements.append(elapsed/len(rows)*1e6)
    return {"scope": "DESCRIPTIVE_LOCAL_CPU_POLICY_INFERENCE; NO_DYNAMICS_OR_MAP_EXTRACTION",
            "median_microseconds_per_row": float(np.median(measurements)), "repeat_microseconds_per_row": measurements,
            "parameters": model["parameters"], "python": platform.python_version(), "numpy": np.__version__}


def publish(study: Path, verification: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("R036 publication output must be fresh")
    summary, result = load_imitation_evaluation(study)
    if result["profile"] != "research":
        raise ValueError("Smoke is not public R036 evidence")
    receipt = read_json(verification)
    if receipt.get("verified") is not True or receipt.get("summary_sha256") != summary["content_sha256"]:
        raise ValueError("R036 publication requires exact run-bound scientific replay")
    _, fitted, header, _, _ = load_development(study/"development")
    catalog = {c["lap_id"]: c for c in header["cases"]}
    discrepancies = source_discrepancies(study, result)
    for row in discrepancies:
        case = next(c for c in result["cases"] if c["case_id"] == row["case_id"])
        source = catalog[case["lap_id"]]
        source_time = source["lap_end_s"]-source["lap_start_s"]
        row.update(source_lap_time_s=source_time, simulated_finish_s=case["completion_time_s"],
                   source_time_difference_s=None if not case["completed"] else case["completion_time_s"]-source_time)
    output.mkdir(parents=True)
    benchmark = inference_benchmark(study, fitted)
    evidence = seal({"schema_version": "apex-imitation-driver-publication-v1", "study_summary": summary, "results": result,
                     "verification": receipt, "development_summary": read_json(study/"development/summary.json"),
                     "development_verification": read_json(study/"development_verification.json"),
                     "model_selection": {k: fitted[k] for k in ("expert_validation_scores", "selected_lead_s", "validation_scores", "selected", "best_bc", "best_linear")},
                     "models": fitted["models"], "base_episode_ledger": fitted["base_episode_ledger"], "episode_ledger": fitted["episode_ledger"],
                     "posthoc_source_discrepancies": discrepancies, "inference_benchmark": benchmark,
                     "run_manifest": read_json(study/"manifest.json"), "run_manifest_sha256": file_sha256(study/"manifest.json")})
    write_manifest(output/"imitation-driver-evidence.json", evidence)
    fig, axes = plt.subplots(2, 2, figsize=(14.5, 9), constrained_layout=True)
    fig.suptitle("APEX R036 | conditional imitation of a simulated preview expert; generic vehicle priors")
    nominal = [c for c in result["cases"] if c["scenario"] == "nominal" and c["max_step_s"] == .02]
    actors = ("transparent", "expert", "linear", "bc", "final")
    ids = sorted({c["lap_id"] for c in nominal})
    ax = axes[0, 0]
    for i, actor in enumerate(actors):
        metrics = [next(c for c in nominal if c["lap_id"] == key and c["actor"] == actor)["station_weighted_mse_m2"] for key in ids]
        values = [np.sqrt(value) if value is not None else np.nan for value in metrics]
        ax.bar(np.arange(len(ids))+(i-2)*.16, values, width=.15, label=actor)
        for j, value in enumerate(values):
            if not np.isfinite(value):
                ax.text(j+(i-2)*.16, 0, "FAILED", rotation=90, va="bottom", ha="center", fontsize=7)
    ax.set_xticks(np.arange(len(ids)), [key.replace("F1_2024_R16_", "") for key in ids])
    ax.set(xlabel="Driver / source lap condition", ylabel="Station-weighted reference RMSE (m)", title="Matched pace, physics, map and initial conditions")
    ax.legend(fontsize=8)
    ax = axes[0, 1]
    with np.load(study/"trajectories.npz", allow_pickle=False) as arrays:
        for actor in ("transparent", "expert", "final"):
            case = next(c for c in nominal if c["lap_id"] == ids[0] and c["actor"] == actor)
            key = case["case_id"]
            ax.plot(arrays[key+"__station_m"], arrays[key+"__lateral_m"], label=actor, linewidth=1)
    ax.set(xlabel="Unwrapped reference progress (m)", ylabel="Signed reference error (m)", title="One declared case; reference corridor is not road width")
    ax.legend(fontsize=8)
    ax = axes[1, 0]
    lead = sorted(float(k) for k in fitted["expert_validation_scores"])
    values = [np.sqrt(fitted["expert_validation_scores"][str(v)]) for v in lead]
    ax.plot(lead, values, marker="o")
    ax.axvline(fitted["selected_lead_s"], linestyle="--", color="#bf603e", label="Frozen expert choice")
    ax.set(xlabel="Known-map feedforward preview (s)", ylabel="Validation reference RMSE (m)", title="Expert improvement is separate from student imitation")
    ax.legend(fontsize=8)
    ax = axes[1, 1]
    names = list(fitted["models"])
    values = [np.sqrt(fitted["models"][name]["training_weighted_mse_rad2"]) for name in names]
    ax.bar(np.arange(len(names)), values, color=["#bf603e" if name == fitted["selected"] else "#3b7ca6" for name in names])
    ax.set_xticks(np.arange(len(names)), names, rotation=20, ha="right", fontsize=8)
    ax.set_yscale("symlog", linthresh=1e-9)
    ax.set(ylabel="Expert-residual training RMSE (rad)", title="Genuine fitted compact models; no human action labels")
    for ax in axes.flat:
        ax.grid(alpha=.15)
        ax.set_axisbelow(True)
    fig.savefig(output/"imitation-driver-summary.png", dpi=160)
    plt.close(fig)
    manifest = seal({"schema_version": "apex-imitation-driver-publication-manifest-v1", "evidence_sha256": evidence["content_sha256"],
                     "publisher_sha256": file_sha256(__file__), "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}})
    write_manifest(output/"imitation-driver-manifest.json", manifest)
    return {"evidence_sha256": evidence["content_sha256"], "publication_sha256": manifest["content_sha256"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(publish(args.study, args.verification, args.output))
