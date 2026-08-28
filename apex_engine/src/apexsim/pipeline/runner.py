from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from apexsim.config import ProjectConfig
from apexsim.pipeline.stages import (
    ablation_stage,
    dataset_stage,
    evaluate_stage,
    ingest_stage,
    publish_stage,
    quality_stage,
    train_stage,
)
from apexsim.provenance import build_run_manifest, ensure_run_directory, write_manifest
from apexsim.registry import RunRegistry


def run_pipeline(config: ProjectConfig, run_id: str) -> dict:
    run_dir = ensure_run_directory(config.artifacts_dir, run_id)
    registry = RunRegistry(config.artifacts_dir / "runs.sqlite")
    registry.start(run_id, config.model.kind, str(run_dir))
    started = datetime.now(timezone.utc).isoformat()
    try:
        canonical = ingest_stage(config, run_dir)
        repository_root = Path(__file__).resolve().parents[4]
        source_manifest = run_dir / "source_manifest.json"
        manifest_inputs = [canonical]
        if source_manifest.is_file():
            manifest_inputs.append(source_manifest)
        write_manifest(
            run_dir / "manifest.json",
            build_run_manifest(
                run_id=run_id,
                run_type="world_model_pipeline",
                config=config,
                seed=config.seed,
                repository_root=repository_root,
                inputs=manifest_inputs,
                truth_labels={
                    "telemetry": "SIMULATED" if config.data.source == "synthetic" else "MEASURED_OR_RECONSTRUCTED",
                    "tyre_age_laps": "SIMULATED" if config.data.source == "synthetic" else "RECONSTRUCTED",
                },
            ),
        )
        quality = quality_stage(canonical, run_dir)
        dataset = dataset_stage(config, canonical, run_dir)
        model = train_stage(config, canonical, run_dir)
        metrics = evaluate_stage(config, canonical, run_dir)
        ablations = ablation_stage(config, canonical, run_dir)
        publication = publish_stage(config, canonical, run_dir)
        summary = {
            "run_id": run_id,
            "status": "succeeded",
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "canonical_data": str(canonical),
            "quality": quality,
            "splits": dataset["splits"],
            "model": model,
            "metrics": metrics,
            "best_ablation": ablations[0],
            "publication": publication,
        }
        (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        registry.finish(run_id, "succeeded", metrics)
        return summary
    except Exception:
        registry.finish(run_id, "failed")
        raise
