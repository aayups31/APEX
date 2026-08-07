"""Airflow 3 TaskFlow DAG for Project APEX.

The DAG is deliberately thin: it calls the same tested pipeline stages used by the CLI. This avoids
building one implementation for local work and a second, divergent implementation for production.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

try:
    from airflow.sdk import dag, task
except ImportError:  # Allows syntax checks without installing Airflow.
    dag = task = None


if dag is not None:
    @dag(
        dag_id="project_apex_world_model",
        start_date=datetime(2026, 1, 1),
        schedule=None,
        catchup=False,
        tags=["f1", "world-model", "simulation"],
    )
    def project_apex_world_model():
        @task(retries=2)
        def run_pipeline_task(config_path: str, run_id: str) -> str:
            from apexsim.config import load_config
            from apexsim.pipeline.runner import run_pipeline

            summary = run_pipeline(load_config(Path(config_path)), run_id)
            return str(Path(summary["publication"]["run_dir"]) / "summary.json")

        run_pipeline_task("configs/fast.yaml", "airflow_scheduled_run")

    project_apex_world_model()
