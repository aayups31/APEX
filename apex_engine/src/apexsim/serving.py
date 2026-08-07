from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

from apexsim.registry import RunRegistry


def create_api(artifacts_dir: str | Path = "artifacts/runs") -> FastAPI:
    root = Path(artifacts_dir)
    registry = RunRegistry(root / "runs.sqlite")
    app = FastAPI(title="Project APEX API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/runs")
    def runs() -> list[dict]:
        return registry.list_runs()

    @app.get("/runs/{run_id}")
    def run_details(run_id: str) -> dict:
        path = root / run_id / "summary.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Run not found")
        return json.loads(path.read_text())

    @app.get("/runs/{run_id}/rollout")
    def rollout_preview(run_id: str) -> list[dict]:
        path = root / run_id / "rollout_preview.csv"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Rollout preview not found")
        import pandas as pd

        return pd.read_csv(path).to_dict(orient="records")

    return app
