from pathlib import Path

from fastapi.testclient import TestClient

from apexsim.serving import PlatformJobStore, SimulationRequest, create_api


def test_platform_serves_ui_and_versioned_api(tmp_path: Path):
    client = TestClient(create_api(tmp_path / "artifacts"))

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["maturity"] == "R0_FOUNDATION"

    page = client.get("/")
    assert page.status_code == 200
    assert "Model the race" in page.text
    assert client.get("/assets/platform.css").status_code == 200
    assert client.get("/assets/platform.js").status_code == 200

    openapi = client.get("/openapi.json").json()
    assert openapi["info"]["version"] == "0.4.0"
    assert "/api/v1/simulations" in openapi["paths"]

    created = client.post("/api/v1/simulations", json={"laps": 1, "seed": 19})
    assert created.status_code == 202
    job_id = created.json()["job_id"]
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "COMPLETED"

    details = client.get(f"/api/v1/runs/{job_id}")
    assert details.status_code == 200
    assert details.json()["quality"]["passed"]
    assert len(client.get(f"/api/v1/runs/{job_id}/standings").json()) == 6
    assert client.get(f"/api/v1/runs/{job_id}/track").json()
    assert client.get(f"/api/v1/runs/{job_id}/telemetry").json()
    assert client.get(f"/api/v1/runs/{job_id}/events").status_code == 200
    assert client.get(f"/api/v1/runs/{job_id}/manifest").json()["run_type"] == "race_simulation"


def test_platform_rejects_out_of_range_preview(tmp_path: Path):
    client = TestClient(create_api(tmp_path / "artifacts"))
    response = client.post("/api/v1/simulations", json={"laps": 50, "seed": 1})
    assert response.status_code == 422

    unexpected = client.post(
        "/api/v1/simulations",
        json={"laps": 1, "seed": 1, "unsupported": True},
    )
    assert unexpected.status_code == 422


def test_platform_marks_interrupted_local_jobs_failed_on_restart(tmp_path: Path):
    root = tmp_path / "artifacts"
    store = PlatformJobStore(root / "platform" / "jobs.sqlite")
    store.create("race-interrupted", SimulationRequest(laps=2, seed=4))

    client = TestClient(create_api(root))
    job = client.get("/api/v1/jobs/race-interrupted")
    assert job.status_code == 200
    assert job.json()["status"] == "FAILED"
    assert "restarted" in job.json()["error"]
