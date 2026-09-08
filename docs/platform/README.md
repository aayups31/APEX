# APEX local platform and API

The local platform is a high-quality inspection surface over the current R0 simulation
evidence. It deliberately separates usable product ergonomics from unsupported model
claims.

## Start

```bash
cd apex_engine
python -m pip install -e '.[dev]'
apexsim api --artifacts-dir artifacts
```

- Platform: `http://127.0.0.1:8000`
- OpenAPI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/v1/health`

## API v1

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/v1/health` | Service version, maturity, and capability declaration. |
| `GET` | `/api/v1/overview` | Counts and latest local evidence status. |
| `GET` | `/api/v1/runs` | Combined race-preview and model-run index. |
| `POST` | `/api/v1/simulations` | Queue a bounded deterministic preview (`laps`, `seed`). |
| `GET` | `/api/v1/jobs/{job_id}` | Read execution state and failure details. |
| `GET` | `/api/v1/runs/{run_id}` | Read the human-oriented run summary. |
| `GET` | `/api/v1/runs/{run_id}/manifest` | Read configuration, code, environment, hashes, and truth labels. |
| `GET` | `/api/v1/runs/{run_id}/standings` | Read final classification. |
| `GET` | `/api/v1/runs/{run_id}/events` | Read the sampled event stream. |
| `GET` | `/api/v1/runs/{run_id}/track` | Read track geometry for replay. |
| `GET` | `/api/v1/runs/{run_id}/telemetry` | Read bounded, sampled telemetry. |

Generated race evidence is stored under
`artifacts/platform/race_runs/{run_id}/`. Directories are immutable: a non-empty target
is never overwritten. `artifacts/platform/jobs.sqlite` is the local job index.

## Operational boundary

The preview executor uses FastAPI in-process background tasks. This is appropriate for a
single local process and automated contract tests. It does not provide durable retries,
horizontal workers, authentication, rate limits, multi-user isolation, or remote object
storage. Those are production-platform work and must be added without weakening artifact
immutability or provenance.

The UI has no analytics or third-party runtime dependency. It consumes only `/api/v1`
and presents all current tyre, fuel, energy, and outcome values as simulated evidence.
