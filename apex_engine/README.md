# APEX Engine

This directory contains the runnable implementation of APEX.

APEX is a research-driven motorsport simulation platform focused on physics-informed race modelling, telemetry processing, strategy optimization, and learned world models.

## Contents

The engine contains:

- the deterministic race-simulation kernel;
- vehicle, tyre, fuel, ERS, weather, traffic, and race-control models;
- telemetry ingestion and canonical data contracts;
- FastF1 and OpenF1 adapters;
- statistical and machine-learning baselines;
- strategy and counterfactual evaluation tools;
- command-line interfaces;
- automated tests and validation utilities.

## Installation

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e '.[dev,real-data]'
```

## Local API and platform

Launch the evidence-linked platform with:

```bash
apexsim api --artifacts-dir artifacts
```

Then visit `http://127.0.0.1:8000` for the minimal web interface or
`http://127.0.0.1:8000/docs` for the OpenAPI interface. Race previews run as local
background jobs and create immutable directories below `artifacts/platform/race_runs/`.
The background executor is intentionally in-process at R0; a durable queue and worker
deployment belong to a later production hardening gate.

## Verify

```bash
ruff check src tests
pytest -q
```
