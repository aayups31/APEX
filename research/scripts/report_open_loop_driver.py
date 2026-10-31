"""Publish run-bound R034/R035 evidence and standard scientific diagnostic figures."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from apexsim.examples.driver_study import load_calibration, load_driver_study
from apexsim.examples.open_loop_study import load_study
from apexsim.provenance import file_sha256, write_manifest
from apexsim.research.evidence import read_json, seal
from apexsim.research.open_loop_errors import HORIZONS, METHODS


def source_speed_diagnostics(study: Path, result: dict):
    """Post-evaluation description only; never enters calibration or feedback."""
    recorded = study/"calibration/recorded"
    records = []
    with np.load(study/"trajectories.npz", allow_pickle=False) as trajectories:
        for case in result["cases"]:
            if case["role"] != "test" or case["mode"] != "feedback" or case["max_step_s"] != .02:
                continue
            key, track = case["lap_id"], case["track_id"]
            base = recorded/"longitudinal/geometry"
            with (np.load(base/(track+"_lap_inputs.npz"), allow_pickle=False) as native,
                  np.load(base/(track+"_geometry_predictions.npz"), allow_pickle=False) as geometry):
                lookup = {int(a): float(s) for (a, b), s, d in zip(native[key+"_native_parents"], geometry[key+"_station_m"],
                                                                  geometry[key+"_distance_m"], strict=True) if a == b and d <= 15}
            frame = pd.read_parquet(recorded/"frames"/(key+".parquet"))
            subset = frame.loc[frame.joint_observed_ready & frame.position_source_row.isin(lookup)]
            stations = np.array([lookup[int(v)] for v in subset.position_source_row])
            progress = trajectories[case["case_id"]+"__station_m"]
            states = trajectories[case["case_id"]+"__states"]
            if np.any(np.diff(progress) <= 0):
                raise ValueError("Posthoc source comparison requires monotone simulated progress")
            selected = (stations >= progress[0]) & (stations <= progress[-1])
            source = subset.speed_mps.to_numpy(float)[selected]
            simulated = np.interp(stations[selected], progress, np.hypot(states[:, 3], states[:, 4]))
            delta = simulated-source
            records.append({"case_id": case["case_id"], "compared_native_rows": len(delta), "all_native_rows": len(frame),
                            "source_speed_truth": "FASTF1_PARSED_SOURCE", "station_truth": "RECONSTRUCTED_BACKWARD_NATIVE_POSITION_ON_SUPPLIED_MAP",
                            "simulated_speed_truth": "SIMULATED_GENERIC_PRIOR_VEHICLE", "use": "POSTHOC_DESCRIPTION_ONLY; NOT_ACCEPTANCE_OR_CALIBRATION",
                            "speed_rmse_mps": float(np.sqrt(np.mean(delta**2))), "speed_mae_mps": float(np.mean(abs(delta))),
                            "speed_bias_mps": float(np.mean(delta)), "source_time_difference_s": case["source_time_difference_s"]})
    return records


def publish(kind: str, study: Path, receipts: list[Path], output: Path):
    if output.exists():
        raise FileExistsError("Publication output must be fresh")
    summary, result = load_study(study) if kind == "open-loop" else load_driver_study(study)
    verified = [read_json(p) for p in receipts]
    if (len(verified) != (2 if kind == "open-loop" else 1) or not summary["task_closure_eligible"]
            or any(r.get("verified") is not True or r.get("summary_sha256") != summary["content_sha256"] for r in verified)):
        raise ValueError("Publication requires accepted run-bound replay/audit receipts")
    if kind == "open-loop" and verified[1].get("paths_checked") != len(result["records"]):
        raise ValueError("Publication requires exhaustive independent horizon audit")
    if kind == "driver" and not verified[0].get("independent_audit", {}).get("passed"):
        raise ValueError("Publication requires independent complete-lap audit")
    output.mkdir(parents=True)
    prefix = "open-loop-errors" if kind == "open-loop" else "transparent-driver"
    evidence = seal({"schema_version": "apex-"+prefix+"-publication-v1", "study_summary": summary, "results": result,
                     "verification_receipts": verified, "run_manifest": read_json(study/"manifest.json"),
                     "run_manifest_sha256": file_sha256(study/"manifest.json"),
                     "posthoc_source_speed_diagnostics": source_speed_diagnostics(study, result) if kind == "driver" else None})
    write_manifest(output/(prefix+"-evidence.json"), evidence)
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    if kind == "open-loop":
        fig.suptitle("APEX R034 | matched supported section forecasts; full-car lap/stint replay unavailable")
        ax = axes[0, 0]
        for method in METHODS:
            ax.plot(HORIZONS, [result["scores"]["test"][str(h)][method]["rmse_mps"] for h in HORIZONS], marker="o", label=method)
        ax.set(xlabel="Exact forecast horizon (s)", ylabel="Hierarchical speed RMSE (m/s)", title="Held-out Monza: two drivers; smaller 3 s cohort")
        ax.legend(fontsize=8)
        ax = axes[0, 1]
        ledger = result["support_ledger"]
        counts = [sum(r["horizon_s"] == h and r["supported"] for r in ledger) for h in HORIZONS]
        x = np.arange(4)
        ax.bar(x, counts, label="Supported")
        ax.bar(x, [result["sections"]-n for n in counts], bottom=counts, label="Frozen section too short", color="#bf603e")
        ax.set_xticks(x, [str(h) for h in HORIZONS])
        ax.set(xlabel="Horizon (s)", ylabel="All source section cases", title="Complete 600-case support accounting")
        ax.legend(fontsize=8)
        ax = axes[1, 0]
        for method in ("shared_drag", "constant_acceleration", "legacy_huber"):
            ax.plot(HORIZONS, [result["scores"]["test"][str(h)][method]["absolute_speed_integral_error_m"] for h in HORIZONS], marker="o", label=method)
        ax.set(xlabel="Horizon (s)", ylabel="Absolute speed-integral error (m)", title="Reconstructed integral; not observed position error")
        ax.legend(fontsize=8)
        ax = axes[1, 1]
        lap_counts = [r["supported_sections"] for r in result["lap_catalog"]]
        ax.hist(lap_counts, bins=np.arange(max(lap_counts)+2)-.5, color="#3b7ca6")
        ax.set(xlabel="Supported frozen sections in source lap", ylabel="Source laps", title="All 88 laps retained, including zero-section laps")
    else:
        fig.suptitle("APEX R035 | conditional generated-action research laps; generic vehicle priors")
        _, calibration, maps = load_calibration(study/"calibration")
        nominal = [r for r in result["cases"] if r["role"] == "test" and r["mode"] == "feedback" and r["max_step_s"] == .02]
        with np.load(study/"trajectories.npz", allow_pickle=False) as arrays:
            track = maps["monza"]
            ax = axes[0, 0]
            ax.plot(*track.xy.T, color="black", label="Supplied reconstructed map", linewidth=2)
            for case in nominal:
                states = arrays[case["case_id"]+"__states"]
                ax.plot(*states[:, :2].T, linewidth=.8, label=case["lap_id"].replace("F1_2024_R16_", ""))
            ax.set_aspect("equal")
            ax.set(xlabel="Map x (m)", ylabel="Map y (m)", title="Complete six-state simulated paths")
            ax.legend(fontsize=7)
            ax = axes[0, 1]
            for case in nominal:
                key = case["case_id"]
                ax.plot(arrays[key+"__station_m"], arrays[key+"__lateral_m"], linewidth=.8, label=case["lap_id"].replace("F1_2024_R16_", ""))
            ax.axhline(2, color="#bf603e", linestyle="--", linewidth=.8)
            ax.axhline(-2, color="#bf603e", linestyle="--", linewidth=.8)
            ax.set(xlabel="Unwrapped reference progress (m)", ylabel="Signed reference error (m)", title="Reference corridor is not a measured road boundary")
            ax.legend(fontsize=7)
            ax = axes[1, 0]
            case = nominal[0]
            key = case["case_id"]
            states = arrays[key+"__states"]
            ax.plot(arrays[key+"__station_m"], np.hypot(states[:, 3], states[:, 4]), label="Simulated speed")
            profile = arrays[key+"__profile_mps"]
            ax.plot(np.arange(len(profile))*track.spacing, profile, label="Frozen map-only target", alpha=.7)
            ax.set(xlabel="Reference progress (m)", ylabel="Speed (m/s)", title="Pace calibration confounded with generic vehicle priors")
            ax.legend(fontsize=8)
        ax = axes[1, 1]
        selected = calibration["selected"]
        labels = [f"{c['fraction']:.2f}/{c['maximum_mps']:.0f}" for c in calibration["candidates"]]
        colors = ["#bf603e" if c["fraction"] == selected["fraction"] and c["maximum_mps"] == selected["maximum_mps"] else "#3b7ca6" for c in calibration["candidates"]]
        ax.bar(np.arange(9), [np.sqrt(c["validation_mse_m2ps2"]) for c in calibration["candidates"]], color=colors)
        ax.set_xticks(np.arange(9), labels, rotation=35)
        ax.set(xlabel="Lateral fraction / maximum speed (m/s)", ylabel="Validation speed-profile RMSE (m/s)", title="Frozen on Bahrain validation; no test outcomes used")
    for ax in axes.flat:
        ax.grid(alpha=.15)
        ax.set_axisbelow(True)
    fig.savefig(output/(prefix+"-summary.png"), dpi=160)
    plt.close(fig)
    manifest = seal({"schema_version": "apex-"+prefix+"-publication-manifest-v1", "evidence_sha256": evidence["content_sha256"],
                     "publisher_sha256": file_sha256(__file__),
                     "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}})
    write_manifest(output/(prefix+"-manifest.json"), manifest)
    return {"evidence_sha256": evidence["content_sha256"], "publication_sha256": manifest["content_sha256"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("open-loop", "driver"), required=True)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--receipt", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    print(publish(options.kind, options.study, options.receipt, options.output))
