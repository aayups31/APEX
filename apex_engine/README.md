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
