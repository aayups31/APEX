from __future__ import annotations

import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Union

import numpy as np
import pandas as pd
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from apexsim.examples.complete_sim_demo import build_demo
from apexsim.registry import RunRegistry


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    laps: int = Field(default=3, ge=1, le=12)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)


class SimulationJob(BaseModel):
    job_id: str
    status: str
    created_at: str
    started_at: Union[str, None]  # noqa: UP007 - Pydantic must evaluate this on local Python 3.9.
    finished_at: Union[str, None]  # noqa: UP007
    laps: int
    seed: int
    artifact_dir: Union[str, None]  # noqa: UP007
    runtime_s: Union[float, None]  # noqa: UP007
    error: Union[str, None]  # noqa: UP007


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    maturity: str
    capabilities: list[str]


class OverviewResponse(BaseModel):
    maturity: str
    evidence_status: str
    race_previews: int
    world_model_runs: int
    latest_job: Union[SimulationJob, None]  # noqa: UP007
    principle: str


class PlatformJobStore:
    def __init__(self, database_path: str | Path) -> None:
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS simulation_jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    laps INTEGER NOT NULL,
                    seed INTEGER NOT NULL,
                    artifact_dir TEXT,
                    runtime_s REAL,
                    error TEXT
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def create(self, job_id: str, request: SimulationRequest) -> dict[str, Any]:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO simulation_jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (job_id, "QUEUED", created_at, None, None, request.laps, request.seed, None, None, None),
            )
        return self.get(job_id)

    def update(self, job_id: str, job_status: str, **changes: Any) -> None:
        allowed = {"started_at", "finished_at", "artifact_dir", "runtime_s", "error"}
        invalid = set(changes) - allowed
        if invalid:
            raise ValueError(f"Unsupported job fields: {sorted(invalid)}")
        assignments = ["status = ?", *(f"{key} = ?" for key in changes)]
        values = [job_status, *changes.values(), job_id]
        with self._connect() as connection:
            connection.execute(
                f"UPDATE simulation_jobs SET {', '.join(assignments)} WHERE job_id = ?",
                values,
            )

    def get(self, job_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM simulation_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return dict(row)

    def list(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM simulation_jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def recover_incomplete(self) -> int:
        """Close jobs that cannot survive a local API process restart."""
        finished_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE simulation_jobs
                SET status = 'FAILED', finished_at = ?,
                    error = 'Local executor restarted before completion'
                WHERE status IN ('QUEUED', 'RUNNING')
                """,
                (finished_at,),
            )
        return cursor.rowcount


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Artifact not found: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _sample_frame(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Artifact not found: {path.name}")
    frame = pd.read_csv(path)
    if len(frame) > limit:
        indices = np.linspace(0, len(frame) - 1, limit).astype(int)
        frame = frame.iloc[indices]
    frame = frame.astype(object).where(pd.notna(frame), None)
    return frame.to_dict(orient="records")


def _execute_preview(job_id: str, request: SimulationRequest, store_path: Path, race_root: Path) -> None:
    store = PlatformJobStore(store_path)
    started = datetime.now(timezone.utc).isoformat()
    start_clock = time.perf_counter()
    store.update(job_id, "RUNNING", started_at=started)
    try:
        output = race_root / job_id
        simulator = build_demo(seed=request.seed, total_laps=request.laps)
        result = simulator.run()
        result.save(output)
        runtime = time.perf_counter() - start_clock
        store.update(
            job_id,
            "COMPLETED",
            finished_at=datetime.now(timezone.utc).isoformat(),
            artifact_dir=str(output),
            runtime_s=runtime,
        )
    except Exception as exc:  # The job record is the platform failure boundary.
        store.update(
            job_id,
            "FAILED",
            finished_at=datetime.now(timezone.utc).isoformat(),
            runtime_s=time.perf_counter() - start_clock,
            error=f"{type(exc).__name__}: {exc}",
        )


def create_api(artifacts_dir: str | Path = "artifacts") -> FastAPI:
    supplied_root = Path(artifacts_dir)
    root = supplied_root.parent if supplied_root.name == "runs" else supplied_root
    model_runs_root = root / "runs"
    platform_root = root / "platform"
    race_root = platform_root / "race_runs"
    store_path = platform_root / "jobs.sqlite"
    race_root.mkdir(parents=True, exist_ok=True)
    store = PlatformJobStore(store_path)
    store.recover_incomplete()
    registry = RunRegistry(model_runs_root / "runs.sqlite")

    web_root = Path(__file__).with_name("web")
    app = FastAPI(
        title="APEX Simulation Platform",
        version="0.4.0",
        description="Evidence-linked motorsport simulation, replay and strategy research API.",
    )
    app.mount("/assets", StaticFiles(directory=web_root), name="assets")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def platform() -> HTMLResponse:
        return HTMLResponse((web_root / "index.html").read_text(encoding="utf-8"))

    @app.get("/api/v1/health")
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="apex-platform",
            version=app.version,
            maturity="R0_FOUNDATION",
            capabilities=["deterministic_race_preview", "artifact_replay", "provenance"],
        )

    @app.get("/api/v1/overview")
    def overview() -> OverviewResponse:
        jobs = store.list(limit=100)
        completed = [job for job in jobs if job["status"] == "COMPLETED"]
        model_runs = registry.list_runs()
        return OverviewResponse(
            maturity="R0",
            evidence_status="FOUNDATION ACTIVE",
            race_previews=len(completed),
            world_model_runs=len(model_runs),
            latest_job=SimulationJob.model_validate(jobs[0]) if jobs else None,
            principle="Evidence before claims",
        )

    @app.get("/api/v1/runs")
    def runs(limit: int = Query(default=30, ge=1, le=100)) -> list[dict[str, Any]]:
        race_runs = [
            {"run_id": job["job_id"], "kind": "race_preview", **job}
            for job in store.list(limit=limit)
        ]
        model_runs = [{"kind": "world_model", **run} for run in registry.list_runs()[:limit]]
        return sorted(
            [*race_runs, *model_runs],
            key=lambda item: item.get("created_at") or item.get("started_at") or "",
            reverse=True,
        )[:limit]

    @app.post("/api/v1/simulations", status_code=status.HTTP_202_ACCEPTED)
    def create_simulation(
        request: SimulationRequest,
        background_tasks: BackgroundTasks,
    ) -> SimulationJob:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        job_id = f"race-{timestamp}-{uuid.uuid4().hex[:8]}"
        job = store.create(job_id, request)
        background_tasks.add_task(_execute_preview, job_id, request, store_path, race_root)
        return SimulationJob.model_validate(job)

    @app.get("/api/v1/jobs/{job_id}")
    def job(job_id: str) -> SimulationJob:
        try:
            return SimulationJob.model_validate(store.get(job_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Simulation job not found") from exc

    def race_run_path(run_id: str) -> Path:
        try:
            job_record = store.get(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Race run not found") from exc
        if job_record["status"] != "COMPLETED" or not job_record["artifact_dir"]:
            raise HTTPException(status_code=409, detail=f"Race run is {job_record['status']}")
        path = Path(job_record["artifact_dir"])
        if path.parent.resolve() != race_root.resolve():
            raise HTTPException(status_code=500, detail="Artifact path failed platform boundary check")
        return path

    @app.get("/api/v1/runs/{run_id}")
    def run_details(run_id: str) -> dict[str, Any]:
        return _read_json(race_run_path(run_id) / "summary.json")

    @app.get("/api/v1/runs/{run_id}/manifest")
    def run_manifest(run_id: str) -> dict[str, Any]:
        return _read_json(race_run_path(run_id) / "manifest.json")

    @app.get("/api/v1/runs/{run_id}/standings")
    def run_standings(run_id: str) -> list[dict[str, Any]]:
        return _sample_frame(race_run_path(run_id) / "standings.csv", 30)

    @app.get("/api/v1/runs/{run_id}/events")
    def run_events(run_id: str) -> list[dict[str, Any]]:
        return _sample_frame(race_run_path(run_id) / "events.csv", 300)

    @app.get("/api/v1/runs/{run_id}/track")
    def run_track(run_id: str) -> list[dict[str, Any]]:
        return _sample_frame(race_run_path(run_id) / "track.csv", 900)

    @app.get("/api/v1/runs/{run_id}/telemetry")
    def run_telemetry(
        run_id: str,
        limit: int = Query(default=1000, ge=100, le=5000),
    ) -> list[dict[str, Any]]:
        return _sample_frame(race_run_path(run_id) / "telemetry.csv", limit)

    return app
