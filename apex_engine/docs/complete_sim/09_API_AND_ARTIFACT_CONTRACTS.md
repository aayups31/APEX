# API and Artifact Contracts

## Scenario request

```json
{
  "base_run_id": "historical_event_model_v3",
  "initial_state_id": "event-lap-timestamp",
  "interventions": [
    {"type": "pace_mode", "car_id": "CAR_01", "value": "PUSH", "start_lap": 12},
    {"type": "pit", "car_id": "CAR_01", "lap": 18, "compound": "HARD"}
  ],
  "rollouts": 200,
  "risk_measure": "p90_finish_position"
}
```

## Scenario response

```json
{
  "scenario_id": "...",
  "status": "completed",
  "support": "WEAK_SUPPORT",
  "warnings": ["wetness exceeds training 95th percentile"],
  "outcomes": {
    "finish_position_median": 4,
    "finish_position_p90": 8,
    "race_time_delta_median_s": -2.1
  },
  "evidence": {
    "model_bundle": "...",
    "dataset_version": "...",
    "assumption_version": "..."
  }
}
```

## Required API endpoints

```text
GET  /health
GET  /models
GET  /datasets
GET  /runs
GET  /runs/{id}
POST /replays
POST /scenarios
GET  /scenarios/{id}
POST /strategies/evaluate
GET  /artifacts/{id}/manifest
```

Do not expose long-running work as synchronous once full ensembles are used. Add a real queue/job store before claiming background operation.

## Artifact status

Each run should be one of:

```text
CREATED → DATA_VALIDATED → CALIBRATED → SIMULATED → EVALUATED → PUBLISHED
                              ↘ FAILED
```

No UI should present a run as evaluated if only simulation completed.
