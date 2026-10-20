"""Render source-bound R029 diagnostics from a sealed, accepted public study."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
from apexsim.provenance import file_sha256, payload_sha256, write_manifest
from apexsim.research.reference_geometry import GeometryConfig, ReferenceCurve


def render(input_path: Path, output: Path) -> dict:
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if output.exists() or output.resolve().is_relative_to(input_path.resolve()):
        raise ValueError("Figures require fresh output outside the immutable study")
    manifest = json.loads((input_path/"manifest.json").read_text())
    summary = json.loads((input_path/"summary.json").read_text())
    for item in (manifest, summary):
        if item["content_sha256"] != payload_sha256({k:v for k,v in item.items() if k != "content_sha256"}):
            raise ValueError("Scientific figure input seal mismatch")
    if manifest["summary_sha256"] != summary["content_sha256"] or summary["profile"] != "research_v3" or not summary["task_closure_eligible"]:
        raise ValueError("Scientific figures require accepted real R029 v3 inputs")
    for name, item in manifest["files"].items():
        if Path(name).name != name or file_sha256(input_path/name) != item["sha256"]:
            raise ValueError("Scientific figure source file mismatch")
    output.mkdir(parents=True)
    for track, case in summary["cases"].items():
        with np.load(input_path/f"{track}_geometry_predictions.npz", allow_pickle=False) as raw:
            arrays = {name: raw[name] for name in raw.files}
        curve = ReferenceCurve(arrays["coefficients"], GeometryConfig(**case["selected_config"]), track)
        station = np.linspace(0., curve.length_m, 4000)
        xy, _, curvature = curve.geometry(station)
        fig, axes = plt.subplots(2, 2, figsize=(12.8, 9.2))
        shape, bending, coverage, sensitivity = axes.ravel()
        test_laps = [m for m in case["lap_metrics"] if m["role"] == "test"]
        for i, lap in enumerate(test_laps):
            key = lap["lap_id"]
            observed = arrays[key+"_aligned_xy"]
            shape.scatter(observed[:, 0], observed[:, 1], s=2, alpha=.18, color="#3569ad", label="Registered native holdout XY" if i == 0 else None)
            valid = arrays[key+"_coarse_supported"]
            common_station = curve.project(arrays[key+"_coarse_xy_m"][valid])["station_m"]
            bending.scatter(common_station, arrays[key+"_coarse_curvature_proxy_1pm"][valid], s=3, alpha=.2, color="#bd6a25", label="Supported coarse curvature proxy" if i == 0 else None)
        shape.plot(xy[:, 0], xy[:, 1], color="#17283f", lw=1., label="Training reference curve")
        for name, label, marker in (("start_finish", "S/F", "*"), ("sector1_end", "S1", "D"), ("sector2_end", "S2", "D"), ("pit_entry", "Pit timing in", "x"), ("pit_exit", "Pit timing out", "x")):
            annotation = case["annotations"][name]
            location = annotation.get("station_m", (annotation.get("spread") or {}).get("circular_mean_station_m"))
            if location is not None:
                point = curve.geometry(np.array([location]))[0][0]
                shape.scatter(*point, marker=marker, s=25, color="#b73535")
                shape.annotate(label, point, xytext=(4, 4), textcoords="offset points", fontsize=7)
        shape.set(xlabel="Local X (m)", ylabel="Local Y (m)", title="Reference racing trace and timing projections")
        shape.set_aspect("equal", adjustable="datalim")
        shape.legend(fontsize=7, loc="best")
        bending.plot(station, curvature, color="#17283f", lw=.9, label="Analytic reference curvature")
        bending.set(xlabel="Reference station (m)", ylabel="Signed curvature (1/m)", title="Held-out curvature consistency; proxy target")
        bending.legend(fontsize=7)
        coverage.step(arrays["support_station_m"], arrays["support_donor_counts"], where="post", color="#2a7852")
        coverage.axhline(3., color="#b73535", ls="--", lw=.8, label="Required minimum: 3 laps")
        coverage.set(xlabel="Reference station (m)", ylabel="Distinct supported training laps", ylim=(0, 10.5), title="Observed source support at every 10 m station")
        coverage.legend(fontsize=7)
        offsets = arrays["sensitivity_normal_offsets_m"]
        sensitivity.fill_between(arrays["sensitivity_station_m"], offsets.min(axis=0), offsets.max(axis=0), color="#6879a8", alpha=.35)
        sensitivity.axhline(0., color="#17283f", lw=.7)
        sensitivity.set(xlabel="Reference station (m)", ylabel="Signed normal offset (m)", title="Ten leave-one-lap fits: descriptive range, not a confidence interval")
        for axis in axes.ravel():
            axis.grid(alpha=.16)
            axis.tick_params(labelsize=8)
            axis.title.set_fontsize(10)
        fig.suptitle(f"{track.title()} | R029 reconstructed reference geometry | {len(test_laps)} development holdout laps", fontsize=13)
        fig.text(.5, .014, "Conditional registered shape; public provider positions; coarse curvature proxy. Road width/elevation/official DRS/full pit route unknown.", ha="center", fontsize=8)
        fig.tight_layout(rect=(0, .04, 1, .96))
        fig.savefig(output/f"{track}-reference-geometry-v3.png", dpi=160)
        plt.close(fig)
    result = {"schema_version": "apex-reference-geometry-figures-v1", "source_summary_sha256": summary["content_sha256"],
              "source_manifest_sha256": manifest["content_sha256"], "plot_script_sha256": file_sha256(__file__),
              "files": {p.name: file_sha256(p) for p in sorted(output.iterdir())}}
    result["content_sha256"] = payload_sha256(result)
    write_manifest(output/"manifest.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, dest="input_path")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(render(args.input_path, args.output), indent=2))
